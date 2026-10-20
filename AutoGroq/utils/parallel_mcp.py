# Modified/extended from AutoGroq by J. Gravelle: Parallel Search MCP support.
"""Small synchronous Streamable HTTP MCP client for AutoGroq's tool runner."""

import json
import uuid

import requests
import streamlit as st


MCP_URL = "https://search.parallel.ai/mcp"
USER_AGENT = "AutoGroq/ParallelSearch (+https://github.com/jgravelle/AutoGroq)"
TIMEOUT = (5, 20)


class ParallelError(Exception):
    """A search service or protocol error that can be shown to the agent."""


def conversation_id():
    # Streamlit owns this state per conversation, never per shared HTTP client.
    if "parallel_search_session_id" not in st.session_state:
        st.session_state.parallel_search_session_id = str(uuid.uuid4())
    return st.session_state.parallel_search_session_id


def _rpc(client, method, params=None, request_id=None):
    payload = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    if request_id is not None:
        payload["id"] = request_id
    with client.post(MCP_URL, json=payload, timeout=TIMEOUT,
                     allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code >= 300:
            raise ParallelError("Unexpected redirect from Parallel Search MCP.")
        if method == "initialize" and response.headers.get("Mcp-Session-Id"):
            client.headers["Mcp-Session-Id"] = response.headers["Mcp-Session-Id"]
        if request_id is None:
            return None
        if "text/event-stream" in response.headers.get("Content-Type", ""):
            # An SSE response may contain notifications before the RPC result.
            messages = []
            for event in response.text.replace("\r\n", "\n").split("\n\n"):
                data = "\n".join(line[5:].lstrip(" ") for line in event.splitlines()
                                 if line.startswith("data:"))
                if data:
                    messages.append(json.loads(data))
        else:
            messages = [response.json()]
        for message in messages:
            if isinstance(message, dict) and message.get("id") == request_id:
                if "error" in message:
                    raise ParallelError(str(message["error"].get("message", "MCP request failed.")))
                if isinstance(message.get("result"), dict):
                    return message["result"]
        raise ParallelError("Parallel Search MCP returned no matching result.")


def call_parallel_tool(name, arguments):
    """Execute one anonymous call; errors do not trigger retries or fallback."""
    arguments = {**arguments, "session_id": conversation_id()}
    try:
        with requests.Session() as client:
            # Suppress netrc authentication while honoring configured proxies/CA.
            # Parallel API keys are intentionally unused by this anonymous tool.
            client.auth = lambda request: request
            client.headers.update({"User-Agent": USER_AGENT,
                                   "Accept": "application/json, text/event-stream"})
            initialized = _rpc(client, "initialize", {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "AutoGroq", "version": "1.0"}}, 1)
            protocol = initialized.get("protocolVersion")
            if protocol != "2024-11-05":
                raise ParallelError("Parallel Search MCP negotiated an unsupported protocol.")
            client.headers["MCP-Protocol-Version"] = protocol
            _rpc(client, "notifications/initialized")
            tools = _rpc(client, "tools/list", {}, 2)
            if name not in [tool.get("name") for tool in tools.get("tools", [])]:
                raise ParallelError("Parallel Search MCP did not advertise " + name + ".")
            result = _rpc(client, "tools/call", {"name": name, "arguments": arguments}, 3)
            text = "\n".join(block["text"] for block in result.get("content", [])
                             if block.get("type") == "text")
            if result.get("isError"):
                raise ParallelError(text or "Parallel Search MCP tool failed.")
            if isinstance(result.get("structuredContent"), dict):
                return json.dumps(result["structuredContent"], ensure_ascii=False)
            if not text:
                raise ParallelError("Parallel Search MCP returned empty content.")
            return text
    except requests.Timeout:
        return "Parallel search error: request timed out. Try again later."
    except requests.HTTPError as error:
        status = error.response.status_code
        if status == 429:
            return "Parallel search error: service quota reached. Try again later."
        return f"Parallel search error: HTTP {status}."
    except (requests.RequestException, ValueError, ParallelError) as error:
        return f"Parallel search error: {error}"
