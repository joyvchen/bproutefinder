from __future__ import annotations
"""
Pass 1: Discover routes via bikepacking.com's XML sitemap.

Location is read directly from each route page's `div.loc` element, which
contains authoritative `/locations/[slug]/` links. No pre-built lookup table
or static region map needed — the page itself is the source of truth.
"""
import re
import time
import random
from typing import Optional
import requests
from bs4 import BeautifulSoup
from config import BASE_URL, USER_AGENT, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX
from utils import parse_distance, parse_days, slugify
from geocode import geocode
from upsert import upsert_route

TYPE_PAGE_SLUGS: dict[str, str] = {
    'singletrack': 'hardtail',
    'gravel': 'gravel',
    'dirt-tour': 'touring',
    'fatbike': 'fat-bike',
}

# Content pages that live under /routes/ or /bikepacking-routes/ but are not actual routes.
ROUTE_SLUG_BLOCKLIST: set[str] = {
    'access-fund',
    'route-difficulty',
}


def build_bike_type_lookup() -> dict[str, list[str]]:
    """Return {route_slug: [bike_types]} from all pages of the 4 bikepacking.com type pages."""
    lookup: dict[str, set] = {}
    for type_slug, bike_type in TYPE_PAGE_SLUGS.items():
        page_num = 1
        while True:
            url = (
                f"{BASE_URL}/type/{type_slug}/" if page_num == 1
                else f"{BASE_URL}/type/{type_slug}/page/{page_num}/"
            )
            try:
                resp = SESSION.get(url, timeout=15)
                if resp.status_code in (404, 410):
                    break
                resp.raise_for_status()
            except Exception as e:
                print(f"  [warn] Could not fetch {url}: {e}", flush=True)
                break
            soup = BeautifulSoup(resp.text, 'lxml')
            slugs_on_page: set[str] = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if not href.startswith('http'):
                    href = BASE_URL + href
                if ROUTE_PATH_RE.search(href):
                    slugs_on_page.add(href.rstrip('/').split('/')[-1])
            if not slugs_on_page:
                break
            for slug in slugs_on_page:
                lookup.setdefault(slug, set()).add(bike_type)
            print(f"  Type page {type_slug} p{page_num}: {len(slugs_on_page)} routes", flush=True)
            page_num += 1
            time.sleep(0.5)
        print(f"  Type {type_slug} total: {sum(1 for s in lookup.values() if bike_type in s)} routes", flush=True)
    return {slug: sorted(types) for slug, types in lookup.items()}


SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
})

ROUTE_PATH_RE = re.compile(r'bikepacking\.com/(routes|bikepacking-routes)/[^/]+/?$')
LOCATION_HREF_RE = re.compile(r'/locations/([^/]+)/?$')

# Slug → proper state name for all 50 US states.
US_STATE_SLUGS: dict[str, str] = {
    'alabama': 'Alabama', 'alaska': 'Alaska', 'arizona': 'Arizona',
    'arkansas': 'Arkansas', 'california': 'California', 'colorado': 'Colorado',
    'connecticut': 'Connecticut', 'delaware': 'Delaware', 'florida': 'Florida',
    'georgia': 'Georgia', 'hawaii': 'Hawaii', 'idaho': 'Idaho',
    'illinois': 'Illinois', 'indiana': 'Indiana', 'iowa': 'Iowa',
    'kansas': 'Kansas', 'kentucky': 'Kentucky', 'louisiana': 'Louisiana',
    'maine': 'Maine', 'maryland': 'Maryland', 'massachusetts': 'Massachusetts',
    'michigan': 'Michigan', 'minnesota': 'Minnesota', 'mississippi': 'Mississippi',
    'missouri': 'Missouri', 'montana': 'Montana', 'nebraska': 'Nebraska',
    'nevada': 'Nevada', 'new-hampshire': 'New Hampshire', 'new-jersey': 'New Jersey',
    'new-mexico': 'New Mexico', 'new-york': 'New York',
    'north-carolina': 'North Carolina', 'north-dakota': 'North Dakota',
    'ohio': 'Ohio', 'oklahoma': 'Oklahoma', 'oregon': 'Oregon',
    'pennsylvania': 'Pennsylvania', 'rhode-island': 'Rhode Island',
    'south-carolina': 'South Carolina', 'south-dakota': 'South Dakota',
    'tennessee': 'Tennessee', 'texas': 'Texas', 'utah': 'Utah',
    'vermont': 'Vermont', 'virginia': 'Virginia', 'washington': 'Washington',
    'west-virginia': 'West Virginia', 'wisconsin': 'Wisconsin', 'wyoming': 'Wyoming',
}

CANADA_PROVINCE_SLUGS: dict[str, str] = {
    'alberta': 'Alberta', 'british-columbia': 'British Columbia',
    'maritimes': 'Maritimes', 'ontario': 'Ontario',
    'quebec': 'Quebec', 'saskatchewan': 'Saskatchewan',
}

UK_REGION_SLUGS: dict[str, str] = {
    'england': 'England', 'scotland': 'Scotland', 'wales': 'Wales',
}

# Specificity levels for slugs that aren't states/provinces/UK regions.
# Slugs not listed here default to 3 (country level).
LOCATION_SPECIFICITY: dict[str, int] = {
    # 0 — broadest continents and regions
    'africa': 0, 'asia': 0, 'europe': 0, 'middle-east': 0,
    'north-america': 0, 'oceania': 0,
    'latin-america': 0,
    # 1 — sub-continental regions (more specific than their parent continent)
    'south-america': 1, 'central-america': 1,
    'central-asia': 1, 'east-africa': 1, 'east-asia': 1,
    'eastern-europe': 1, 'north-africa': 1,
    # 2 — country-level aggregators
    'usa': 2, 'canada': 2,
}

# Slugs whose auto-generated country name (slug.replace('-',' ').title()) would be wrong.
SLUG_COUNTRY_OVERRIDES: dict[str, str] = {
    'bikepacking-mexico': 'Mexico',
    'india-himalayas': 'India',
    'new-zealand': 'New Zealand',
    'south-africa': 'South Africa',
    'usa': 'USA',
    'canada': 'Canada',
}

# Fallback: country names that appear in route titles (for routes without div.loc).
TITLE_COUNTRIES = [
    'Mongolia', 'Switzerland', 'Ireland', 'France', 'Germany', 'Spain', 'Italy',
    'Austria', 'Netherlands', 'Belgium', 'Czech Republic', 'Slovakia', 'Slovenia',
    'Albania', 'Croatia', 'Portugal', 'Norway', 'Sweden', 'Iceland', 'Denmark',
    'Greece', 'Cyprus', 'Greenland', 'UK', 'United Kingdom',
    'Canada', 'Mexico', 'Argentina', 'Bolivia', 'Peru', 'Ecuador', 'Colombia',
    'Chile', 'Brazil', 'Costa Rica', 'Guatemala', 'New Zealand', 'Australia',
    'Japan', 'Nepal', 'Kyrgyzstan', 'Kazakhstan', 'Turkey', 'Morocco',
    'South Africa', 'Kenya', 'Tanzania', 'Rwanda', 'Ethiopia', 'Georgia',
]

US_STATE_NAMES = list(US_STATE_SLUGS.values())


def classify_location_slug(slug: str) -> tuple[Optional[str], Optional[str], int]:
    """Return (state, country, specificity). Higher specificity = more specific location."""
    if slug in US_STATE_SLUGS:
        return US_STATE_SLUGS[slug], 'USA', 4
    if slug in CANADA_PROVINCE_SLUGS:
        return CANADA_PROVINCE_SLUGS[slug], 'Canada', 4
    if slug in UK_REGION_SLUGS:
        return UK_REGION_SLUGS[slug], 'UK', 4
    spec = LOCATION_SPECIFICITY.get(slug, 3)
    country = SLUG_COUNTRY_OVERRIDES.get(slug) or slug.replace('-', ' ').title()
    return None, country, spec


def resolve_route_locations(
    slug_set: set,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Given all location slugs for a route, return (state, country, region).

    Sorts slugs by specificity descending:
    - Most specific slug → state + country
    - Next slug whose resolved name differs → region

    Examples:
      {turkey, europe}            → Turkey, Europe
      {australia, oceania}        → Australia, Oceania
      {colorado, usa, north-america} → Colorado/USA, North America
      {central-america, latin-america} → Central America, Latin America
    """
    if not slug_set:
        return None, None, None

    classified = []
    for slug in slug_set:
        state, country, spec = classify_location_slug(slug)
        classified.append((spec, slug, state, country))
    classified.sort(key=lambda x: x[0], reverse=True)  # most specific first

    _, _, state, country = classified[0]

    region = None
    for _, _, _, c in classified[1:]:
        if c and c != country:
            region = c
            break

    return state, country, region


def extract_location_from_page(
    soup: BeautifulSoup,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Read location directly from the route page's div.loc element.

    bikepacking.com renders this as static HTML on every route page:
      <div class="loc">
        <a href="/locations/australia/">Australia</a>,
        <a href="/locations/oceania/">Oceania</a>
      </div>

    Extracts the slugs from href attributes and resolves via resolve_route_locations.
    """
    loc_div = soup.find('div', class_='loc')
    if not loc_div:
        return None, None, None
    slug_set = set()
    for a in loc_div.find_all('a', href=True):
        m = LOCATION_HREF_RE.search(a['href'])
        if m:
            slug_set.add(m.group(1))
    if not slug_set:
        return None, None, None
    return resolve_route_locations(slug_set)


def location_from_name(name: str) -> tuple[Optional[str], Optional[str]]:
    """
    Fallback: extract state/country from route title when div.loc is absent.
    Checks country names before US states to avoid ambiguity (e.g. Georgia).
    """
    name_lower = name.lower()
    for country in TITLE_COUNTRIES:
        if country.lower() in name_lower:
            return None, country
    for state in US_STATE_NAMES:
        if state in name:
            return state, 'USA'
    return None, None


def fetch_route_urls_from_sitemap() -> list[str]:
    """Discover all route URLs from bikepacking.com's XML sitemap index."""
    sitemap_index_url = f"{BASE_URL}/sitemap.xml"
    print(f"  Fetching sitemap index: {sitemap_index_url}", flush=True)

    try:
        resp = SESSION.get(sitemap_index_url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [error] Could not fetch sitemap index: {e}", flush=True)
        return []

    soup = BeautifulSoup(resp.text, 'lxml')
    sub_sitemaps = [loc.get_text(strip=True) for loc in soup.find_all('loc')]
    print(f"  Found {len(sub_sitemaps)} sub-sitemaps to scan", flush=True)

    route_urls: list[str] = []
    for sitemap_url in sub_sitemaps:
        try:
            resp = SESSION.get(sitemap_url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [warn] Skipping {sitemap_url}: {e}", flush=True)
            continue

        sub_soup = BeautifulSoup(resp.text, 'lxml')
        locs = [loc.get_text(strip=True) for loc in sub_soup.find_all('loc')]
        found = [
            u.rstrip('/') + '/' for u in locs
            if ROUTE_PATH_RE.search(u) and u.rstrip('/').split('/')[-1] not in ROUTE_SLUG_BLOCKLIST
        ]
        if found:
            print(f"    {sitemap_url}: {len(found)} routes", flush=True)
            route_urls.extend(found)
        time.sleep(0.3)

    unique_urls = list(set(route_urls))
    print(f"  Total: {len(unique_urls)} unique route URLs discovered", flush=True)
    return unique_urls


def scrape_route_basic(url: str, bike_type_lookup: dict | None = None) -> Optional[dict]:
    """Fetch a route page and extract basic metadata."""
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"    [error] {e}", flush=True)
        return None

    soup = BeautifulSoup(resp.text, 'lxml')
    slug = slugify(url)

    # Name
    h1 = soup.find('h1')
    title_el = soup.find('title')
    if h1:
        name = h1.get_text(strip=True)
    elif title_el:
        name = title_el.get_text(strip=True).split('|')[0].strip()
    else:
        name = slug.replace('-', ' ').title()

    # Image — prefer OG image tag
    og_image = soup.find('meta', property='og:image')
    image_url: Optional[str] = og_image['content'] if og_image and og_image.get('content') else None
    if not image_url:
        img = soup.find('img')
        if img:
            image_url = img.get('src') or img.get('data-src')

    # Location: read from div.loc on the page, fall back to name heuristic
    state, country, region = extract_location_from_page(soup)
    if not country:
        state, country = location_from_name(name)

    # Distance/days from page text — numeric patterns are unambiguous
    page_text = soup.get_text(' ', strip=True)[:4000]
    distance_mi, distance_km = parse_distance(page_text)
    days_min, days_max = parse_days(page_text)
    lat, lng = geocode(state, country=country)

    route: dict = {
        'slug': slug,
        'source_url': url.rstrip('/') + '/',
        'name': name,
        'state': state,
        'country': country,
        'region': region,
        'lat': lat,
        'lng': lng,
        'distance_mi': distance_mi,
        'distance_km': distance_km,
        'image_url': image_url,
    }
    # Only write days if found — never overwrite detail-scraped values with None
    if days_min is not None:
        route['days_min'] = days_min
        route['days_max'] = days_max
    if bike_type_lookup is not None:
        bike_types = bike_type_lookup.get(slug)
        if bike_types:
            route['bike_type'] = bike_types
    return route


def run(limit: int | None = None, dry_run: bool = False) -> int:
    print("Pass 1: Discovering routes via sitemap...", flush=True)

    urls = fetch_route_urls_from_sitemap()
    if not urls:
        print("  [warn] No route URLs found. Check sitemap structure.", flush=True)
        return 0

    if limit:
        urls = urls[:limit]
        print(f"  Limiting to {limit} routes for this run", flush=True)

    print("  Building bike type lookup from type pages...", flush=True)
    bike_type_lookup = build_bike_type_lookup()
    print(f"  Bike type lookup: {len(bike_type_lookup)} routes with known type", flush=True)

    count = 0
    for i, url in enumerate(urls):
        print(f"  [{i+1}/{len(urls)}] {url}", flush=True)
        route = scrape_route_basic(url, bike_type_lookup)
        if route and route.get('slug'):
            if dry_run:
                print(
                    f"    DRY RUN: {route['name']} "
                    f"| state={route.get('state')} country={route.get('country')} "
                    f"region={route.get('region')} "
                    f"| lat={route.get('lat')} "
                    f"| {route.get('distance_mi')} mi"
                    f"| bike_type={route.get('bike_type')}",
                    flush=True,
                )
            else:
                upsert_route(route, dry_run=False)
            count += 1

        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    print(f"Pass 1 complete: {count} routes upserted", flush=True)
    return count
