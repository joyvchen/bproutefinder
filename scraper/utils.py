"""Parsing helpers for scraped text."""
import re
from typing import Optional


def parse_distance(text: str) -> tuple[Optional[float], Optional[float]]:
    """Extract (miles, km) from strings like '247 MI (398 KM)' or '247 miles'."""
    mi, km = None, None
    mi_match = re.search(r'([\d,]+(?:\.\d+)?)\s*mi(?:les?)?', text, re.IGNORECASE)
    km_match = re.search(r'([\d,]+(?:\.\d+)?)\s*km', text, re.IGNORECASE)
    if mi_match:
        mi = float(mi_match.group(1).replace(',', ''))
    if km_match:
        km = float(km_match.group(1).replace(',', ''))
    return mi, km


def parse_days(text: str) -> tuple[Optional[int], Optional[int]]:
    """Extract (days_min, days_max) from strings like '5-8 days' or '5 days'."""
    range_match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*days?', text, re.IGNORECASE)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    single_match = re.search(r'(\d+)\s*days?', text, re.IGNORECASE)
    if single_match:
        d = int(single_match.group(1))
        return d, d
    return None, None


def parse_elevation(text: str) -> tuple[Optional[int], Optional[int]]:
    """Extract (ft, m) from strings like '24,000 ft (7,315 m)'."""
    ft, m = None, None
    ft_match = re.search(r'([\d,]+)\s*ft', text, re.IGNORECASE)
    m_match = re.search(r'([\d,]+)\s*m\b', text, re.IGNORECASE)
    if ft_match:
        ft = int(ft_match.group(1).replace(',', ''))
    if m_match:
        m = int(m_match.group(1).replace(',', ''))
    return ft, m


def parse_difficulty(text: str) -> Optional[float]:
    """Extract numeric difficulty from '6.5/10' or '7 out of 10'."""
    match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    match = re.search(r'(\d+(?:\.\d+)?)\s*out\s*of\s*10', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    # Bare number in a field labeled "difficulty"
    match = re.search(r'^(\d+(?:\.\d+)?)$', text.strip())
    if match:
        val = float(match.group(1))
        if 1 <= val <= 10:
            return val
    return None


def parse_pct(text: str) -> Optional[int]:
    """Extract integer percentage from '87%' or '87 percent'."""
    match = re.search(r'(\d+)\s*%', text)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)\s*percent', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def parse_tire_width(text: str) -> tuple[Optional[int], Optional[int]]:
    """
    Extract (min_mm, max_mm) from tire width strings in editorial body text.
    Handles: '700x40-55c', '2.2-2.4"', '40-55mm', '2.35"', '700x50c'
    Returns widths in mm (approximate conversion for inch sizes).
    """
    # 700xNNc or 700xNN-NNc format (road/gravel)
    match = re.search(r'700\s*[xX×]\s*(\d+)(?:-(\d+))?c?', text)
    if match:
        lo = int(match.group(1))
        hi = int(match.group(2)) if match.group(2) else lo
        return lo, hi

    # NNmm or NN-NNmm
    match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*mm', text, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.search(r'(\d+)\s*mm', text, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(1))

    # Inch sizes (MTB): 2.2-2.4" → approximate mm (multiply by 25.4)
    match = re.search(r'(\d+\.\d+)\s*[-–]\s*(\d+\.\d+)\s*["\']', text)
    if match:
        lo = round(float(match.group(1)) * 25.4)
        hi = round(float(match.group(2)) * 25.4)
        return lo, hi
    match = re.search(r'(\d+\.\d+)\s*["\']', text)
    if match:
        w = round(float(match.group(1)) * 25.4)
        return w, w

    return None, None


BIKE_TYPE_KEYWORDS = {
    'gravel': ['gravel bike', 'gravel bicycle', 'gravel-specific'],
    'hardtail': ['hardtail', 'hard tail', 'xc bike', 'cross-country'],
    'full-sus': [
        'full suspension', 'full-suspension', 'full sus', 'enduro bike',
        'trail bike', 'all-mountain',
    ],
    'road': ['road bike', 'road bicycle'],
    'touring': ['touring bike', 'bikepacking bike', 'adventure bike'],
    'fat-bike': ['fat bike', 'fat-bike', 'fat tire'],
}


def extract_bike_types(text: str) -> list[str]:
    """Scan editorial body text and return a list of matching bike type tokens."""
    text_lower = text.lower()
    found = []
    for bike_type, keywords in BIKE_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(bike_type)
    return found


def slugify(url: str) -> str:
    """Derive a slug from a bikepacking.com route URL."""
    # https://bikepacking.com/routes/colorado-trail/ → colorado-trail
    url = url.rstrip('/')
    return url.split('/')[-1]


def location_from_text(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Try to extract (state/province, country) from a location string.
    Examples: 'USA, Colorado' → ('Colorado', 'USA')
              'British Columbia, Canada' → ('British Columbia', 'Canada')
    """
    # Simple heuristic — can be improved with a lookup table
    parts = [p.strip() for p in text.split(',')]
    if len(parts) >= 2:
        return parts[-1], parts[0]  # last part = country, first = state
    return text, None
