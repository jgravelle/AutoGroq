# Modified/extended from AutoGroq by J. Gravelle: actual-caller regressions.
"""Run with python -m unittest discover -s tests -v (Python 3.11).

Uses the installed Streamlit runtime, production initialization, loader, tool UI,
dispatcher, prompt builder, result display and reset. Only HTTP and inference
boundaries are scripted; these tests do not claim live model reasoning.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "AutoGroq"))

from streamlit.testing.v1 import AppTest
from utils.parallel_mcp import MCP_URL, USER_AGENT, TIMEOUT

APP = Path(__file__).parent / "fixtures" / "parallel_app.py"


class ParallelCallerTests(unittest.TestCase):
    def app(self, selected=None, **state):
        app = AppTest.from_file(str(APP), default_timeout=10)
        if selected is not None:
            app.session_state["selected_tools"] = selected
        for key, value in state.items():
            app.session_state[key] = value
        app.run()
        self.assertFalse(app.exception)
        return app

    def checkbox(self, app, name):
        return next(box for box in app.checkbox if box.label == f"Add {name} tool to all agents")

    def run_agent(self, app, query="Python release documentation", url=""):
        next(item for item in app.text_area if item.label == "Additional Input:").set_value(query)
        next(item for item in app.text_input if item.label == "URL:").set_value(url)
        next(item for item in app.button if item.label == "Run agent").click().run()
        self.assertFalse(app.exception)

    def calls(self, app):
        return [r["payload"]["params"] for r in app.session_state["http_requests"]
                if r["payload"]["method"] == "tools/call"]

    def prompt(self, app):
        return app.session_state["model_requests"][-1]["messages"][0]["content"]

    def test_default_loader_dispatch_results_and_anonymous_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            netrc = Path(directory) / "netrc"
            netrc.write_text("machine search.parallel.ai login unused password must-not-be-sent\n")
            with patch.dict(os.environ, {"PARALLEL_API_KEY": "must-not-be-used", "NETRC": str(netrc)}):
                app = self.app(model="saved-local-model", provider="ollama")
                self.assertEqual(app.session_state["selected_tools"], ["parallel_search"])
                self.assertTrue(self.checkbox(app, "parallel_search").value)
                self.run_agent(app)
        call = self.calls(app)[0]
        self.assertEqual(call["name"], "web_search")
        self.assertEqual(call["arguments"]["objective"], "Python release documentation")
        self.assertEqual(call["arguments"]["search_queries"], ["Python release documentation"])
        self.assertIn("https://example.org/source", self.prompt(app))
        self.assertIn("Verified source excerpt", self.prompt(app))
        self.assertIn("Scripted answer", app.session_state["discussion_history"])
        self.assertEqual(app.session_state["model_requests"][-1]["model"], "saved-local-model")
        self.assertEqual(app.session_state["provider"], "ollama")
        requests = app.session_state["http_requests"]
        self.assertEqual([r["payload"]["method"] for r in requests],
                         ["initialize", "notifications/initialized", "tools/list", "tools/call"])
        for request in requests:
            self.assertEqual(request["url"], MCP_URL)
            self.assertEqual(request["headers"]["User-Agent"], USER_AGENT)
            self.assertNotIn("Authorization", request["headers"])
            self.assertTrue(request["anonymous_auth"])
            self.assertEqual(request["timeout"], TIMEOUT)
            self.assertFalse(request["allow_redirects"])
        for request in requests[1:]:
            self.assertEqual(request["headers"]["Mcp-Session-Id"], "transport-session")
            self.assertEqual(request["headers"]["MCP-Protocol-Version"], "2024-11-05")

    def test_saved_empty_and_custom_choices_and_disable(self):
        app = self.app(selected=[])
        self.run_agent(app)
        self.assertEqual(self.calls(app), [])
        self.assertFalse(self.checkbox(app, "parallel_search").value)
        self.checkbox(app, "parallel_search").check().run()
        self.run_agent(app)
        self.assertEqual(len(self.calls(app)), 1)
        self.checkbox(app, "parallel_search").uncheck().run()
        self.run_agent(app)
        self.assertEqual(len(self.calls(app)), 1)
        saved = self.app(selected=["parallel_fetch"])
        self.assertEqual(saved.session_state["selected_tools"], ["parallel_fetch"])
        self.assertFalse(self.checkbox(saved, "parallel_search").value)

    def test_search_fetch_followup_and_reset_identity(self):
        app = self.app()
        self.run_agent(app)
        original = self.calls(app)[0]["arguments"]["session_id"]
        self.checkbox(app, "parallel_search").uncheck()
        self.checkbox(app, "parallel_fetch").check().run()
        self.run_agent(app, url="https://example.org/source?q=1#section")
        self.assertEqual(self.calls(app)[-1]["arguments"]["urls"],
                         ["https://example.org/source?q=1#section"])
        self.assertEqual(self.calls(app)[-1]["arguments"]["session_id"], original)
        for request in app.session_state["http_requests"]:
            self.assertEqual(request["url"], MCP_URL)
            self.assertEqual(request["headers"]["User-Agent"], USER_AGENT)
            self.assertNotIn("Authorization", request["headers"])
        self.checkbox(app, "parallel_fetch").uncheck()
        self.checkbox(app, "parallel_search").check().run()
        self.run_agent(app, query="Python follow up changes")
        self.assertEqual(self.calls(app)[-1]["arguments"]["session_id"], original)
        next(item for item in app.button if item.label == "Reset").click().run()
        self.assertEqual(app.session_state["selected_tools"], ["parallel_search"])
        self.assertEqual(next(item for item in app.text_area if item.label == "Additional Input:").value, "")
        self.assertEqual(next(item for item in app.text_input if item.label == "URL:").value, "")
        prior_call_count = len(self.calls(app))
        self.run_agent(app, query="")
        self.assertEqual(len(self.calls(app)), prior_call_count)
        self.run_agent(app)
        self.assertNotEqual(self.calls(app)[-1]["arguments"]["session_id"], original)

    def test_interleaved_conversations(self):
        a, b = self.app(), self.app()
        self.run_agent(a)
        self.run_agent(b)
        aid = self.calls(a)[-1]["arguments"]["session_id"]
        bid = self.calls(b)[-1]["arguments"]["session_id"]
        self.assertNotEqual(aid, bid)
        # AppTest owns one process-global test runtime; interleave real sessions.
        self.run_agent(a, query="A follow up research question")
        self.run_agent(b, query="Another independent research question")
        self.run_agent(a, query="A final follow up research question")
        self.assertEqual(self.calls(a)[-1]["arguments"]["session_id"], aid)
        self.assertEqual(self.calls(b)[-1]["arguments"]["session_id"], bid)

    def test_errors_quotas_retry_identity_and_no_fallback(self):
        for failure, expected in [("timeout", "timed out"), ("http_quota", "quota"),
                                  ("tool_quota", "quota"), ("http_error", "503"),
                                  ("invalid_json", "error"), ("rpc_error", "Invalid tool arguments"),
                                  ("missing_result", "no matching result"), ("empty", "empty content")]:
            with self.subTest(failure=failure):
                app = self.app(failure=failure)
                self.run_agent(app)
                self.assertIn(expected, self.prompt(app))
                self.assertEqual(len(self.calls(app)), 1)
                identity = self.calls(app)[0]["arguments"]["session_id"]
                app.session_state["failure"] = None
                self.run_agent(app)
                self.assertEqual(len(self.calls(app)), 2)
                self.assertEqual(self.calls(app)[-1]["arguments"]["session_id"], identity)

    def test_sse_and_structured_result_consumption(self):
        for state in [{"sse": True}, {"failure": "structured"}]:
            with self.subTest(state=state):
                app = self.app(**state)
                self.run_agent(app)
                self.assertIn("Verified source excerpt", self.prompt(app))

    def test_cancellation_does_not_reach_model_or_retry(self):
        app = self.app(failure="cancel")
        self.run_agent(app)
        self.assertTrue(app.session_state["cancelled"])
        self.assertEqual(app.session_state["model_requests"], [])
        self.assertEqual(len(self.calls(app)), 1)
        identity = self.calls(app)[0]["arguments"]["session_id"]
        app.session_state["failure"] = None
        self.run_agent(app)
        self.assertEqual(self.calls(app)[-1]["arguments"]["session_id"], identity)

    def test_fetch_rejects_bad_urls_before_network(self):
        app = self.app(selected=["parallel_fetch"])
        for url in ["", "file:///tmp/private", "https://user:pass@example.org", "https://example.org:bad"]:
            self.run_agent(app, url=url)
            self.assertEqual(self.calls(app), [])
            self.assertIn("valid HTTP or HTTPS", self.prompt(app))

    def test_selected_tools_survive_archive_generation(self):
        app = self.app()
        for agent in app.session_state["agents"]:
            self.assertEqual(agent.tools[0].name, "parallel_search")
            self.assertEqual(agent.to_dict()["tools"][0]["name"], "parallel_search")
            self.assertEqual(agent.tools[0].name, "parallel_search")
        self.assertGreater(len(app.session_state["autogen_zip_buffer"].getvalue()), 0)

    def test_explicit_existing_fetcher_remains_available(self):
        app = self.app(selected=["fetch_web_content"])
        self.run_agent(app, url="https://example.org/existing")
        self.assertEqual(self.calls(app), [])
        self.assertIn("Existing fetcher content", self.prompt(app))
        self.assertEqual(app.session_state["http_requests"][0]["url"], "https://example.org/existing")

    def test_empty_query_does_not_call_service(self):
        app = self.app()
        self.run_agent(app, query="")
        self.assertEqual(self.calls(app), [])
        self.assertIn("enter a search query", self.prompt(app))


if __name__ == "__main__":
    unittest.main()
