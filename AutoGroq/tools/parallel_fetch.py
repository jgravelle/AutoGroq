# Modified/extended from AutoGroq by J. Gravelle: optional Parallel page fetching.
import inspect
from urllib.parse import urlsplit

from models.tool_base_model import ToolBaseModel
from utils.parallel_mcp import call_parallel_tool


def parallel_fetch(url: str) -> str:
    """Fetch excerpts from the reference URL using Parallel Search MCP."""
    try:
        parsed = urlsplit(url.strip())
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError()
        # Validate the port before making any request.
        parsed.port
    except ValueError:
        return "Parallel search error: enter a valid HTTP or HTTPS reference URL."
    return call_parallel_tool("web_fetch", {"urls": [url.strip()]})


parallel_fetch_tool = ToolBaseModel(
    name="parallel_fetch", description=parallel_fetch.__doc__,
    title="Parallel Page Fetch", file_name="parallel_fetch.py",
    content=inspect.getsource(parallel_fetch), function=parallel_fetch)


def get_tool():
    return parallel_fetch_tool
