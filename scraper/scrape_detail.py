from __future__ import annotations
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
from config import USER_AGENT, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX
from utils import (
    parse_difficulty, parse_pct, parse_elevation, parse_distance,
    parse_days, parse_days_value, parse_elevation_value, parse_difficulty_value,
    extract_bike_types, parse_tire_width, parse_best_season_months,
)
from upsert import fetch_routes_needing_detail, update_route_detail, mark_detail_scraped


SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

# Headings inside Must Know that indicate a bike recommendation section
BIKE_HEADING_RE = re.compile(
    r'ideal\s*bike|best\s*bike|bike\s*(?:choice|recommendation|setup|type|kit)|'
    r'conditions?\s+affecting|equipment|what\s+(?:to\s+)?ride|about\s+the\s+bike|'
    r'recommended\s+bike|suitable\s*bike|gear\b',
    re.IGNORECASE,
)

# Sentence contains a bike recommendation signal
BIKE_SIGNAL_RE = re.compile(
    r'hardtail|gravel\s*bike|mountain\s*bike|\bMTB\b|rigid|touring\s*bike|fat\s*bike|'
    r'full\s*sus(?:pension)?|trail\s*bike|enduro|'
    r'\b29er\b|27\.5|29\s*inch|700c|'
    r'we\s+(?:recommend|prefer|suggest|found)|recommend(?:ed)?|ideal(?:\s+for)?|'
    r'best\s+(?:suited|for|option|choice)|works?\s+(?:well|great|best)|\boptimal\b',
    re.IGNORECASE,
)

# Sentence mentions tire measurements or tire guidance
# Character class covers ASCII " ', Unicode primes ′″, and typographic curly quotes ""
TIRE_SIGNAL_RE = re.compile(
    r'\d+(?:\.\d+)?\s*(?:mm|[“′″””\'′″]|inch)|tire\s+width|tyre\s+width|'
    r'(?:wide|narrow)\s+tires?|at\s+least\s+\d|'
    r'\d+(?:\.\d+)?\s*(?:or\s+(?:larger|bigger|more|wider)|\+)\s*(?:tires?|tyres?)|'
    r'\d+\.\d+s\b|'
    r'\b\d+(?:/\d+)?c\b',
    re.IGNORECASE,
)


def fetch_html(url: str) -> Optional[str]:
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  [fetch error] {url}: {e}")
        return None


def _li_value(soup: BeautifulSoup, css_class: str) -> str:
    """
    Return the combined text value from a Bikepacking.com stat <li> element.
    Structure: <li class="cls"><div><h3>Label</h3><p>Value</p><span>(secondary)</span></div></li>
    The <span> at div level is a secondary value (e.g. metric equivalent).
    The <span> nested inside <p> (e.g. difficulty's '?') is included in p.get_text().
    """
    li = soup.find('li', class_=css_class)
    if not li:
        return ''
    div = li.find('div')
    if not div:
        return ''
    p = div.find('p')
    # Only grab spans that are direct children of div (not nested inside p)
    sibling_span = next(
        (c for c in div.children if getattr(c, 'name', None) == 'span'),
        None,
    )
    primary = p.get_text(strip=True) if p else ''
    secondary = sibling_span.get_text(strip=True) if sibling_span else ''
    return (primary + ' ' + secondary).strip()


def parse_stat_block(soup: BeautifulSoup) -> dict:
    """
    Extract numeric stats using Bikepacking.com's <li class="stat-name"> structure.
    Each stat lives in a dedicated li: li.distance, li.ascent, li.days, li.difficulty,
    li.unpaved, li.singletrack, li.highpoint, li.rideability.
    """
    result = {}

    # Distance: <p>142 Mi.</p><span>(229 KM)</span>
    dist = _li_value(soup, 'distance')
    if dist:
        mi, km = parse_distance(dist)
        if mi: result['distance_mi'] = mi
        if km: result['distance_km'] = km

    # Ascent: <p>16,390'</p><span>(4,996 M)</span>  — elevation uses ' not ft
    ascent = _li_value(soup, 'ascent')
    if ascent:
        ft, m = parse_elevation_value(ascent)
        if ft: result['elevation_gain_ft'] = ft
        if m: result['elevation_gain_m'] = m

    # High Point: same format as ascent
    hp = _li_value(soup, 'highpoint')
    if hp:
        ft, m = parse_elevation_value(hp)
        if ft: result['high_point_ft'] = ft
        if m: result['high_point_m'] = m

    # Days: <p>4</p> or <p>5-8</p>  — bare number, no "days" keyword
    days = _li_value(soup, 'days')
    if days:
        days_min, days_max = parse_days_value(days)
        if days_min:
            result['days_min'] = days_min
            result['days_max'] = days_max

    # Difficulty: <p>6<span>?</span></p>  — bare number, possibly with trailing '?'
    diff = _li_value(soup, 'difficulty')
    if diff:
        d = parse_difficulty_value(diff)
        if d: result['difficulty'] = d

    # Percentages
    for field, cls in [
        ('unpaved_pct', 'unpaved'),
        ('singletrack_pct', 'singletrack'),
        ('rideable_pct', 'rideability'),
    ]:
        val = _li_value(soup, cls)
        if val:
            pct = parse_pct(val)
            if pct is not None: result[field] = pct

    return result


def _find_must_know_div(soup: BeautifulSoup):
    """
    Return the element containing Must Know tab content.
    Tries multiple HTML structures used by bikepacking.com.
    """
    MUST_KNOW_RE = re.compile(r'when\s+to\s+go|ideal\s+bike|tire\s+width', re.IGNORECASE)

    # 1. div.inner with Must Know content (original structure)
    for div in soup.find_all('div', class_='inner'):
        if MUST_KNOW_RE.search(div.get_text()):
            return div

    # 2. Tab referenced by "Must Know" nav item
    tabs_nav = soup.find('ul', id='tabs')
    if tabs_nav:
        for li in tabs_nav.find_all('li'):
            if re.search(r'must.?know', li.get_text(), re.IGNORECASE):
                rel_attr = li.attrs.get('rel', '')
                if isinstance(rel_attr, list):
                    rel_attr = ' '.join(rel_attr)
                tab_id = re.search(r'tab-\d+', rel_attr)
                if tab_id:
                    found = soup.find(id=tab_id.group(0))
                    if found:
                        return found

    # 3. Any div/section that contains both an "Ideal Bike" heading and substantive text
    for tag in soup.find_all(['div', 'section']):
        if MUST_KNOW_RE.search(tag.get_text()):
            # Prefer a container that isn't too large (< 5000 chars of text)
            text = tag.get_text()
            if len(text) < 5000:
                return tag

    return None


def _walk_must_know_sections(el) -> dict:
    """
    Walk subheadings in the Must Know element and return a dict
    {'bike': text, 'tire': text, 'season': text} based on heading keywords.

    Handles two heading formats used by bikepacking.com:
      1. Block headings: <h4>When to go</h4><ul><li>...</li></ul>
      2. Inline labels: <li><strong>When to go:</strong> ...</li>
    """
    sections: dict = {}
    HEADING_TAGS = ('h2', 'h3', 'h4', 'h5', 'dt')

    # Format 1: block headings (h2-h5, dt) with following sibling content
    for heading in el.find_all(HEADING_TAGS):
        htext = heading.get_text(strip=True)
        if len(htext) > 100:
            continue

        parts = []
        for sib in heading.find_next_siblings():
            if sib.name in HEADING_TAGS:
                break
            t = sib.get_text(' ', strip=True)
            if t:
                parts.append(t)
        content = ' '.join(parts).strip()
        if not content:
            continue

        if BIKE_HEADING_RE.search(htext):
            sections.setdefault('bike', content)
        elif re.search(r'tire|tyre|wheel\s+size', htext, re.IGNORECASE):
            sections.setdefault('tire', content)
        elif re.search(r'when\s+to\s+go|season|best\s+time|weather', htext, re.IGNORECASE):
            sections.setdefault('season', content)

    # Format 2: inline strong labels inside <li> or <p> elements
    # e.g. <li><strong>When to go:</strong> text here...</li>
    # Also handles cases where the strong IS the full statement:
    # <li><strong>Ideal riding season is August – October.</strong> Other text.</li>
    for container in el.find_all(['li', 'p']):
        strong = container.find('strong')
        if not strong:
            continue
        label = strong.get_text(strip=True).rstrip(':').lower()
        if len(label) > 80:
            continue  # too long to be a label

        full_text = container.get_text(' ', strip=True)
        label_raw = strong.get_text(strip=True)
        # Stripped content = text after the label (for bike/tire where label is just a heading)
        content = re.sub(r'^\s*' + re.escape(label_raw) + r'\s*:?\s*', '', full_text, flags=re.IGNORECASE).strip()

        if re.search(r'when\s+to\s+go|season|best\s+time|weather', label, re.IGNORECASE):
            # For season: use full_text so months embedded in the strong tag are captured
            season_text = full_text if len(full_text) > 10 else content
            if season_text:
                sections.setdefault('season', season_text)
        elif BIKE_HEADING_RE.search(label):
            if content and len(content) >= 15:
                sections.setdefault('bike', content)
        elif re.search(r'tire|tyre|wheel\s+size', label, re.IGNORECASE):
            if content and len(content) >= 15:
                sections.setdefault('tire', content)

    return sections


def _split_sentences(text: str) -> list:
    text = re.sub(r'\s+', ' ', text).strip()
    return re.split(r'(?<=[.!?])\s+(?=[A-Z""])', text)


def _extract_bike_sentence(text: str) -> str:
    """Return the sentence(s) from text that describe the bike recommendation."""
    sentences = _split_sentences(text)
    hits = [s for s in sentences if BIKE_SIGNAL_RE.search(s)]
    return ' '.join(hits).strip() if hits else text.strip()


def _extract_tire_sentence(text: str) -> str:
    """Return sentence(s) from text that mention tire measurements.
    Prefers sentences with parseable widths over generic 'tire width' mentions
    (e.g. avoids logistics sentences like 'Amtrak tire width regulations...')."""
    sentences = _split_sentences(text)
    # Pass 1: sentences that both signal AND have a parseable measurement
    hits = [s for s in sentences if TIRE_SIGNAL_RE.search(s) and parse_tire_width(s)[0]]
    if hits:
        return ' '.join(hits).strip()
    # Pass 2: any sentence with a tire signal (fallback)
    hits = [s for s in sentences if TIRE_SIGNAL_RE.search(s)]
    return ' '.join(hits).strip() if hits else ''


def parse_must_know(soup: BeautifulSoup) -> dict:
    """
    Extract best_season, ideal_bike, and tire width from the Must Know tab.
    Uses section-walking to handle headings like "Conditions affecting bike choice".
    Falls back to label-pattern matching and whole-page search.
    """
    result = {}
    must_know_div = _find_must_know_div(soup)
    search_el = must_know_div or soup

    # ── Section walker: handles any heading variant ───────────────
    sections = _walk_must_know_sections(search_el)

    # Bike section (may contain both bike recommendation and tire info)
    bike_text = sections.get('bike', '')
    if bike_text:
        ideal = _extract_bike_sentence(bike_text)
        if ideal and len(ideal) > 5:
            result['ideal_bike'] = ideal
        w_min, w_max = parse_tire_width(bike_text)
        if w_min:
            result['tire_width_min_mm'] = w_min
            result['tire_width_max_mm'] = w_max or w_min
        tire_sent = _extract_tire_sentence(bike_text)
        if tire_sent:
            result['tire_width_notes'] = tire_sent

    # Explicit tire section (separate heading)
    tire_text = sections.get('tire', '')
    if tire_text:
        if 'tire_width_min_mm' not in result:
            w_min, w_max = parse_tire_width(tire_text)
            if w_min:
                result['tire_width_min_mm'] = w_min
                result['tire_width_max_mm'] = w_max or w_min
        if 'tire_width_notes' not in result and len(tire_text) > 10:
            result['tire_width_notes'] = tire_text

    # Season section
    season_text = sections.get('season', '')
    if season_text:
        result['best_season'] = season_text
        months = parse_best_season_months(season_text)
        if months:
            result['best_season_months'] = months

    # ── Fallbacks for pages without matched headings ──────────────
    text = search_el.get_text(' ', strip=True)

    # Ideal bike: explicit label "Ideal Bike:" or "Best Bike:"
    if 'ideal_bike' not in result:
        for tag in search_el.find_all(['p', 'li']):
            tag_text = tag.get_text(' ', strip=True)
            m = re.search(r'(?:best|ideal)\s*bike[:\s]+(.+)', tag_text, re.IGNORECASE)
            if m and len(m.group(1).strip()) > 5:
                result['ideal_bike'] = m.group(1).strip()
                break

    if 'ideal_bike' not in result:
        for heading in search_el.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'dt', 'strong']):
            htext = heading.get_text(strip=True)
            if re.search(r'ideal\s*bike', htext, re.IGNORECASE) and len(htext) < 40:
                parts = []
                for sib in heading.find_next_siblings():
                    if sib.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'dt'):
                        break
                    sib_text = sib.get_text(' ', strip=True)
                    if sib_text and len(sib_text) > 5:
                        parts.append(sib_text)
                    if len(' '.join(parts)) > 600:
                        break
                if parts:
                    result['ideal_bike'] = ' '.join(parts)[:600]
                    break

    if 'ideal_bike' not in result:
        m = re.search(r'(?:best|ideal)\s*bike[:\s]+(.{10,800})', text, re.IGNORECASE | re.DOTALL)
        if m:
            ideal_text = m.group(1).strip()
            for stop in [r'\s+When\s+to\b', r'\s+Best\s+time\b', r'\s{2,}[A-Z][A-Za-z ]{3,}']:
                ideal_text = re.split(stop, ideal_text, flags=re.IGNORECASE)[0].strip()
            if 5 < len(ideal_text) < 600:
                result['ideal_bike'] = ideal_text

    # Tire width: scan tire-mentioning elements
    if 'tire_width_min_mm' not in result:
        tire_sections: list = []
        for tag in search_el.find_all(['p', 'li', 'div']):
            p_text = tag.get_text(' ', strip=True)
            if re.search(r'tire|tyre|wheel|mm|\d+["\']', p_text, re.IGNORECASE) and len(p_text) < 600:
                tire_sections.append(p_text)
        tire_sections.append(text)
        for section in tire_sections:
            w_min, w_max = parse_tire_width(section)
            if w_min:
                result['tire_width_min_mm'] = w_min
                result['tire_width_max_mm'] = w_max or w_min
                break

    # Tire width notes: "Tire Width:" label pattern
    if 'tire_width_notes' not in result:
        tn_match = re.search(r'[Tt]ire\s+[Ww]idth[:\s]+(.+?)(?=\s{2,}[A-Z][A-Za-z ]|\Z)', text, re.DOTALL)
        if tn_match:
            notes = re.sub(r'\s+', ' ', tn_match.group(1)).strip()
            notes = re.split(
                r'\s+(?:Best\s+(?:bike|time|season)|When\s+to\s+go|Resupply|Ideal\s+[Bb]ike)',
                notes, flags=re.IGNORECASE
            )[0].strip()
            if len(notes) > 10:
                result['tire_width_notes'] = notes

    # Season: regex fallback for "When to Go" not picked up as heading
    if 'best_season' not in result:
        # [:\s]+ handles both "When to go:" (inline label) and "When to go " (heading-follower)
        when_match = (
            re.search(r'when\s+to\s+go[:\s]+(.{20,500})', text, re.IGNORECASE | re.DOTALL)
            or re.search(r'best\s+time[:\s]+(.{20,500})', text, re.IGNORECASE | re.DOTALL)
        )
        if when_match:
            season_text = when_match.group(1).strip()
            season_text = re.split(r'\s{2,}[A-Z][A-Za-z ]{2,20}\s{2,}', season_text)[0][:300].strip()
            result['best_season'] = season_text
            months = parse_best_season_months(season_text)
            if months:
                result['best_season_months'] = months

    return result


def parse_difficulty2(soup: BeautifulSoup) -> dict:
    """
    Extract the four sub-difficulty ratings from div.difficulty2.
    Structure: <li><div style="background-color:COLOR">SCORE</div>Category Name <span>Label</span></li>
    Score is '-' (and background is #cccccc) when not filled in.
    """
    result = {}
    d2 = soup.find('div', class_='difficulty2')
    if not d2:
        return result

    field_map = {
        'climbing scale': 'climbing_scale',
        'technical difficulty': 'technical_difficulty',
        'physical demand': 'physical_demand',
        'resupply': 'resupply_logistics',  # "Resupply & Logistics"
    }

    for li in d2.find_all('li'):
        score_div = li.find('div')
        if not score_div:
            continue
        score_text = score_div.get_text(strip=True)
        if score_text == '-':
            continue
        try:
            score = float(score_text)
        except ValueError:
            continue
        if not (1 <= score <= 10):
            continue
        li_text = li.get_text(' ', strip=True).lower()
        for keyword, field in field_map.items():
            if keyword in li_text:
                result[field] = score
                break

    return result


def parse_rwgps_embed(soup: BeautifulSoup) -> dict:
    """Extract Ride with GPS embed URL and route ID from the page's iframe."""
    result = {}
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '')
        # Matches: ridewithgps.com/embeds?type=route&id=12345678
        match = re.search(r'ridewithgps\.com/embeds[^"\']*type=route[^"\']*id=(\d+)', src, re.IGNORECASE)
        if not match:
            # Also try: ridewithgps.com/routes/12345678/embed
            match = re.search(r'ridewithgps\.com/routes/(\d+)/embed', src, re.IGNORECASE)
        if match:
            route_id = match.group(1)
            result['rwgps_route_id'] = route_id
            # Normalize to standard embed URL
            result['rwgps_embed_url'] = f'https://ridewithgps.com/embeds?type=route&id={route_id}&sampleGraph=true'
            break
    return result


def parse_editorial_body(soup: BeautifulSoup) -> dict:
    """
    Scan ALL page paragraphs for bike type, tire width, and bike recommendations.
    Uses full-page scan so info in Difficulty, Conditions, or any other section is found,
    not just the article body or Must Know tab.
    """
    result = {}

    # Bike type: use article/content container to avoid nav false-positives
    article = (
        soup.find('article')
        or soup.find(class_=re.compile(r'entry.?content|post.?content|content', re.IGNORECASE))
        or soup
    )
    body_text = article.get_text(' ', strip=True)
    bike_types = extract_bike_types(body_text)
    if bike_types:
        result['bike_type'] = bike_types

    # For tire width and ideal bike: scan ALL page paragraphs.
    # Info may appear in Route Difficulty, Conditions, or other sections outside the article.
    all_paragraphs = soup.find_all(['p', 'li'])

    # Tire width: split each tire-mentioning paragraph into sentences, collect all widths
    for p in all_paragraphs:
        p_text = p.get_text(' ', strip=True)
        if len(p_text) < 20 or len(p_text) > 800:
            continue
        if not re.search(r'tire|tyre|wheel', p_text, re.IGNORECASE):
            continue
        widths: list = []
        for sent in _split_sentences(p_text):
            w_min, w_max = parse_tire_width(sent)
            if w_min:
                widths.extend([w_min, w_max or w_min])
        if widths:
            result['tire_width_min_mm'] = min(widths)
            result['tire_width_max_mm'] = max(widths)
            tire_sent = _extract_tire_sentence(p_text)
            result['_tire_width_notes_from_body'] = tire_sent or p_text[:500]
            break

    # Ideal bike fallback — two-pass:
    # Pass 1: prefer paragraphs with BOTH a bike signal AND a tire/equipment signal
    #         (avoids picking up "we suggest" in unrelated contexts like food)
    # Pass 2: any paragraph with a bike signal alone
    bike_para: Optional[str] = None
    for pass_num in (1, 2):
        for p in all_paragraphs:
            p_text = p.get_text(' ', strip=True)
            if len(p_text) < 20 or len(p_text) > 800:
                continue
            has_bike = BIKE_SIGNAL_RE.search(p_text)
            has_tire = TIRE_SIGNAL_RE.search(p_text)
            if pass_num == 1 and not (has_bike and has_tire):
                continue
            if pass_num == 2 and not has_bike:
                continue
            extracted = _extract_bike_sentence(p_text)
            if extracted:
                bike_para = extracted
                break
        if bike_para:
            break

    if bike_para:
        result['_ideal_bike_from_body'] = bike_para

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
    result.update(parse_difficulty2(soup))
    result.update(parse_must_know(soup))  # sets ideal_bike, tire_width_*, best_season (highest priority)

    editorial = parse_editorial_body(soup)
    # ideal_bike: Must Know wins; editorial body is fallback only
    if 'ideal_bike' not in result:
        body_ideal = editorial.pop('_ideal_bike_from_body', None)
        if body_ideal:
            result['ideal_bike'] = body_ideal
    else:
        editorial.pop('_ideal_bike_from_body', None)
    # tire_width_notes: Must Know wins; body fallback
    if 'tire_width_notes' not in result:
        body_notes = editorial.pop('_tire_width_notes_from_body', None)
        if body_notes:
            result['tire_width_notes'] = body_notes
    else:
        editorial.pop('_tire_width_notes_from_body', None)
    # tire_width min/max: Must Know wins
    for k in ('tire_width_min_mm', 'tire_width_max_mm'):
        if k in result:
            editorial.pop(k, None)
    result.update(editorial)

    result.update(parse_rwgps_embed(soup))
    desc = parse_description(soup)
    if desc:
        result['description'] = desc
    return result


# Fields that --force-all explicitly nulls out so stale scrapes are fully replaced
_RESCRAPE_FIELDS = [
    'ideal_bike', 'tire_width_min_mm', 'tire_width_max_mm', 'tire_width_notes',
    'best_season', 'best_season_months',
]


def run(limit: int | None = None, dry_run: bool = False,
        force_null_fields: bool = False, force_all: bool = False) -> int:
    routes = fetch_routes_needing_detail(limit=limit, force_null_fields=force_null_fields,
                                         force_all=force_all)
    mode = 'ALL routes' if force_all else ('null-field routes' if force_null_fields else 'unscraped routes')
    print(f"Pass 2: Enriching {len(routes)} {mode} from detail pages...")

    count = 0
    for i, route in enumerate(routes):
        url = route['source_url']
        print(f"  [{i+1}/{len(routes)}] {route['name']} — {url}")

        detail = scrape_route_page(url)

        # When force_all, explicitly null fields that weren't found so stale data is cleared
        if force_all:
            for field in _RESCRAPE_FIELDS:
                if field not in detail:
                    detail[field] = None

        if detail:
            # Merge ideal_bike-inferred types with existing bike_type from Pass 1
            ideal_types = detail.pop('_ideal_bike_types', [])
            if ideal_types:
                existing = set(route.get('bike_type') or [])
                merged = sorted(existing | set(ideal_types))
                if merged:
                    detail['bike_type'] = merged

            update_route_detail(route['slug'], detail, dry_run=dry_run)
            if not dry_run:
                mark_detail_scraped(route['id'])
            count += 1

        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    print(f"Pass 2 complete: {count} routes enriched")
    return count
