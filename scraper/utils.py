from __future__ import annotations
"""Parsing helpers for scraped text."""
import re
from typing import Optional


def parse_distance(text: str) -> tuple[Optional[float], Optional[float]]:
    """Extract (miles, km) from strings like '247 MI (398 KM)' or '247 miles'."""
    mi, km = None, None
    mi_match = re.search(r'(\d[\d,]*(?:\.\d+)?)\s*mi(?:les?)?', text, re.IGNORECASE)
    km_match = re.search(r'(\d[\d,]*(?:\.\d+)?)\s*km', text, re.IGNORECASE)
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


def parse_days_value(text: str) -> tuple[Optional[int], Optional[int]]:
    """Parse days from a bare stat block value like '4' or '5-8' (no 'days' keyword)."""
    range_match = re.search(r'(\d+)\s*[-–]\s*(\d+)', text)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    single_match = re.search(r'(\d+)', text)
    if single_match:
        d = int(single_match.group(1))
        if 1 <= d <= 365:
            return d, d
    return None, None


def parse_elevation_value(text: str) -> tuple[Optional[int], Optional[int]]:
    """Parse elevation from stat block values like \"16,390' (4,996 M)\" or '5,000 ft'."""
    ft, m = None, None
    # Feet: "16,390'" (apostrophe/prime) or "16,390 ft"
    ft_match = re.search(r"([\d,]+)['′′]", text) or re.search(r'([\d,]+)\s*ft', text, re.IGNORECASE)
    if ft_match:
        ft = int(ft_match.group(1).replace(',', ''))
    # Meters: "(4,996 M)" parenthesized secondary value
    m_match = re.search(r'\(\s*([\d,]+)\s*[Mm]\s*\)', text)
    if m_match:
        m = int(m_match.group(1).replace(',', ''))
    return ft, m


def parse_difficulty_value(text: str) -> Optional[float]:
    """Parse difficulty from a bare stat value like '6?' or '7.5' or '6/10'."""
    # "6/10" format
    match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', text)
    if match:
        return float(match.group(1))
    # Bare number, possibly followed by '?' — extract first float in range 1-10
    match = re.search(r'(\d+(?:\.\d+)?)', text)
    if match:
        val = float(match.group(1))
        if 1 <= val <= 10:
            return val
    return None


def parse_elevation(text: str) -> tuple[Optional[int], Optional[int]]:
    """Extract (ft, m) from strings like '24,000 ft (7,315 m)' or 'Ascent: 24,000 ft'."""
    ft, m = None, None
    # Look for ft near an elevation/ascent label first, then fall back to bare number
    labeled_ft = re.search(r'(?:ascent|elevation)[^\d]{0,30}([\d,]+)\s*ft', text, re.IGNORECASE)
    bare_ft = re.search(r'([\d,]+)\s*ft', text, re.IGNORECASE)
    ft_match = labeled_ft or bare_ft
    if ft_match:
        ft = int(ft_match.group(1).replace(',', ''))

    # For meters: only match inside parens like "(7,315 m)" or after labeled field
    # to avoid matching "500m trail" or "3 months"
    labeled_m = re.search(r'(?:ascent|elevation)[^\d]{0,30}([\d,]+)\s*m\b', text, re.IGNORECASE)
    paren_m = re.search(r'\(\s*([\d,]+)\s*m\s*\)', text, re.IGNORECASE)
    m_match = labeled_m or paren_m
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
    Handles: 700x40-55c, 2.2-2.4", 40-55mm, 2.35", 700x50c,
             X to Y inches, at least 45mm up to 2.2"
    Returns widths in mm (approximate conversion for inch sizes).
    """
    # Match ASCII quotes, Unicode double prime (U+2033), prime (U+2032), and curly quotes
    inch_quote = '["\'\\u2032\\u2033\\u201c\\u201d]'

    # 1. 700xNNc or 700xNN-NNc format (road/gravel)
    match = re.search(r'700\s*[xX×]\s*(\d+)(?:-(\d+))?c?', text)
    if match:
        lo = int(match.group(1))
        hi = int(match.group(2)) if match.group(2) else lo
        return lo, hi

    # 2. NNmm range with dash: 40-55mm
    match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*mm', text, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))

    # 2b. Road/gravel "N/Mc" or "Nc" tire notation (700c width, prefix omitted)
    # "45/50c" → (45, 50), "32c" → (32, 32)
    # Guard: 25–80mm to exclude wheel diameters (26", 27", 29", 700c)
    match = re.search(r'(\d+)\s*/\s*(\d+)\s*c\b', text, re.IGNORECASE)
    if match:
        lo, hi = int(match.group(1)), int(match.group(2))
        if 25 <= lo <= 80 and 25 <= hi <= 80:
            return lo, hi
    match = re.search(r'\b(\d+)\s*c\b', text, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        if 25 <= val <= 80:
            return val, val

    # 3. "X to Y inches" / "X to Y inch" prose
    match = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:to|–|-)\s*(\d+(?:\.\d+)?)\s*inch(?:es)?',
        text, re.IGNORECASE,
    )
    if match:
        lo = round(float(match.group(1)) * 25.4)
        hi = round(float(match.group(2)) * 25.4)
        return lo, hi

    # 4. Prose inch range: "at least 2.4" ... up to 3.0"" or "2.4" to 3.0""
    match = re.search(
        r'(?:at\s+least\s+)?(\d+\.\d+)\s*' + inch_quote + r'.{0,60}?(?:up\s+to|or\s+up\s+to|to)\s*(?:a\s+)?(\d+\.\d+)\s*' + inch_quote,
        text, re.IGNORECASE,
    )
    if match:
        lo = round(float(match.group(1)) * 25.4)
        hi = round(float(match.group(2)) * 25.4)
        return lo, hi

    # 4b. "N.N" or larger (M.M" is ideal)" — lower bound + ideal size in parens
    # Must come before 3b so "(M.M" ideal)" is captured as the max, not discarded
    match = re.search(
        r'(\d+\.\d+)\s*' + inch_quote + r'.{0,60}?\(\s*(\d+\.\d+)\s*' + inch_quote,
        text, re.IGNORECASE,
    )
    if match:
        lo = round(float(match.group(1)) * 25.4)
        hi = round(float(match.group(2)) * 25.4)
        return lo, hi

    # 3b. Minimum-size expression: "2.1 or larger tires", "2.4+ tires", "3" or bigger"
    match = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:inch(?:es?)?|' + inch_quote + r')?\s*(?:\+|or\s+(?:larger|bigger|more|wider))\s*(?:tires?|tyres?|inch(?:es?)?)?',
        text, re.IGNORECASE,
    )
    if match:
        val = float(match.group(1))
        if 1.0 <= val <= 5.0:
            w = round(val * 25.4)
            return w, w

    # 5. Cross-unit prose: "at least 45mm ... up to 2.2"" or "45mm to 2.2""
    match = re.search(
        r'(?:at\s+least\s+)?(\d+)\s*mm.{0,60}?(?:up\s+to|or\s+up\s+to|to)\s*(?:a\s+)?(\d+\.\d+)\s*' + inch_quote,
        text, re.IGNORECASE,
    )
    if match:
        lo = int(match.group(1))
        hi = round(float(match.group(2)) * 25.4)
        return lo, hi

    # 6. Standard inch range with dash: 2.2-2.4"
    match = re.search(r'(\d+\.\d+)\s*[-–]\s*(\d+\.\d+)\s*' + inch_quote, text)
    if match:
        lo = round(float(match.group(1)) * 25.4)
        hi = round(float(match.group(2)) * 25.4)
        return lo, hi

    # 7. Single mm value: 45mm (guard: >= 25mm to exclude stray small numbers like "3mm gap")
    match = re.search(r'(\d+)\s*mm', text, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        if val >= 25:
            return val, val

    # 8a. Integer inch range: ~2-3" or 2-3" (guard: 1–5" plausible tire range)
    match = re.search(r'~?(\d+)(?!\.\d)\s*[-–]\s*(\d+)(?!\.\d)\s*' + inch_quote, text)
    if match:
        lo_in, hi_in = int(match.group(1)), int(match.group(2))
        if 1 <= lo_in <= 5 and 1 <= hi_in <= 5:
            return round(lo_in * 25.4), round(hi_in * 25.4)

    # 8b. Single inch value (integer or decimal): ~2", 2.35", etc.
    # Guard: 1–5" to avoid false matches on wheel diameters (20", 26", 29") or years
    match = re.search(r'(?:~|approximately\s+|approx\.?\s+|about\s+)?(\d+(?:\.\d+)?)\s*' + inch_quote, text)
    if match:
        val = float(match.group(1))
        if 1.0 <= val <= 5.0:
            w = round(val * 25.4)
            return w, w

    # 9. Informal plural-s format used in MTB community: "2.4s", "ride 2.3s"
    # Matches decimal number immediately followed by 's' (no space) in 1-5" range
    match = re.search(r'(\d+\.\d+)s\b', text, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        if 1.0 <= val <= 5.0:
            w = round(val * 25.4)
            return w, w

    # 10. Compact "Nin" notation: "2.3in", "2.4in tyres" (no space between number and "in")
    match = re.search(r'(\d+(?:\.\d+)?)in\b', text, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        if 1.0 <= val <= 5.0:
            w = round(val * 25.4)
            return w, w

    return None, None


BIKE_TYPE_KEYWORDS = {
    'gravel': ['gravel bike', 'gravel bicycle', 'gravel-specific', '700c', 'gravel grinder'],
    'hardtail': ['hardtail', 'hard tail', 'xc bike', 'cross-country', '29er', 'rigid 29', '29" wheel'],
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


MONTH_NAMES: dict[str, int] = {
    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
    'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12,
}

SEASON_MONTHS: dict[str, list[int]] = {
    'spring': [3, 4, 5],
    'summer': [6, 7, 8],
    'fall': [9, 10, 11],
    'autumn': [9, 10, 11],
    'winter': [12, 1, 2],
}


def parse_best_season_months(text: str) -> list[int]:
    """
    Convert a best_season string to a sorted list of month numbers (1-12).
    Handles: 'June through September', 'Late summer to early fall',
             'July-August', 'Spring and summer', 'Year-round', etc.
    """
    if not text:
        return []
    text_lower = text.lower()

    if re.search(r'year.?round|all year|any time|anytime', text_lower):
        return list(range(1, 13))

    months: set[int] = set()

    # First extract named months
    found_months = [m for name, m in MONTH_NAMES.items() if re.search(r'\b' + name + r'\b', text_lower)]

    if found_months:
        # Only fill the range between months when they're explicitly connected with
        # "through / to / – / -" or "between X and Y" (e.g. "June through September").
        # When months are comma-listed ("March, April, October, November"), just use those months.
        month_alt = '|'.join(MONTH_NAMES.keys())
        range_signal = re.search(
            r'(?:' + month_alt + r').{0,15}(?:through|thru|\bto\b|[-–]).{0,15}(?:' + month_alt + r')'
            r'|between\s+(?:\w+\s+){0,3}(?:' + month_alt + r').{0,20}(?:and|to).{0,15}(?:' + month_alt + r')',
            text_lower,
        )
        if range_signal and len(found_months) >= 2:
            # Use only the two months inside the matched range expression — not all months
            # in the full text. This prevents "December–March. November or April are possible"
            # from incorrectly expanding to include November and April.
            range_text = range_signal.group(0)
            range_month_positions: dict[int, int] = {}
            for name, m in MONTH_NAMES.items():
                if m not in range_month_positions:
                    idx = range_text.find(name)
                    if idx >= 0:
                        range_month_positions[m] = idx
            if len(range_month_positions) >= 2:
                ordered = sorted(range_month_positions.items(), key=lambda x: x[1])
                start_num = ordered[0][0]
                end_num = ordered[-1][0]
                if start_num <= end_num:
                    for m in range(start_num, end_num + 1):
                        months.add(m)
                else:
                    # Cross-year: e.g. December (12) through March (3)
                    for m in range(start_num, 13):
                        months.add(m)
                    for m in range(1, end_num + 1):
                        months.add(m)
            else:
                # Fallback: expand between numeric min and max of all found months
                for m in range(min(found_months), max(found_months) + 1):
                    months.add(m)
        else:
            months.update(found_months)
    else:
        # Fall back to season names — only check the FIRST sentence that mentions a season.
        # Later sentences often mention bad seasons in a negative context ("Winter brings snow..."),
        # and we don't want those to corrupt the recommendation.
        ordered = ['winter', 'spring', 'summer', 'fall', 'autumn']
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sent in sentences:
            s_lower = sent.lower()
            found_seasons = [s for s in ordered if re.search(r'\b' + s + r'\b', s_lower)]
            if not found_seasons:
                continue
            if len(found_seasons) == 1:
                months.update(SEASON_MONTHS[found_seasons[0]])
            else:
                all_months = [m for s in found_seasons for m in SEASON_MONTHS[s]]
                for m in range(min(all_months), max(all_months) + 1):
                    months.add(m)
            break  # stop after first sentence that has season names

    return sorted(months)


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
