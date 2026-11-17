"""An MCP web-search server backed by Google Programmable Search.

Install dependencies with `uv sync`.
Set GOOGLE_API_KEY and GOOGLE_CSE_ID in the environment before launching this file.
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("Google Web Search")
SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


@mcp.tool()
async def web_search(query: str, count: int = 5) -> list[dict[str, str]]:
    """Search Google and return result titles, URLs, and descriptions."""
    query = query.strip()
    if not query:
        raise ValueError("Search query cannot be empty")
    if not 1 <= count <= 10:
        raise ValueError("count must be between 1 and 10")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Set GOOGLE_API_KEY before starting the MCP server")

    search_engine_id = os.getenv("GOOGLE_CSE_ID")
    if not search_engine_id:
        raise RuntimeError("Set GOOGLE_CSE_ID before starting the MCP server")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                SEARCH_URL,
                params={
                    "key": api_key,
                    "cx": search_engine_id,
                    "q": query,
                    "num": count,
                    "safe": "active",
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Google Search API returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Could not reach search API: {exc}") from exc

    results = response.json().get("items", [])
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "description": item.get("snippet", ""),
        }
        for item in results[:count]
    ]


if __name__ == "__main__":
    mcp.run()
