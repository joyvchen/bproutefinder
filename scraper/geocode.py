"""
Nominatim geocoding helper.
Returns (lat, lng) for a state/region string.
Results are cached in GEOCODE_CACHE_FILE to avoid repeated API calls.
Nominatim requires <= 1 request/second.
"""
import json
import os
import time
import requests
from typing import Optional
from config import NOMINATIM_URL, USER_AGENT, GEOCODE_CACHE_FILE


def load_cache() -> dict:
    if os.path.exists(GEOCODE_CACHE_FILE):
        with open(GEOCODE_CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(GEOCODE_CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)


_cache: dict | None = None


def geocode(state: Optional[str], region: Optional[str] = None, country: Optional[str] = None) -> tuple[Optional[float], Optional[float]]:
    global _cache
    if _cache is None:
        _cache = load_cache()

    query_parts = [p for p in [region, state, country] if p]
    if not query_parts:
        return None, None

    cache_key = ', '.join(query_parts)
    if cache_key in _cache:
        cached = _cache[cache_key]
        return cached.get('lat'), cached.get('lng')

    query = cache_key
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        time.sleep(1.1)  # Nominatim rate limit

        if data:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            _cache[cache_key] = {"lat": lat, "lng": lng}
            save_cache(_cache)
            return lat, lng
    except Exception as e:
        print(f"  [geocode] Error for '{query}': {e}")

    _cache[cache_key] = {"lat": None, "lng": None}
    save_cache(_cache)
    return None, None
