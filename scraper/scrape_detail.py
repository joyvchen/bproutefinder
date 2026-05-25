"""
Pass 2: Scrape individual route detail pages.

Enriches existing route records with: description, difficulty (1–10),
unpaved_pct, singletrack_pct, rideable_pct, elevation_gain_ft,
bike_type, tire_width_min_mm, tire_width_max_mm.

Uses requests + BeautifulSoup (faster than Playwright for static pages).
Falls back to Playwright for JS-rendered pages.
"""
import asyncio
import random
import re
import time
from datetime import datetime, timezone
from typing import Optional
import requests
from bs4 import BeautifulSoup
from playwright.async_api import Browser
from config import USER_AGENT, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX
from utils import (
    parse_difficulty, parse_pct, parse_elevation, parse_distance,
    parse_days, extract_bike_types, parse_tire_width,
)
from upsert import fetch_routes_needing_detail, upsert_route, mark_detail_scraped


SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


def fetch_html(url: str) -> Optional[str]:
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  [fetch error] {url}: {e}")
        return None


def parse_stat_block(soup: BeautifulSoup) -> dict:
    """
    Extract numeric stats from the structured stats/specs block on a route page.
    Bikepacking.com shows these as labeled pairs: Distance, Ascent, Days, Difficulty,
    Unpaved, Singletrack, Rideable.
    """
    result = {}

    # Try to find the stats container
    stats_block = (
        soup.find(class_=re.compile(r'route.?stat|stats|spec|info.?box', re.IGNORECASE))
        or soup.find('table')
    )
    if not stats_block:
        stats_block = soup

    text = stats_block.get_text(' ', strip=True)

    # Distance
    mi, km = parse_distance(text)
    if mi:
        result['distance_mi'] = mi
    if km:
        result['distance_km'] = km

    # Elevation / Ascent
    ft, m = parse_elevation(text)
    if ft:
        result['elevation_gain_ft'] = ft
    if m:
        result['elevation_gain_m'] = m

    # Days
    days_min, days_max = parse_days(text)
    if days_min:
        result['days_min'] = days_min
        result['days_max'] = days_max

    # Difficulty (look near "difficulty" label)
    diff_match = re.search(r'difficulty[:\s]*([0-9.]+(?:\s*/\s*10)?)', text, re.IGNORECASE)
    if diff_match:
        result['difficulty'] = parse_difficulty(diff_match.group(0))

    # Percentage fields
    for field, pattern in [
        ('unpaved_pct', r'unpaved[:\s]*([\d]+)\s*%'),
        ('singletrack_pct', r'singletrack[:\s]*([\d]+)\s*%'),
        ('rideable_pct', r'rideable[:\s]*([\d]+)\s*%'),
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result[field] = int(m.group(1))

    return result


def parse_editorial_body(soup: BeautifulSoup) -> dict:
    """
    Scan editorial/body paragraphs for bike type and tire width recommendations.
    These are rarely in the stats table — they appear in the written content.
    """
    result = {}

    # Get body paragraphs (article content, excluding sidebar/nav)
    article = (
        soup.find('article')
        or soup.find(class_=re.compile(r'entry.?content|post.?content|content', re.IGNORECASE))
        or soup
    )
    body_text = article.get_text(' ', strip=True)

    # Bike type
    bike_types = extract_bike_types(body_text)
    if bike_types:
        result['bike_type'] = bike_types

    # Tire width — scan each paragraph for width patterns
    paragraphs = article.find_all(['p', 'li'])
    for p in paragraphs:
        p_text = p.get_text(' ', strip=True)
        if re.search(r'tire|tyre|wheel', p_text, re.IGNORECASE):
            w_min, w_max = parse_tire_width(p_text)
            if w_min:
                result['tire_width_min_mm'] = w_min
                result['tire_width_max_mm'] = w_max or w_min
                break

    return result


def parse_description(soup: BeautifulSoup) -> Optional[str]:
    """Extract a short description from the first meaningful paragraph."""
    article = (
        soup.find('article')
        or soup.find(class_=re.compile(r'entry.?content|post.?content', re.IGNORECASE))
    )
    if not article:
        article = soup

    for p in article.find_all('p'):
        text = p.get_text(strip=True)
        if len(text) > 80:  # skip very short paragraphs
            return text[:400] + ('...' if len(text) > 400 else '')
    return None


def scrape_route_page(url: str) -> dict:
    html = fetch_html(url)
    if not html:
        return {}
    soup = BeautifulSoup(html, 'lxml')
    result = {}
    result.update(parse_stat_block(soup))
    result.update(parse_editorial_body(soup))
    desc = parse_description(soup)
    if desc:
        result['description'] = desc
    return result


def run(limit: int | None = None, dry_run: bool = False) -> int:
    routes = fetch_routes_needing_detail(limit=limit)
    print(f"Pass 2: Enriching {len(routes)} routes from detail pages...")

    count = 0
    for i, route in enumerate(routes):
        url = route['source_url']
        print(f"  [{i+1}/{len(routes)}] {route['name']} — {url}")

        detail = scrape_route_page(url)
        if detail:
            detail['slug'] = route['slug']
            upsert_route(detail, dry_run=dry_run)
            if not dry_run:
                mark_detail_scraped(route['id'])
            count += 1

        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    print(f"Pass 2 complete: {count} routes enriched")
    return count
