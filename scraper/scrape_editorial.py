"""
Pass 3: Scrape editorial roundup pages and assign Top Pick badges.

For each URL in EDITORIAL_URLS:
  - Fetch the page
  - Find all links to bikepacking.com route pages
  - Match against existing routes in Supabase by source_url
  - Upsert into editorial_features table
  - Call sync_recommendation_scores() to refresh badges
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from config import EDITORIAL_URLS, BASE_URL, USER_AGENT
from upsert import fetch_all_routes_for_editorial, upsert_editorial_feature, sync_scores

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


def fetch_page_title(soup: BeautifulSoup) -> str:
    title = soup.find('title')
    return title.get_text(strip=True) if title else ''


def find_route_links(soup: BeautifulSoup) -> list[str]:
    """Return all hrefs on the page that look like bikepacking.com route pages."""
    route_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href.startswith('http'):
            href = BASE_URL + href
        # Match paths like /routes/xxx/ or /bikepacking-routes/xxx/
        if re.search(r'bikepacking\.com/(routes|bikepacking-routes)/[^/]+/?$', href):
            route_links.append(href.rstrip('/') + '/')
    return list(set(route_links))


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.endswith('/'):
        url += '/'
    return url


def run(dry_run: bool = False) -> int:
    # Build a lookup dict: normalized source_url → route record
    all_routes = fetch_all_routes_for_editorial()
    route_lookup = {normalize_url(r['source_url']): r for r in all_routes}
    print(f"Pass 3: {len(all_routes)} routes loaded for editorial matching")

    total_badges = 0

    for editorial_url in EDITORIAL_URLS:
        print(f"\n  Fetching editorial page: {editorial_url}")
        try:
            resp = SESSION.get(editorial_url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [error] {e}")
            time.sleep(2)
            continue

        soup = BeautifulSoup(resp.text, 'lxml')
        title = fetch_page_title(soup)
        route_links = find_route_links(soup)
        print(f"  Found {len(route_links)} route links on page: {title}")

        for link in route_links:
            normalized = normalize_url(link)
            route = route_lookup.get(normalized)
            if route:
                print(f"    + Top Pick: {route['name']}")
                upsert_editorial_feature(
                    route_id=route['id'],
                    source_url=editorial_url,
                    source_title=title,
                    dry_run=dry_run,
                )
                total_badges += 1
            else:
                # Try partial match (slug)
                slug = normalized.rstrip('/').split('/')[-1]
                for src_url, r in route_lookup.items():
                    if slug in src_url:
                        print(f"    + Top Pick (slug match): {r['name']}")
                        upsert_editorial_feature(
                            route_id=r['id'],
                            source_url=editorial_url,
                            source_title=title,
                            dry_run=dry_run,
                        )
                        total_badges += 1
                        break

        time.sleep(2)

    # Refresh denormalized scores
    print(f"\nSyncing recommendation scores...")
    sync_scores(dry_run=dry_run)
    print(f"Pass 3 complete: {total_badges} editorial badges assigned")
    return total_badges
