# Modified/extended from AutoGroq by J. Gravelle: scripted caller test fixture.
"""Real Streamlit controls and AutoGroq dispatch; scripted HTTP/model boundaries."""
import json
from unittest.mock import patch

import requests
import streamlit as st

import agent_management
from utils.session_utils import initialize_session_variables
from utils.tool_utils import load_tool_functions, populate_tool_models, show_tools
from utils.ui_utils import show_interfaces, display_reset_and_upload_buttons


def send(client, request, **kwargs):
    payload = json.loads(request.body) if request.method == "POST" else {"method": "legacy/get"}
    st.session_state.http_requests.append({
        "url": request.url, "headers": dict(request.headers), "payload": payload,
        "timeout": kwargs.get("timeout"), "anonymous_auth": client.auth is not None,
        "allow_redirects": kwargs.get("allow_redirects")})
    failure = st.session_state.get("failure")
    if payload["method"] == "tools/call":
        if failure == "timeout":
            raise requests.Timeout()
        if failure == "cancel":
            raise KeyboardInterrupt("scripted cancellation")
    response = requests.Response()
    response._content_consumed = True
    response.status_code = 200
    response.headers["Content-Type"] = "application/json"
    if request.method == "GET":
        response._content = b'<html><body><article>Existing fetcher content</article></body></html>'
        return response
    if payload["method"] == "initialize":
        result = {"protocolVersion": "2024-11-05"}
        response.headers["Mcp-Session-Id"] = "transport-session"
    elif payload["method"] == "notifications/initialized":
        response.status_code = 202
        response._content = b""
        return response
    elif payload["method"] == "tools/list":
        result = {"tools": [{"name": "web_search"}, {"name": "web_fetch"}]}
    else:
        if failure == "http_quota":
            response.status_code = 429
            response._content = b'{}'
            return response
        if failure == "http_error":
            response.status_code = 503
            response._content = b'{}'
            return response
        if failure == "invalid_json":
            response._content = b'not json'
            return response
        if failure == "missing_result":
            response._content = b'{"jsonrpc":"2.0","id":99,"result":{}}'
            return response
        if failure == "rpc_error":
            response._content = json.dumps({"jsonrpc": "2.0", "id": payload["id"],
                "error": {"code": -32602, "message": "Invalid tool arguments"}}).encode()
            return response
        data = {"results": [{"url": "https://example.org/source", "title": "Source",
                             "excerpts": ["Verified source excerpt for the scripted test."]}]}
        result = {"content": [{"type": "text", "text": json.dumps(data)}]}
        if failure == "tool_quota":
            result = {"isError": True, "content": [{"type": "text", "text": "Anonymous quota reached"}]}
        if failure == "structured":
            result = {"structuredContent": data, "content": []}
        if failure == "empty":
            result = {"content": []}
    encoded = json.dumps({"jsonrpc": "2.0", "id": payload.get("id"), "result": result})
    if st.session_state.get("sse"):
        response.headers["Content-Type"] = "text/event-stream"
        encoded = ': keepalive\r\n\r\nevent: message\r\ndata: ' + encoded + '\r\n\r\n'
    response._content = encoded.encode()
    return response


class ScriptedModel:
    def send_request(self, request):
        st.session_state.model_requests.append(request)
        return {"choices": [{"message": {"content": "Scripted answer using supplied sources."}}]}


initialize_session_variables()
st.session_state.setdefault("http_requests", [])
st.session_state.setdefault("model_requests", [])
st.session_state.setdefault("temperature", 0.3)
load_tool_functions()
populate_tool_models()
show_interfaces()
show_tools()
transport = patch.object(requests.Session, "send", send)
if st.session_state.get("live"):
    # Live smoke retains the real anonymous MCP transport, with scripted inference.
    from contextlib import nullcontext
    transport = nullcontext()
with transport, patch.object(agent_management, "get_api_key", return_value=None), \
        patch.object(agent_management, "get_llm_provider", return_value=ScriptedModel()):
    if st.button("Run agent"):
        try:
            agent_management.process_agent_interaction(0)
        except KeyboardInterrupt:
            st.session_state.cancelled = True
display_reset_and_upload_buttons()
