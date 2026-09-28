"""Weather MCP server — gives Claude Code weather tools + manages the dashboard's city list."""

import json
import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.abspath(__file__))
CITIES_FILE = os.path.join(PROJECT_DIR, "cities.json")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 61: "Light rain",
    63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow",
    75: "Heavy snow", 80: "Rain showers", 95: "Thunderstorm",
}


def _load_cities():
    try:
        with open(CITIES_FILE, encoding="utf-8") as f:
            return json.load(f).get("cities", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_cities(cities):
    with open(CITIES_FILE, "w", encoding="utf-8") as f:
        json.dump({"cities": cities}, f, indent=2)


def _geocode(city):
    r = httpx.get(GEOCODE_URL, params={"name": city, "count": 1}, timeout=10)
    r.raise_for_status()
    results = r.json().get("results")
    return results[0] if results else None


@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather conditions for a city."""
    place = _geocode(city)
    if not place:
        return f"Could not find a city called {city!r}."
    r = httpx.get(FORECAST_URL, params={
        "latitude": place["latitude"], "longitude": place["longitude"],
        "current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
        "timezone": "auto",
    }, timeout=10)
    r.raise_for_status()
    cur = r.json()["current"]
    desc = WEATHER_CODES.get(cur["weather_code"], "Unknown")
    name = f"{place['name']}, {place.get('country', '')}".strip(", ")
    return (f"{name}: {desc}, {cur['temperature_2m']}°C, "
            f"humidity {cur['relative_humidity_2m']}%, wind {cur['wind_speed_10m']} km/h.")


@mcp.tool()
def list_cities() -> str:
    """List the cities currently shown on the weather dashboard."""
    cities = _load_cities()
    return "Dashboard cities: " + (", ".join(cities) if cities else "(none yet)")


@mcp.tool()
def add_city(city: str) -> str:
    """Add a city to the weather dashboard."""
    place = _geocode(city)
    if not place:
        return f"Could not find a city called {city!r}, so I didn't add it."
    name = place["name"]
    cities = _load_cities()
    if name in cities:
        return f"{name} is already on the dashboard."
    cities.append(name)
    _save_cities(cities)
    return f"Added {name} to the dashboard. Refresh it to see it."


@mcp.tool()
def remove_city(city: str) -> str:
    """Remove a city from the weather dashboard."""
    cities = _load_cities()
    match = next((c for c in cities if c.lower() == city.lower()), None)
    if not match:
        return f"{city} isn't on the dashboard."
    cities.remove(match)
    _save_cities(cities)
    return f"Removed {match} from the dashboard."


if __name__ == "__main__":
    mcp.run()