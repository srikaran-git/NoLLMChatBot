"""MCP tools for current weather and English Wikipedia search.

Install dependencies with `uv sync`.
Run: python weather.py
"""

import re
from html import unescape
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("Weather and Wikipedia")
HEADERS = {"User-Agent": "WeatherWikipediaMCP/1.0 (personal learning project)"}


@mcp.tool()
async def weather(city: str) -> dict:
    """Get current weather for a city, including temperature, humidity, wind and conditions."""
    city = city.strip()
    if not city:
        raise ValueError("city must not be empty")

    try:
        async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
            geo_response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en"},
            )
            geo_response.raise_for_status()
            locations = geo_response.json().get("results") or []
            if not locations:
                return {"error": f"No location found for {city!r}"}

            location = locations[0]
            forecast_response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "precipitation,weather_code,wind_speed_10m",
                    "timezone": "auto",
                },
            )
            forecast_response.raise_for_status()
            forecast = forecast_response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Weather lookup failed: {exc}") from exc

    return {
        "location": ", ".join(
            str(part) for part in (location.get("name"), location.get("admin1"), location.get("country"))
            if part
        ),
        "observed_at": forecast["current"].get("time"),
        "timezone": forecast.get("timezone"),
        "current": forecast["current"],
        "units": forecast.get("current_units", {}),
        "source": "https://open-meteo.com/",
    }


@mcp.tool()
async def wikipedia_search(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search English Wikipedia and return titles, brief excerpts, and page URLs."""
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")

    try:
        async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
            response = await client.get(
                "https://en.wikipedia.org/w/rest.php/v1/search/page",
                params={"q": query, "limit": limit},
            )
            response.raise_for_status()
            pages = response.json().get("pages", [])
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Wikipedia search failed: {exc}") from exc

    return [
        {
            "title": page.get("title", ""),
            "excerpt": unescape(re.sub(r"<[^>]+>", "", page.get("excerpt", ""))),
            "url": "https://en.wikipedia.org/wiki/" + quote(page.get("key", ""), safe="()"),
        }
        for page in pages
    ]


if __name__ == "__main__":
    mcp.run()
