"""
Pass 1: Scrape the bikepacking.com routes listing page.

Clicks "Load 4 More" until all routes are visible, then extracts basic
metadata from each route card and upserts into Supabase.
"""
import asyncio
import re
from typing import Optional
from bs4 import BeautifulSoup
from playwright.async_api import Page
from config import LISTING_URL, BASE_URL
from utils import parse_distance, parse_days, slugify
from geocode import geocode
from upsert import upsert_route


async def load_all_routes(page: Page) -> None:
    """Click 'Load 4 More' until the button disappears."""
    await page.goto(LISTING_URL, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    while True:
        try:
            btn = page.locator("text=/load (4 )?more/i").first
            is_visible = await btn.is_visible(timeout=2000)
            if not is_visible:
                break
            await btn.click()
            await page.wait_for_timeout(1800)
        except Exception:
            break


def parse_card(card_soup) -> Optional[dict]:
    """Extract route metadata from a single route card element."""
    # Link + slug
    link = card_soup.find('a', href=True)
    if not link:
        return None
    source_url = link['href']
    if not source_url.startswith('http'):
        source_url = BASE_URL + source_url
    slug = slugify(source_url)

    # Name
    name_el = card_soup.find(['h2', 'h3', 'h4']) or link
    name = name_el.get_text(strip=True) if name_el else slug.replace('-', ' ').title()

    # Image
    img = card_soup.find('img')
    image_url = img.get('src') or img.get('data-src') if img else None
    image_alt = img.get('alt') if img else None

    # Get all text for metadata parsing
    card_text = card_soup.get_text(' ', strip=True)

    # Distance
    distance_mi, distance_km = parse_distance(card_text)

    # Days
    days_min, days_max = parse_days(card_text)

    # Location — look for patterns like "USA, Colorado" or "Colorado, USA"
    state, country = extract_location(card_soup, card_text)

    # Geocode
    lat, lng = geocode(state, country=country)

    return {
        'slug': slug,
        'source_url': source_url,
        'name': name,
        'state': state,
        'country': country or 'USA',
        'lat': lat,
        'lng': lng,
        'distance_mi': distance_mi,
        'distance_km': distance_km,
        'days_min': days_min,
        'days_max': days_max,
        'image_url': image_url,
        'image_alt': image_alt,
    }


def extract_location(card_soup, card_text: str) -> tuple[Optional[str], Optional[str]]:
    """Heuristic to find state/country from card content."""
    # Look for location elements with common class patterns
    for cls in ['location', 'route-location', 'meta-location', 'post-location']:
        el = card_soup.find(class_=re.compile(cls, re.IGNORECASE))
        if el:
            text = el.get_text(strip=True)
            parts = [p.strip() for p in re.split(r'[,|·•]', text)]
            if len(parts) >= 2:
                return parts[0], parts[-1]
            if parts:
                return parts[0], None

    # Fallback: scan card text for US state names
    us_states = [
        'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
        'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
        'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
        'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
        'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
        'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
        'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
        'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
        'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
        'West Virginia', 'Wisconsin', 'Wyoming',
    ]
    for state in us_states:
        if state in card_text:
            return state, 'USA'
    return None, None


async def run(page: Page, limit: int | None = None, dry_run: bool = False) -> int:
    print("Pass 1: Loading all routes from listing page...")
    await load_all_routes(page)

    html = await page.content()
    soup = BeautifulSoup(html, 'lxml')

    # Try common card selectors
    cards = (
        soup.find_all(class_=re.compile(r'route.?card|post.?card|entry', re.IGNORECASE))
        or soup.find_all('article')
        or soup.find_all('li', class_=re.compile(r'route|post', re.IGNORECASE))
    )

    if not cards:
        # Broad fallback: all <a> tags linking to /routes/
        links = soup.find_all('a', href=re.compile(r'/routes/[^/]+/?$'))
        cards = [a.find_parent(['li', 'div', 'article']) or a for a in links]

    print(f"  Found {len(cards)} route cards")
    if limit:
        cards = cards[:limit]

    count = 0
    for card in cards:
        try:
            route = parse_card(card)
            if route and route.get('slug'):
                upsert_route(route, dry_run=dry_run)
                print(f"  [{count+1}] {route['name']} ({route['slug']})")
                count += 1
        except Exception as e:
            print(f"  [error] {e}")

    print(f"Pass 1 complete: {count} routes upserted")
    return count
