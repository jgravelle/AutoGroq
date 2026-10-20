# Modified/extended from AutoGroq by J. Gravelle: built-in Parallel web search.
import inspect

from models.tool_base_model import ToolBaseModel
from utils.parallel_mcp import call_parallel_tool


def parallel_search(query: str) -> str:
    """Search the web for current sources and excerpts using Parallel Search MCP."""
    if not query or not query.strip():
        return "Parallel search error: enter a search query."
    return call_parallel_tool("web_search", {
        "objective": query, "search_queries": [" ".join(query.split()[:6])]})


parallel_search_tool = ToolBaseModel(
    name="parallel_search", description=parallel_search.__doc__,
    title="Parallel Web Search", file_name="parallel_search.py",
    content=inspect.getsource(parallel_search), function=parallel_search)


def get_tool():
    return parallel_search_tool
