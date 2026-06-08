#!/usr/bin/env python3
"""
Process llm_input.json → llm_output.json using improved NLP extraction.
Produces llm_* columns for each route. Run after enrich_llm.py --mode fetch.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, '.')
from utils import parse_best_season_months

# ── Inch-to-mm conversion table ───────────────────────────────────────────────
def in_to_mm(inches: float) -> int:
    return round(inches * 25.4)

# ── Tire extraction ────────────────────────────────────────────────────────────
# Patterns for inch widths: 2.2", 2.25", 2.2 inch, etc.
_INCH_RE = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:"|\'\'|in(?:ch(?:es?)?)?\b)',
    re.IGNORECASE,
)
# Patterns for mm widths: 45mm, 50 mm, etc.
_MM_RE = re.compile(r'\b(\d{2,3})\s*mm\b', re.IGNORECASE)
# Range patterns: "2.2-2.6"", "2.2 to 2.6 in", "40-50mm", "40 to 50mm"
_RANGE_INCH_RE = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:"|in(?:ch(?:es?)?)?\b)?\s*(?:to|–|-)\s*(\d+(?:\.\d+)?)\s*(?:"|in(?:ch(?:es?)?)?(?:\b|(?=\s)))',
    re.IGNORECASE,
)
_RANGE_MM_RE = re.compile(
    r'(\d{2,3})\s*(?:mm)?\s*(?:to|-|–|through|and)\s*(\d{2,3})\s*mm\b',
    re.IGNORECASE,
)
# Mixed unit range: "45mm to 2.4"" or "45mm or 650b x 2.1""
_RANGE_MIXED_RE = re.compile(
    r'(\d{2,3})\s*mm\s*(?:to|-|–|or)\s*(?:\d+[a-z]*\s*[x×]\s*)?(\d+(?:\.\d+)?)\s*(?:"|\'\'|in(?:ch(?:es?)?)?)(?!\w)',
    re.IGNORECASE,
)
# "at least X", "minimum X", "greater/more than X"
_ATLEAST_INCH = re.compile(
    r'(?:at\s+least|minimum|min\.|no\s+(?:less|narrower|smaller)\s+than|bigger\s+than|wider\s+than|greater\s+than|more\s+than)\s+(\d+(?:\.\d+)?)\s*(?:"|\'\'|in(?:ch(?:es?)?)?)(?!\w)',
    re.IGNORECASE,
)
_ATLEAST_MM = re.compile(
    r'(?:at\s+least|minimum|min\.|no\s+(?:less|narrower|smaller)\s+than|bigger\s+than|wider\s+than|greater\s+than|more\s+than)\s+(\d{2,3})\s*mm\b',
    re.IGNORECASE,
)
_ORLARGER_INCH = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:"|\'\'|in(?:ch(?:es?)?)?)(?!\w)[^.]*?(?:or\s+(?:larger|bigger|wider|greater)|and\s+(?:up|larger|bigger|wider)|\+)',
    re.IGNORECASE,
)
# Bare number like "2.1 or bigger/greater tires" (no explicit unit, context makes it inches)
_ORLARGER_BARE_INCH = re.compile(
    r'\b([12]\.\d+)\s+(?:or\s+(?:larger|bigger|wider|greater|more)|and\s+(?:up|larger|bigger|wider))[^.]*?(?:tire|tyre|wheel)',
    re.IGNORECASE,
)
_ORLARGER_MM = re.compile(
    r'(\d{2,3})\s*mm\b[^.]*?(?:or\s+(?:larger|bigger|wider|greater)|and\s+(?:up|larger|bigger|wider)|\+)',
    re.IGNORECASE,
)


_QUOTE_NORMALIZE = str.maketrans({
    '“': '"', '”': '"',  # " "  LEFT/RIGHT DOUBLE QUOTATION MARK
    '″': '"', '′': "'",  # ″ ′  DOUBLE/SINGLE PRIME
    '’': "'", '‘': "'",  # ' '  CURLY APOSTROPHES
    '´': "'",                  # ´    ACUTE ACCENT
})


def _normalize(text: str) -> str:
    return text.translate(_QUOTE_NORMALIZE)


def _parse_tire_widths_from_text(text: str) -> tuple[int | None, int | None, str | None]:
    """Return (min_mm, max_mm, display_label) from a tire/bike text field.

    display_label preserves the original inch precision from the source text
    so the frontend can show "2.35"" instead of rounding to "2.4"" via mm conversion.
    """
    if not text:
        return None, None, None
    text = _normalize(text)

    # Try range patterns first (most specific)
    m = _RANGE_INCH_RE.search(text)
    if m:
        lo_str, hi_str = m.group(1), m.group(2)
        lo, hi = in_to_mm(float(lo_str)), in_to_mm(float(hi_str))
        if lo > hi:
            lo, hi = hi, lo
            lo_str, hi_str = hi_str, lo_str
        if lo == hi:
            return lo, None, f'{lo_str}"'
        return lo, hi, f'{lo_str}"–{hi_str}"'

    m = _RANGE_MM_RE.search(text)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi, f'{lo}–{hi}mm'

    m = _RANGE_MIXED_RE.search(text)
    if m:
        lo_mm = int(m.group(1))
        hi_str = m.group(2)
        hi_mm = in_to_mm(float(hi_str))
        if lo_mm > hi_mm:
            return hi_mm, lo_mm, f'{hi_str}"–{lo_mm}mm'
        return lo_mm, hi_mm, f'{lo_mm}mm–{hi_str}"'

    # "at least X" / "minimum X" / "greater than X"
    m = _ATLEAST_INCH.search(text)
    if m:
        mm = in_to_mm(float(m.group(1)))
        return mm, None, f'{m.group(1)}"+'

    m = _ATLEAST_MM.search(text)
    if m:
        mm = int(m.group(1))
        return mm, None, f'{mm}mm+'

    # "X or larger/greater"
    m = _ORLARGER_INCH.search(text)
    if m:
        mm = in_to_mm(float(m.group(1)))
        return mm, None, f'{m.group(1)}"+'

    m = _ORLARGER_BARE_INCH.search(text)
    if m:
        mm = in_to_mm(float(m.group(1)))
        return mm, None, f'{m.group(1)}"+'

    m = _ORLARGER_MM.search(text)
    if m:
        mm = int(m.group(1))
        return mm, None, f'{mm}mm+'

    # Single inch mention
    m = _INCH_RE.search(text)
    if m:
        v = float(m.group(1))
        if 1.0 <= v <= 5.0:  # plausible tire width
            mm = in_to_mm(v)
            return mm, None, f'{m.group(1)}"'

    # Single mm mention
    m = _MM_RE.search(text)
    if m:
        mm = int(m.group(1))
        if 20 <= mm <= 150:  # plausible tire width
            return mm, None, f'{mm}mm'

    return None, None, None


# ── Bike type extraction ───────────────────────────────────────────────────────
_BIKE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ('Fat Bike',        re.compile(r'\bfat[\s-]?(?:bike|tire|tyre)\b', re.I)),
    ('Full-Sus MTB',    re.compile(r'\bfull[\s-]?sus(?:pension)?\b', re.I)),
    ('Hardtail MTB',    re.compile(r'\bhard[\s-]?tail\b', re.I)),
    ('Rigid ATB',       re.compile(r'\brigid\s+(?:[\w.+]+\s+)?atb\b', re.I)),
    ('Rigid MTB',       re.compile(r'\brigid\s+(?:mountain|mtb|29er|bike|rig|fork)\b', re.I)),
    ('ATB',             re.compile(r'\batbs?\b', re.I)),
    ('Plus-Tire MTB',   re.compile(r'\bplus[\s-]?(?:tire|tyre|bike|sized)\b', re.I)),
    ('Gravel Bike',     re.compile(r'\bgravel\s*(?:bike|cyclist|setup|rig)?\b', re.I)),
    ('CX Bike',         re.compile(r'\bcyclocross\b|\bcross\s*bike\b', re.I)),
    ('Dirt Touring',    re.compile(r'\bdirt[\s-]?tour(?:ing)?\b|\btouring\s*bike\b', re.I)),
    ('MTB',             re.compile(r'\b(?:mountain\s*bike|mtb|29er)\b', re.I)),
]


def _extract_ideal_bike(bike_text: str | None) -> tuple[str | None, str | None]:
    """Return (short_label, tooltip_text)."""
    if not bike_text:
        return None, None
    bike_text = _normalize(bike_text)

    hits: list[tuple[int, str]] = []
    for label, pat in _BIKE_PATTERNS:
        m = pat.search(bike_text)
        if not m:
            continue
        # Don't add generic MTB if a more specific variant already matched
        if label == 'MTB' and any(l in ('Hardtail MTB', 'Rigid MTB', 'Full-Sus MTB', 'ATB', 'Plus-Tire MTB') for _, l in hits):
            continue
        hits.append((m.start(), label))

    if not hits:
        return None, bike_text.strip()

    hits.sort()
    labels = list(dict.fromkeys(l for _, l in hits))  # dedupe, preserve order

    # Combine up to 2 most prominent
    if len(labels) >= 3 and 'Gravel Bike' in labels and 'Hardtail MTB' in labels:
        label_str = 'Gravel or Hardtail MTB'
    elif len(labels) >= 2:
        label_str = ' or '.join(labels[:2])
    else:
        label_str = labels[0]

    return label_str, bike_text.strip()


# ── Manual season overrides for routes with ambiguous or non-obvious text ──────
# Key: slug, Value: list of month ints (1-12)
SEASON_OVERRIDES: dict[str, list[int] | None] = {
    # These were identified as having text that doesn't yield a clear season
    '828s-and-heartbreak':             None,   # text is about summer trail bypass, not season rec
    'bike-odyssey-bikepacking-route-greece': [3, 4, 5, 6, 7, 8, 9, 10, 11],  # "late March-November; spring through fall"
    'bikepacking-new-mexico-history-tour': None,  # vague
    'bikepacking-cedar-mesa':          None,   # only mentions avoiding summer
    'cotopaxi-360':                    [6, 7, 8, 9],  # "June to mid-Sept high season, driest"
    'cowichan-valley-8':               None,   # mentions summer months being busy
    'aspen-ridge-overnighter':         None,   # no season info
    # Routes where the southern hemisphere seasons need manual handling
    'attack-of-the-buns':             [3, 4, 5, 9, 10, 11],   # AU: Sept-Nov + Mar-May
    'fin-del-mundo-overnighter':      [10, 11, 12, 1, 2, 3, 4],  # late Oct - early May (SH spring-autumn)
    'mabr-s4':                        None,   # rideable any time (year-round)
    'the-morgan-loop':                [5, 6, 7],  # AU: May-July = winter (dry, cooler)
    'hunt-1000':                      [10, 11, 12, 1, 2, 3],  # Oct-Mar = AU summer
    'red-centre':                     [5, 6, 7, 8],  # May-Aug = AU dry season
    'hawkesbury-ognr':                [4, 5, 6, 7, 8, 9, 10, 11],  # AU April-November
    'ruta-de-las-vicunas-northern-chile': [5, 6, 7, 8],  # winter (dry)
    'sand-s3':                        [6, 7, 8],  # SA winter best
    'lesotho-traverse':               [10, 11, 12],  # spring (Oct-Dec)
    'munda-biddi-trail':              [3, 4, 5, 8, 9],  # AU spring (Aug-Sep) and autumn (Apr-May)
    'the-morgan-loop':                [5, 6, 7],  # AU winter
    'billy-bunyip-overnighter':       [3, 4, 5, 9, 10, 11],  # AU spring + autumn
    'st-bathans-traverse':            [12, 1, 2, 3, 4, 5],  # NZ: covered in snow Jun-Nov
    # Cross-year ranges parsed correctly by regex but worth confirming
    'madrean-rugged-ramble':          [10, 11, 12, 1, 2, 3, 4],
    'el-camino-del-diablo':           [11, 12, 1, 2, 3, 4],
    'camels-dunes-wadis-uae':         [12, 1, 2, 3],
    'anza-borrego-overnighter':       [10, 11, 12, 1, 2, 3, 4],
    'river-road-ramble-big-bend':     [11, 12, 1, 2, 3],
    'edt8':                           [12, 1, 2, 3],
    'queens-ransom':                  [10, 11, 12, 1, 2, 3],
    'sky-islands-odyssey-east-loop':  [10, 11, 12, 1, 2, 3, 4],
    'sky-islands-odyssey-west-loop':  [10, 11, 12, 1, 2, 3, 4],
    'tcbr-sur':                       [11, 12, 1, 2],
    'ruta-seis-miles-sur':            [10, 11, 12, 1, 2, 3, 4],
    'caminos-del-sol':                [9, 10, 11, 12, 1, 2, 3, 4, 5],
    'fools-loop-arizona':             [11, 12, 1, 2, 3, 4],
    'sand-s2':                        [4, 5, 6, 7, 8, 9, 10],  # AU autumn-spring
    'sand-s1':                        [5, 6, 7, 8, 9],  # SA winter/dry
    'sand-s4':                        [4, 5, 6, 7, 8, 9, 10],
    'sand-s5':                        [4, 5, 6, 7, 8],
    'ojai-rim-loop':                  [11, 12, 1, 2, 3, 4, 5],
    'golden-jackrabbit-loop':         [10, 11, 12, 1, 2, 3, 4],
    'socal-desert-ramble':            [10, 11, 12, 1, 2, 3, 4],
    'jordan-bike-trail':              [3, 4, 10, 11, 12],
    'trans-cuba':                     [12, 1, 2, 3, 4, 5],
    'ruta-maya-de-los-cuchumatanes':  [11, 12, 1, 2, 3, 4],
    'ruta-toro-toro-bolivia':         [6, 7, 8, 9, 10],  # Bolivian winter
    'cones-canyons-peru-divide':      [4, 5, 6, 7, 8, 9],
    'peru-great-divide':              [4, 5, 6, 7, 8, 9],
    'mama-coca':                      [6, 7, 8, 9],  # high Andean: dry season Jun-Sep (text confirms "outside dry season = snow-covered")
    'carolina-sandhills-overnighter': [10, 11, 12, 1, 2, 3, 4, 5],
    'cappadocia-delight':             [4, 5, 9, 10],
    'caucasus-crossing-armenia':      [6, 7, 9, 10],
    'bikepacking-big-bend-side-nowhere': [2, 3, 4, 9, 10, 11, 12],
    'cuatro-venados-eco-overnighter-oaxaca': [10, 11, 12, 1],
    'meandros-de-montebello-chiapas': None,  # rainy/dry tradeoffs, no clear best
    'meandros-en-mitla-mexico':       [10, 11, 12, 1],
    'micro-vuelta-sierra-norte':      [10, 11, 12, 1],
    'oaxaca-ixtepeji':                [10, 11, 12],
    'oaxaca-puerto-escondido':        [10, 11, 12, 1],
    'san-jose-del-pacifico':          [10, 11, 12, 1],
    'vuelta-a-los-pueblos-mancomunados': [10, 11, 12, 1],
    'excursiones-en-etla':            [10, 11, 12],
    'caminos-del-sol':                [9, 10, 11, 12, 1, 2, 3, 4, 5],
    'gran-via-del-sol':               [9, 10, 11, 12, 1, 2, 3, 4, 5],
    'trans-salvador':                 [11, 12, 1, 2, 3, 4],
    'trans-cuba':                     [12, 1, 2, 3, 4, 5],
    'travesia-por-atitlan-guatemala': [10, 11, 12, 1, 2, 3, 4],
    'ruta-el-dorado':                 [1, 2, 3, 7, 8],  # Colombia: dry seasons Jan-Mar + Jul-Aug per text
    'paramos-conexion':               None,  # Colombia equatorial, complex
    'oh-boyaca-colombia':             [12, 1, 2, 3, 7, 8],  # driest Dec-Mar + Jul-Aug dry season
    'el-camino-de-la-puma':           [4, 5, 6, 7, 8, 9, 10, 11, 12],  # Apr-Dec dry season
    'trans-mexico-norte':             [12, 1, 2, 3, 4],
    'trans-mexico-sur':               [11, 12, 1, 2, 3],
    'ruta-seis-miles-norte':          [11, 12, 1, 2, 3],  # Nov-Mar (open season)
    'patagonia-beer-trail-argentina': None,  # no season info
    'tres-cordilleras-boliva-peru':   None,  # no season info
    'ruta-del-capitan-lemos':         None,  # no season info
    'european-divide-trail':          [5, 6, 7, 8, 9, 10],
    'mabr-n1':                        [5, 6, 7, 8, 9],
    'mabr-n2':                        [5, 6, 7, 8, 9, 10],
    'mabr-n3':                        [5, 6, 7, 8, 9],
    'mabr-s1':                        [5, 6, 7, 8, 9],
    'mabr-s2':                        [5, 6, 7, 8, 9],
    'mabr-s3':                        [5, 6, 7, 8, 9],
    'konig':                          None,
    'at-bashi-circuit':               [6, 7, 8, 9],
    'expedition-alay':                [7, 8],
    'tian-shan-traverse-kyrgyzstan':  [7, 8, 9],
    'the-celestial-divide':           [7, 8, 9],  # "July to mid-September"
    'bartang-valley-tajikistan':      [6, 7, 8, 9],
    'border-roads-tibet':             [5, 6, 7, 8, 9, 10],
    'jura-traverse':                  [6, 7, 8, 9],
    'la-observer':                    None,
    'the-lanna-kingdom':              [11, 12, 1, 2],  # Thailand winter (Nov-Feb)
    'tiger-head-mountain-loop':       [11, 12, 1, 2],  # Thailand winter
    'dragon-blood-socotra-yemen':     None,  # no season info
    'cycling-nyika-national-park-malawi': [5, 6, 7, 8, 9, 10, 11],
    'trans-uganda':                   [12, 1, 2, 6, 7, 8, 9],  # dry seasons
    'congo-nile-trail':               [6, 7, 8, 9],  # mid-May to mid-Sep main dry
    'lesotho-traverse':               [10, 11, 12],  # spring
    'cycling-the-gr5-belgian-ardennes': None,
    'berkshire-hills-ramble':         None,
    'havel-wetland-wander':           None,
    'emmental-switzerland':           [6, 7, 8, 9],
    'rheintal':                       [5, 6, 7, 8, 9, 10],
    'hin-und-hunsruck':               [5, 6, 7, 8, 9, 10],
    'sweet-and-sauerland':            [5, 6, 7, 8, 9],
    'taunus-storm-chase':             [5, 6, 7, 8, 9, 10],
    'harz-is-hard':                   [6, 7, 8, 9],
    'rhoenrad-circle':                [4, 5, 6, 7, 8, 9, 10],
    'rennsteig-express':              [4, 5, 6, 7, 8, 9, 10],
    'verona-lessinia-loop':           None,
    'trans-dolomiti':                 [6, 7, 8, 9, 10],
    'tour-du-mont-blanc':             [6, 7, 8, 9],
    'livigno-loop':                   [5, 6, 7, 8, 9, 10],
    'alta-via-dei-monti-liguri':      [6, 7, 8, 9, 10],
    'bikepacking-sibillini-italy':    [5, 6, 7, 8, 9, 10],
    'marmots-land':                   [7, 8, 9, 10],
    'braies-beyond':                  [9, 10],  # "best conditions" in Sept/Oct
    'zillertal-trail':                [6, 7, 8, 9],  # "June to September ideal"
    'trans-karavanks-slovenia':       [5, 6, 7, 8, 9, 10],
    'bikepacking-slovenia':           [5, 6, 7, 8, 9],
    'ardeche-cevennes-divide':        [4, 5, 6, 7, 8, 9, 10, 11],
    'grande-traversee-provence':      [3, 4, 5, 9, 10],
    'transardinia':                   [9, 10, 11],  # "late Sept to early Nov" best
    'tour-du-vaucluse':               [5, 6, 9, 10],
    'trans-verdon-france':            [3, 4, 5, 9, 10],
    'gran-sasso-loop':                None,
    'grangarda':                      [4, 5, 6, 7, 8, 9, 10],
    'iberica-norte':                  [3, 4, 5, 9, 10],
    'montanas-vacias':                [3, 4, 5, 9, 10],
    'of-resilience-and-hope':         [3, 4, 10, 11],
    'road-bike-touring-gr-48-spain':  [3, 4, 5, 9, 10],
    'gr247-spain':                    [3, 4, 5, 9, 10],
    'altravesur-bikepacking-route':   [3, 4, 5, 9, 10, 11],        # "Spring/fall ideal; May and October best" (Andalusia)
    'bikepacking-croatia':            None,
    'bosnian-highline':               [5, 6, 9],
    'apennine-mountain-traverse':     [4, 5, 6, 7, 8, 9, 10],
    'bikepacking-abruzzo':            None,
    'campari-long-ride':              None,
    'bruschetta-loop-italy':          [5, 6, 7, 8, 9, 10, 11],
    'lunigiana-trail':                None,
    'cima-dasta-loop':                [6, 7, 8, 9, 10],
    'asiago-loop':                    [5, 6, 7, 8, 9, 10],
    'gorgany-trail-ukraine':          [6, 7, 8, 9, 10],
    'polonina-borzhava-ukraine':      None,
    'holyland-challenge-israel':      [3, 4, 5, 10, 11],  # Israel: spring + fall; scraped text was about camping, not season
    'bikepacking-cyprus-crossing':    [4, 5, 6, 7, 8, 9, 10],
    'kyrenia-traverse':               [4, 5, 6, 9, 10, 11],
    'cappadocia-delight':             [4, 5, 9, 10],
    'hydra-bikepacking-route':        [5, 6, 7, 8, 9, 10],
    'the-annapurna-circuit':          [4, 5, 10, 11],
    'totsnz':                         [5, 6, 7, 8, 9, 10, 11],  # May 1 - Nov 30
    'tots-nz':                        [5, 6, 7, 8, 9, 10, 11],
    'tasmanian-trail':                None,
    'the-tassie-traverse':            [11, 12, 1, 2, 3, 4],  # Nov to mid-April
    'south-island-sundowner':         None,
    'st-bathans-traverse':            [12, 1, 2, 3, 4, 5],  # June-Nov = snow
    'bikepacking-reunion-island':     None,
    'great-western-loop':             [4, 5, 6, 7, 8, 9, 10],
    'dalarna-ramble-overnighter':     [8, 9, 10],
    'gysinge-rtl':                    None,
    'huddingeleden':                  [6, 7, 8],
    'vastmanland-overnighter':        [9, 10],  # best time Sept-Oct
    'wilder-stockholm':               [5, 6, 7, 8, 9, 10],
    'sormland-project':               [5, 6, 7, 8, 9, 10],
    'bergslagsleden':                 None,
    'swamp-thing-trail-estonia':      [6, 7, 8],
    'heuvelland-explorer':            [4, 5, 6, 7, 8, 9, 10],
    'of-milk-and-navvies':            [6, 7, 8, 9],  # Mjolkevegen opens late June
    'dalarna-ramble-overnighter':     [8, 9, 10],
    'bear-bones-bash-mid-wales':      [3, 4, 5, 6, 7, 8, 9, 10, 11],
    'bear-bones-border-bash':         [5, 6, 7, 8],
    'black-mountain-crossing':        [5, 6, 7, 8, 9],
    'exmoor-explorer-overnighter':    [4, 5, 6, 7, 8],
    'gower-gold-overnighter':         [4, 5, 6, 7, 8, 9],
    'purbeck-bimble-dorset-uk':       [5, 6, 7, 8, 9],
    'hereford-express':               [6, 7, 8, 9],
    'downs-overnighter':              [4, 5, 6, 7, 8, 9],
    'henley-100':                     [4, 5, 6, 7, 8, 9, 10],
    'wolf-way':                       None,  # year-round
    'old-chalk-way':                  [4, 5, 6, 7, 8, 9, 10],
    'peak-potter':                    None,
    'dark-white-peak-peek':           None,
    'straight-outta-manchester':      None,
    'brecons-bash':                   [5, 6, 7, 8, 9],
    'gb-divide':                      [5, 6, 7, 9],                # May, June, July, September
    'new-forest-gravel-taster-uk':    [5, 6, 7, 8, 9],
    'deeside-trail':                  None,
    'cairngorms-loop':                [5, 6, 7],
    'ten-peaks-trail':                [4, 5, 6, 7, 8, 9],
    'witch-of-the-westfjords':        [7, 8],  # late July best
    'european-divide-trail':          [5, 6, 7, 8, 9, 10],
    'westfjords-way':                 [6, 7, 8, 9],
    'swiss-jura-explorer':            [3, 4, 5, 6, 7, 8, 9, 10],
    'emmental-switzerland':           [6, 7, 8, 9],
    'jura-traverse':                  [6, 7, 8, 9],
    'havel-wetland-wander':           None,
    'rambouillet-forest-overnighter': [6, 7, 8],
    'ardennes-arbalete':              [4, 5, 6, 7, 8, 9, 10],  # Belgian Ardennes: spring through fall; best_season field was null
    'ardeche-cevennes-divide':        [4, 5, 6, 7, 8, 9, 10, 11],
    'bikepacking-the-white-rim':      None,
    # Grassy season picker gets wrong months from negative mentions
    'bc-grasslands-circuit':          [3, 4, 5, 9, 10, 11],   # "best in spring... Fall also pleasant"
    'bonnington-scrambler':           [7, 8, 9],  # Rail trail closed May1-late June; summer best
    'bc350':                          [5, 6],      # "May 15 to June 15 range"
    'central-wasatch-traverse':       [6, 7, 8, 9, 10],
    'cross-washington-xwa':           [5, 6, 7, 8, 9, 10],
    'dollarhide-summit-overnighter':  [6, 7, 8, 9, 10],  # late spring through fall
    'sun-valley-high-country-loop':   [6, 7, 8, 9, 10],
    'sage-and-saddles':               [6, 7, 8, 9, 10],
    'slotoja':                        [6, 7, 8, 9, 10],
    'bikepacking-big-bend-side-nowhere': [2, 3, 4, 9, 10, 11, 12],
    'mojave-solitaire':               [10, 11, 12, 1, 2, 3, 4],  # "scouted in mid-November"
    'owens-valley-ramble':            [3, 4, 5, 10, 11],
    'san-diego-high-country-overnighter': [3, 4, 5, 9, 10, 11],
    'san-juan-space-jam-new-mexico':  [3, 4, 5, 9, 10, 11],
    'valles-caldera-explorer':        [4, 5, 6, 7, 8, 9, 10],
    'redington-lemmon-loop':          [11, 12, 1, 2, 3, 4],  # fall/spring/winter
    'ring-around-the-ritas':          [2, 3, 4, 9, 10],
    'robbers-roost-overnighter':      [3, 4, 5, 9, 10, 11],
    'cathedral-valley-loop':          [3, 4, 5, 9, 10, 11],
    'grand-staircase-loop':           [3, 4, 5, 9, 10, 11],
    'moab-based routes':              [3, 4, 5, 9, 10, 11],
    'peaks-and-plateaus':             [3, 4, 5, 9, 10],  # Moab area
    'cabezon-peak-overnighter':       [10, 11, 12, 1, 2, 3, 4],
    'black-canyon-trail':             [10, 11, 12, 1, 2, 3],
    'socal-desert-ramble':            [10, 11, 12, 1, 2, 3, 4],
    'stagecoach-400-bikepacking-route': [3, 4, 10, 11],
    'el-camino-del-diablo':           [11, 12, 1, 2, 3, 4],
    'death-valley-dustup':            [11, 12, 1, 2, 3],  # November-March; avoid extreme summer heat
    'mojave-solitaire':               [10, 11, 12, 1, 2, 3, 4],
    'joshua-tree-dirt-roads':         [3, 4, 5, 9, 10, 11],
    'bike-touring-joshua-tree-dirt-roads': [3, 4, 5, 9, 10, 11],
    'golden-jackrabbit-loop':         [10, 11, 12, 1, 2, 3, 4],
    'hartman-rocks-overnighter':      [3, 4, 5, 9, 10, 11],
    'north-routt-ramble':             [6, 7, 8, 9],
    'prairie-breaks':                 [6, 7, 8, 9],
    'flint-hills-oz-overnighter':     [3, 4, 5, 6, 7, 8, 9, 10],
    'no-business-loop':               None,  # unclear from text
    'cohutta-cat':                    [3, 4, 10, 11],
    'sheltowee-bikepacking-route':    [3, 4, 5, 9, 10, 11],
    'highlands-traverse-overnighter': [4, 5, 6, 7, 8, 9, 10, 11],
    'rothrock-rambler-overnighter':   [4, 5, 9, 10, 11],
    'old-stone-house-loop':           [6, 7, 8, 9, 10],
    'north-country-traverse':         [4, 5, 6, 7, 8, 9, 10, 11],
    'no-place-like-oz':               [3, 4, 5, 9, 10, 11],
    'heart-of-the-greens-loop':       None,
    'transnc':                        [4, 5, 6, 7, 8, 9, 10],
    'trans-wnc':                      [4, 5, 6, 7, 8, 9, 10],
    'wardsboro-loop-overnighter':     [5, 6, 7, 8, 9],
    'roundabout-brattleboro':         None,
    'finger-lakes-overnighter':       [3, 4, 5, 9, 10, 11],
    'montshire-maze':                 [6, 7, 8, 9, 10],  # "Mid-June to October"
    'qualla-quest':                   [5, 6, 7, 8, 9, 10],
    'norcal-outback':                 [4, 5, 6],
    'caldera-500':                    None,
    'cascade-skyline':                [7, 8, 9],
    'oregon-timber-trail':            [7, 8, 9, 10],
    'oregon-cascades-volcanic-arc-ocva': [6, 7, 8, 9, 10],  # "Late June to October"
    'oregon-outback':                 [4, 5, 6, 9, 10],
    'oregon-big-country':             None,
    'high-cascades-overnighter':      [7, 8, 9],
    'silver-siouxon':                 None,
    'gunsight-ridge-bikepacking-mount-hood-finest': [7, 8, 9],
    'frog-lake-loop':                 [4, 5, 6, 7, 8, 9],
    'olympic-bridges-overnighter':    [6, 7, 8, 9, 10, 11],        # "Summer and fall best; spring/winter wet"
    'fire-ice-cave-loop':             [5, 6, 7, 8, 9, 10],
    'anaxshat-passage':               [6, 7, 8, 9, 10],
    'central-oregon-backcountry-explorer': [4, 5, 6, 7, 8, 9, 10],
    'gawr-s1':                        [6, 7, 8, 9, 10],
    'gawr-s2':                        [6, 7, 8, 9, 10],
    'gawr-s3':                        [6, 7, 8],
    'gawr-s4':                        [4, 5, 6, 7, 8, 9, 10],
    'gawr-s5':                        [4, 5, 6, 7, 8, 9, 10],
    'gawr-s6':                        [4, 5, 6, 7, 8, 9, 10],
    'great-divide-mountain-bike-route-gdmbr': [6, 7, 8, 9, 10],
    'edt1':                           [7, 8, 9],  # mid-August to mid-September best
    'edt2':                           [8, 9, 10],
    'edt3':                           [8, 9, 10],
    'edt4':                           [4, 5, 6, 7, 8, 9, 10],
    'edt5':                           [4, 5, 9, 10, 11],
    'edt6':                           [4, 5, 10, 11],
    'edt7':                           [3, 4, 5, 10, 11, 12],
    'edt8':                           [12, 1, 2, 3],
    'nehc1000':                       [6, 7, 8, 9],
    'northern-white-mountains-loop':  [5, 6, 7, 8, 9, 10, 11],
    'heart-of-the-greens-loop':       None,
    'green-mountain-gravel-growler':  [8, 9, 10],
    'upper-valley-trail-mix':         [5, 6, 7, 8, 9, 10],
    'tahoe-twirl':                    [6, 7, 8, 9, 10],
    'vapor-trail':                    [7, 8, 9, 10],
    'the-alpine-loop':                [6, 7, 8, 9],
    'san-jose-del-pacifico':          [10, 11, 12, 1],
    'bikepacking-pisgah-appalachian-beer-trail': [5, 6, 7, 8, 9],
    'shasta-siskiyou-loop':           [6, 7, 8, 9, 10],
    'summit-to-sea':                  None,
    'redwood-backcountry-rambler':    None,
    'hope-1000':                      [5, 6, 7, 8, 9],
    'mammoth-gravel-loop':            [5, 6, 7, 8, 9, 10],
    'manistee-overnighter':           None,
    'nbwgl':                          [7, 8, 9],
    'southern-blues-600':             [7, 8, 9],
    'salmon-river-solitude':          [7, 8, 9],
    'warm-lake-wanderer':             [5, 6, 7, 8, 9],
    'hereford-express':               [6, 7, 8, 9],
    'ridges-rivers-and-rails-overnighter': [6, 7, 8, 9, 10],
    'minneiowisco':                   [9, 10],
    'minnesota-river-ramble':         [9, 10],
    'wisconsin-waterfalls-loop':      [10],
    'trans-wisconsin-bicycle-route':  [9, 10],
    'tour-de-chequamegon-wisconsin':  [10],
    'flint-hills-oz-overnighter':     [3, 4, 5, 9, 10],
    'yellow-river-loop':              [3, 4, 5, 6, 7, 8, 9, 10, 11],  # "suggest going between March and November"
    'brown-county-delight':           None,
    'no-place-like-oz':               [3, 4, 5, 9, 10, 11],
    'trail-des-voyageurs':            None,
    'straddle-and-paddle':            [8, 9],
    'valhalla-beach-party':           [6, 7, 8, 9, 10],
    'north-country-traverse':         [4, 5, 6, 7, 8, 9, 10, 11],
    'ridout-bigwind-rugged-ramble':   [4, 5, 6, 7, 8, 9, 10, 11],
    'foret-ouareau-loop':             [5, 6, 7, 8, 9, 10],
    'griffith-highland-overnighter':  None,
    'le-p-tit-train-du-nord':         None,
    'english-river-overnighter':      [5, 6, 7, 8, 9],
    'englishman-river-overnighter':   [5, 6, 7, 8, 9],
    'powell-river-sampler':           [5, 6, 7, 8, 9, 10],
    'santa-rosa-valleys-and-vistas':  [6, 7, 9, 10],
    'frog-peak-loop':                 [5, 6, 7, 8, 9],
    'bc-trail':                       [6, 7, 8, 9],
    'around-the-babines':             [7, 8, 9, 10],
    'bikepacking-lower-sunshine-coast': [4, 5, 6, 7, 8, 9, 10, 11],
    'bikepacking-the-chilcotin-mountains': [6, 7, 8, 9, 10],  # "mid-June to late-October"
    'bikepacking-sea-to-sky-trail':   [6, 7, 8, 9, 10],
    'cloudburst-mountain-divide':     [6, 7, 8, 9, 10],
    'chute-lake-charcuterie':         [9, 10],
    'alberni-bam-bam':                [5, 6, 7, 8, 9],
    'tree-to-sea-loop-vancouver-island': [5, 6, 7, 8],
    'marmots-land':                   [7, 8, 9, 10],
    'dalarna-ramble-overnighter':     [8, 9, 10],
    'kenai-250':                      [6, 7, 8, 9],
    'expedition-alay':                [7, 8],
    'at-bashi-circuit':               [6, 7, 8, 9],
    'bartang-valley-tajikistan':      [6, 7, 8, 9],
    'raki-roads':                     None,
    'bikepacking-tso-kar-to-tso-moriri-indian-himalaya': None,
    'annapurna-circuit':              [4, 5, 10, 11],
    'the-annapurna-circuit':          [4, 5, 10, 11],
    'bikepacking-coconino-loop':      [3, 4, 5, 9, 10, 11],
    'bikepacking-the-colorado-trail': [7, 8, 9],
    'four-by-four':                   [6, 7, 8],
    'sun-valley-high-country-loop':   [6, 7, 8, 9, 10],
    'slotoja':                        [6, 7, 8, 9, 10],
    'basin-and-batholith':            [5, 6, 7, 8, 9],
    'eagle-hardscrabble-overnighter': [7, 8, 9, 10],
    'the-wydaho-one-hundred':         [6, 7, 8, 9, 10],
    'hart-sheldon-hot-springs':       [4, 5, 6],  # late spring only
    'salmon-river-solitude':          [7, 8, 9],
    'north-routt-ramble':             [6, 7, 8, 9],
    'red-feather-ramble':             [6, 7, 8, 9, 10],
    'four-by-four':                   [6, 7, 8],
    'waunita-overnighter':            None,
    'gunni-grinder':                  None,  # race info
    'hartman-rocks-overnighter':      [3, 4, 5, 9, 10, 11],
    'pitkin-passage':                 [6, 7, 8, 9, 10],
    'bear-lake-shakedown':            [6, 7, 8, 9, 10],
    'around-arrowrock':               [4, 5, 6, 7, 8, 9, 10, 11],
    'scout-mountain-route':           [6, 7, 8, 9, 10],
    'sun-valley-high-country-loop':   [6, 7, 8, 9, 10],
    'snow-odyssey':                   None,
    'west-fork-overnighter':          [6, 7, 8, 9],
    'high-life':                      None,
    'snowden-or-dust-route':          [6, 7, 8],
    'bull-valley-mountains-loop':     [3, 4, 5, 9, 10, 11],
    'ojai-rim-loop':                  [11, 12, 1, 2, 3, 4, 5],
    'ephraims-grave-scenic-route':    [4, 5, 6, 9, 10],
    'around-arrowrock':               [4, 5, 6, 7, 8, 9, 10, 11],
    'teanaway-river-link-up':         [6, 7, 8, 9],
    'three-sisters-three-rivers':     [6, 7, 8, 9],
    'thunder-in-paradise':            [7, 8, 9],
    'mount-st-helens-epic':           [7, 8, 9],
    'fish-forks-overnighter':         [7, 8, 9, 10],
    'high-cascades-overnighter':      [7, 8, 9],
    'salmon-river-solitude':          [7, 8, 9],
    'hopscotch':                      None,
    'woodlands-route':                None,
    'hope-1000':                      [5, 6, 7, 8, 9],
    'old-stone-house-loop':           [6, 7, 8, 9, 10],
    'bear-lake-shakedown':            [6, 7, 8, 9, 10],
    'ridges-rivers-and-rails-overnighter': [6, 7, 8, 9, 10],
    'great-san-diego-triathlon':      [10, 11, 12, 1, 2, 3, 4],  # San Diego: fall through spring; scraped text was storm warning
    'drakes-passage':                 None,
    'drake-passage':                  [8, 9, 10, 11],
    'fools-loop-arizona':             [10, 11, 12, 1, 2, 3, 4],
    'ring-around-the-ritas':          [2, 3, 4, 9, 10],
    'las-vegas-backcountry':          None,
    'wilsons-ramble':                 None,
    'the-wildcat':                    [4, 5, 6, 7, 8, 9, 10],
    'woods-rat-run':                  [5, 6, 7, 8, 9, 10],
    'vaetmanland-overnighter':        [9, 10],
    'brandenburgodyssee':             None,
    'heuvelland-explorer':            [4, 5, 6, 7, 8, 9, 10],
    'new-forest-gravel-taster-uk':    [5, 6, 7, 8, 9],
    'great-western-loop':             [4, 5, 6, 7, 8, 9, 10],
    'morgan-loop':                    [5, 6, 7],
    'the-rolling-horse':              [7, 8, 9, 10],
    'rollingrolling-horse':           [7, 8, 9, 10],
    'the-royal-ramble':               None,
    'billy-bunyip-overnighter':       [3, 4, 5, 9, 10, 11],
    'otway-rip':                      None,
    'hawkesbury-ognr':                [4, 5, 6, 7, 8, 9, 10, 11],
    'munda-biddi-trail':              [3, 4, 5, 8, 9],
    'palmetto-trail':                 None,
    'trans-north-georgia-tnga':       [4, 5, 9, 10],  # Spring (April/May) + Fall (September/October)
    'maah-daah-hey':                  [4, 5, 6, 9, 10, 11],  # April-June + September-November; avoid summer heat
    'blue-ridge-wrangler':            [3, 4, 5, 6, 7, 8, 9, 10, 11],
    'overnighter-harrisonburg-va':    [3, 4, 5, 9, 10, 11],
    'canaan-valley-forks-of-cheat':   [5, 6, 7, 8, 9],
    'chesapeake-ohio-canal':          None,
    'rothrock-rambler-overnighter':   [4, 5, 9, 10, 11],
    'highlands-traverse-overnighter': [4, 5, 6, 7, 8, 9, 10, 11],
    'the-steel-triangle':             [3, 4, 5, 6, 7, 8],
    'no-business-loop':               None,
    'northern-white-mountains-loop':  [5, 6, 7, 8, 9, 10, 11],
    'nehc1000':                       [6, 7, 8, 9],
    'finger-lakes-overnighter':       [3, 4, 5, 9, 10, 11],
    'foret-ouareau-loop':             [5, 6, 7, 8, 9, 10],
    'ridout-bigwind-rugged-ramble':   [4, 5, 6, 7, 8, 9, 10, 11],
    'griffith-highland-overnighter':  None,
    'downs-overnighter':              [4, 5, 6, 7, 8, 9],
    'wolf-way':                       None,
    'brandenburgodsee':               None,
    'rammstein':                      None,
    # Routes added from user QA
    'grand-island-overnighter':       [9, 10],  # "favorite time is Sept and Oct; ferry runs Memorial Day to early Oct"
    'lakeland-200-uk':                [3, 4, 5, 6, 7, 8, 9, 10, 11],  # "spring to autumn"
    'little-switzerland-loop':        [5, 6, 7, 8, 9, 10],  # "May to October ideal; year-round but campgrounds May-Oct only"
    # ── Fix routes where parse_best_season_months produces all-12 months ─────────
    # Parser can't split on "since/except" constructions in these texts
    'ironwood-overnighter':           [1, 2, 3, 4, 10, 11, 12],   # "Winter/late fall/early spring best; summer extremely hot"
    'jeune-landing-loop':             [3, 4, 5, 6, 7, 8, 9, 10, 11],  # "almost all year except heavy snow winter days"
    'bikepacking-north-country-trail': [5, 6, 7, 8, 9, 10],      # managed season 5/15–10/31; fall ideal
    'la-huella-del-oso':              [5, 6, 7, 8, 9, 10],        # "late spring, summer, early fall" (Asturias)
    'kenya-bike-odyssey':             [1, 2, 6, 7, 8, 9, 12],    # avoid long rains Mar–May and short rains Oct–Nov
    'lincoln-gravel-imp':             None,                        # genuinely year-round paved/gravel
    'turin-hills-loop':               None,                        # genuinely year-round; no snow in winter
    # ── Geography-based overrides for routes with null best_season text ──────────
    # US — Desert Southwest (avoid hot summer)
    'swell-night-out':                [3, 4, 5, 9, 10, 11],       # San Rafael Swell, Utah
    'caja-del-rio':                   [3, 4, 5, 10, 11],          # New Mexico
    'fatpacking-moab-kane-creak-and-pritchett-canyon': [3, 4, 5, 9, 10, 11],  # Moab
    'kokopelli-trail-bikepacking-route': [3, 4, 5, 9, 10, 11],   # Moab area
    'bikepacking-the-arizona-trail-azt': [3, 4, 5, 10, 11],      # Arizona Trail
    'arizona-bikepacking-gila-river-ramble': [10, 11, 12, 1, 2, 3, 4],  # AZ lower desert
    'tombstone-hustle-bikepacking-cochise-and-the-dragoons': [3, 4, 10, 11, 12],  # SE Arizona
    'wolf-hole-mountain-overnighter': [3, 4, 10, 11],             # AZ Kaibab plateau
    'monumental-loop':                [3, 4, 5, 9, 10, 11],       # Utah canyon country
    'lost-canyon-overnighter':        [3, 4, 5, 9, 10, 11],       # SW US canyon country
    'cattle-calls-and-canyon-walls':  [3, 4, 5, 9, 10, 11],       # canyon country
    'echo-titus-circuit':             [11, 12, 1, 2, 3],        # likely CO mountains
    'secret-mesa-loop':               [5, 6, 7, 8, 9, 10],        # likely CO high country
    # US — Southeast/Gulf (avoid humid summer peaks, frost winters)
    'huracan-300-bikepacking-route':  [10, 11, 12, 1, 2, 3, 4],  # Florida
    'texas-bbq-tour':                 [3, 4, 5, 10, 11, 12],      # Texas
    'texas-hill-country-overnighter': [3, 4, 5, 10, 11, 12],      # Texas Hill Country
    'alabama-skyway':                 [3, 4, 5, 10, 11],          # Alabama
    'chauga-river-ramble':            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],  # "Ride all seasons" – SC/GA
    'mega-mid-south':                 [3, 4, 5, 9, 10, 11],       # Mid-South US
    'ouachita-triple-crown':          [3, 4, 5, 9, 10, 11],       # Arkansas/Oklahoma
    'ouachita-vistas-overnighter':    [3, 4, 5, 9, 10, 11],
    # US — Appalachians / Mid-Atlantic / Northeast
    'amherst-overnighter':            [5, 6, 7, 8, 9, 10],        # New England
    'appalachian-gravel-growler':     [4, 5, 6, 7, 8, 9, 10, 11],
    'arkansas-high-country-route-northwest-loop': [4, 5, 6, 9, 10, 11],
    'delaware-county-catskills-dirt-circuit': [5, 6, 7, 8, 9, 10],  # Catskills NY
    'delaware-water-gap-loop':        [4, 5, 6, 7, 8, 9, 10, 11],
    'false-cape-border-dash':         [4, 5, 6, 9, 10, 11],       # VA coast
    'looking-glass-loop':             [4, 5, 6, 7, 8, 9, 10],     # Pisgah NC
    'moco-bikepacking-montgomery-county': [4, 5, 6, 9, 10, 11],   # Maryland
    'pennsylvania-grand-canyon-loop': [5, 6, 7, 8, 9, 10],
    'sky-meadows-overnighter':        [4, 5, 6, 7, 8, 9, 10],     # Virginia
    'the-real-pisgah':                [4, 5, 6, 7, 8, 9, 10],     # Pisgah NC
    'buckeye-trail-bicycle-route':    [4, 5, 6, 7, 8, 9, 10],     # Ohio
    'virginia-mountain-bike-trail':   [4, 5, 6, 7, 8, 9, 10],
    'vtxl':                           [6, 7, 8, 9, 10],           # Vermont Long Trail ridges
    'wayne-forest-trail-tour':        [4, 5, 6, 7, 8, 9, 10],     # Wayne NF Ohio
    'yancey-ridge-s24o':              [4, 5, 6, 7, 8, 9, 10],     # NC
    'croatan-gravel-vanish':          [4, 5, 6, 7, 8, 9, 10],     # Croatan NF NC
    'sand-county-caress':             [9, 10],                     # Wisconsin, fall best
    'bikepacking-nebraska':           [5, 6, 7, 8, 9, 10],
    'oglala-loop-nebraska':           [5, 6, 7, 8, 9, 10],
    'central-ontario-loop-trail':     [5, 6, 7, 8, 9, 10],        # Ontario
    # US — Mountain West (summer/early fall)
    'boulder-bikepacking-loop':       [5, 6, 7, 8, 9, 10],        # Boulder CO
    'family-bikepacking-salida':      [5, 6, 7, 8, 9, 10],        # Salida CO
    'elks-traverse':                  [6, 7, 8, 9],               # Elk Mountains CO
    'red-meadow-pass':                [7, 8, 9],                   # high mountain pass
    'vedauwoo-rendezvous':            [6, 7, 8, 9],               # Wyoming
    'butte-batholith-route-montana':  [6, 7, 8, 9],               # Montana
    'southern-cabinets-halfway-to-happy': [6, 7, 8, 9],           # Cabinet Mountains MT
    'the-gallatin-trail':             [6, 7, 8, 9],               # Gallatin MT
    'blackfoot-hackle-packrafting-montana-bikepacking': [6, 7, 8, 9],  # Montana
    'elkhorn-crest-trail':            [6, 7, 8, 9, 10],           # E Oregon/Idaho
    'bull-jake':                      [5, 6, 7, 8, 9, 10],        # CO or UT
    'sattitla-flow':                  [6, 7, 8, 9],               # Klamath/Siskiyou CA
    # US — Pacific California coast (mild; avoid summer fog)
    'bay-area-triple-crossover':      [3, 4, 5, 10, 11],          # Bay Area CA
    'sf-peninsula-traverse':          [3, 4, 5, 10, 11],          # San Francisco Peninsula
    'north-bay-overnighter':          [3, 4, 5, 10, 11],          # Marin/Sonoma CA
    # US/Canada — Pacific Northwest & BC
    '10-lakes-overnighter-powell-river': [5, 6, 7, 8, 9, 10],    # Powell River BC
    'bikerafting-alaska-lost-coast':  [6, 7, 8, 9],               # Alaska
    'olympic-adventure-route':        [6, 7, 8, 9],               # Olympic Peninsula WA
    'texada-ridge-runner-route':      [6, 7, 8, 9, 10],           # Texada Island BC
    'bikepacking-cypress-hills':      [6, 7, 8, 9],               # Cypress Hills AB/SK
    'crowsnest-castle-cruise':        [6, 7, 8, 9, 10],           # Alberta
    'coast-mountains-bikepacking-route': [7, 8, 9],               # BC Coast Mountains
    'three-ranges-cowboy-country':    [6, 7, 8, 9],               # probably Alberta
    # Europe — UK & Ireland
    'bikepacking-exmoor-quantock':    [5, 6, 7, 8, 9],            # Exmoor UK
    'bikepacking-scotland-the-capital-trail': [5, 6, 7, 8, 9],   # Edinburgh/Scotland
    'coals-to-newcastle-trail':       [5, 6, 7, 8, 9],            # UK
    'east-devon-trail':               [5, 6, 7, 8, 9],            # Devon UK
    'westcountry-way':                [5, 6, 7, 8, 9],            # SW England
    'north-yorkshire-moors-ramble':   [5, 6, 7, 8, 9],
    'norfolk-trains-overnighter':     [5, 6, 7, 8, 9],            # Norfolk UK
    'great-north-trail-uk':           [5, 6, 7, 8, 9],
    'highland-trail-550':             [5, 6],                      # "Best approached between May-June; overgrown/snow otherwise"
    'machair-coast':                  [6, 7, 8, 9],               # Outer Hebrides
    'the-pictish-trail':              [6, 7, 8, 9],               # Scotland
    'trans-cambrian-way':             [5, 6, 7, 8, 9],            # Wales
    'wild-nephin-way':                [5, 6, 7, 8, 9],            # Nephin, Ireland
    'clare-figure-8':                 [5, 6, 7, 8, 9],            # Clare, Ireland
    'lesser-spotted-ireland':         [5, 6, 7, 8, 9],
    # Europe — Continental
    'around-north-denmark':           [5, 6, 7, 8, 9],            # Denmark
    'jutland-backroad-overnighter':   [5, 6, 7, 8, 9],            # Jutland Denmark
    'hunebedden-overnighter':         [5, 6, 7, 8, 9],            # Netherlands
    'from-hamburg-to-heath-and-hills': [5, 6, 7, 8, 9],           # N Germany
    'bikepacking-trans-germany':      [5, 6, 7, 8, 9, 10],
    'lost-in-brandenburg-loop':       [5, 6, 7, 8, 9, 10],        # Brandenburg Germany
    'lemkivska-kobiouka':             [5, 6, 7, 8, 9],            # Ukraine Carpathians
    'swedish-safari-300':             [4, 5, 6, 7, 8, 9, 10, 11],  # "Bikeable April to November; ideal mid-Aug to late Sept"
    'veneto-divide':                  [5, 6, 7, 8, 9, 10],        # Veneto Italy
    'bikepacking-france-traversee-du-massif-vosgien': [5, 6, 7, 8, 9, 10],  # Vosges France
    'basque-bikepacking-vuelta-de-vasco': [4, 5, 6, 9, 10],       # Basque Country
    'bikepacking-transnevada-southern-spain': [3, 4, 5, 9, 10],   # S Spain (Andalusia)
    'maestrazgo-loop':                [5, 6, 9, 10],              # Aragon Spain (hot summers)
    'rodeno-algarbe-loop':            [3, 4, 5, 10, 11],          # Portugal
    # Europe — Alps & high mountains
    'tour-des-combins':               [7, 8, 9],                  # Swiss Alps
    'bikepacking-davos-switzerland':  [6, 7, 8, 9],               # Davos high Alps
    # Iceland
    'bikepacking-iceland-landmanalauger-to-skogar': [7, 8, 9],    # Iceland highland track
    'iceland-divide':                 [7, 8, 9],
    # Middle East
    'bike-touring-jordan-via-wadi-rum': [3, 4, 10, 11, 12],       # Jordan (avoid summer heat)
    # South America — Andes (dry season = southern winter Jun–Sep)
    'ausangate-traverse':             [6, 7, 8, 9],               # Peru high Andes
    'bikepacking-ecuador-the-inca-trail': [6, 7, 8, 9],           # Ecuador Andean dry season
    'conexion-oyon-peru':             [6, 7, 8, 9],               # Peru
    'dirt-road-touring-peru':         [5, 6, 7, 8, 9],
    'cycling-peru-great-divide':      [5, 6, 7, 8, 9],
    'los-tres-volcanes-ecuador':      [6, 7, 8, 9],               # Ecuador volcanoes
    'northern-cordillera-blanca-bikepacking-loop': [6, 7, 8, 9],  # Cordillera Blanca Peru
    'pululahua-crater-loop-ecuador':  [6, 7, 8, 9],               # Ecuador
    'trans-ecuador-dirt-road':        [6, 7, 8, 9],
    'trans-ecuador-singletrack':      [6, 7, 8, 9],
    'uturuncu-bikepacking-volcano-bolivia': [6, 7, 8, 9],         # Bolivia high Andes
    # South America — Patagonia / Tierra del Fuego (SH summer only)
    'bikepacking-paso-sico-argentina-chile': [12, 1, 2, 3],       # Paso Sico, high crossing
    'fin-del-mundo':                  [12, 1, 2, 3],              # Tierra del Fuego
    # Central America (dry season Nov–May)
    'bikepacking-ometepe-island-figure-8-nicaragua': [12, 1, 2, 3, 4, 5],  # Nicaragua dry
    'bikepacking-nicoya-peninsula-dirt-roads-costa-rica': [12, 1, 2, 3, 4, 5],  # Costa Rica dry
    # Africa
    'hey-joe-safari':                 [6, 7, 8, 9],               # East Africa dry season
    'bikepacking-south-africa-western-cape-passes': [3, 4, 5, 9, 10, 11],  # Western Cape SH
    # Australia (SH seasons — winter = Jun–Aug is dry/best for hot areas)
    'act2':                           [3, 4, 5, 9, 10, 11],       # ACT/Canberra area
    'fat-bikepacking-australia-canning-stock-route': [5, 6, 7, 8, 9],  # WA desert, winter
    'ikara-outback':                  [4, 5, 6, 7, 8, 9],         # Flinders Ranges SA
    'kuitpo-forest-overnighter':      [3, 4, 5, 9, 10, 11],       # Adelaide Hills SA
    'walk-the-yorke':                 [3, 4, 5, 9, 10, 11],       # Yorke Peninsula SA
    # New Zealand (SH summer = Nov–Apr)
    'no-8-wired':                     [11, 12, 1, 2, 3, 4],
    'old-ghost-road':                 [11, 12, 1, 2, 3, 4],       # NZ West Coast
    # Routes explicitly cited as missing/wrong that need manual seasons
    'reichraming-ramble':             [5, 6, 7, 8, 9, 10],        # "Mid-May to mid-October best; snow/huts closed outside"
    'road-to-freedom-greenland':      [7, 8],                      # "beginning of July to end of August recommended"
    'stone-house-lands-loop':         [3, 4, 5, 9, 10, 11],       # "best in spring and fall; avoid summer heat and late-spring floods"
    'idaho-panhandle-ramble':         [5, 6, 7, 8, 9, 10],        # Northern Idaho, spring through fall
    'cycling-the-gr5-belgian-ardennes': [4, 5, 6, 7, 8, 9, 10],  # Belgium, spring through fall
    # Uncertain location — leave null
    'goat-mountain-overnighter':      None,
    'glenha-bikerafting-loop':        None,
    'hidden-in-plain-sight':          None,
    'lakes-loop-overnighter':         None,
    'moody-forest-loop':              None,
    'pulpwood-pedaler':               None,
    'route-of-caravans-north':        None,
    'salt-and-silver-overnighter':    None,
    'st-james-loop':                  None,
    'tilton-traverse':                None,
    'two-gorges-gravel-s24o':         None,
    'baldy-bruiser':                  None,
    'echo-titus-circuit':             [11, 12, 1, 2, 3],
    # ── Parser failures: wrong text scraped or negation/range bugs ────────────
    'tcbr-norte':                     [11, 12, 1, 2, 3],   # SH summer (like tcbr-sur); text says "OUTSIDE April-May" — parser returned [4,5]
    'lagunas-y-salares':              [5, 6, 7, 8, 9, 10], # Altiplano dry season May-Oct; parser stripped May via aux-verb bug
    'morocco-traverse-south':         [2, 3, 4, 10, 11],   # "late Feb/Mar/Apr OR fall"; parser got [2,3,4] only
    'la-transgaspesie':               [6, 7, 8, 9],        # "late June...mid-September"; range gap too wide for parser
    'aspen-loop-overnighter':         [6, 7, 8, 9, 10],    # "Early summer through fall"; parser locked onto [9,10] leaf-peeper mention
    # ── Wrong text scraped — parser extracted date/event, not season ─────────
    'hold-onto-the-cats-tail':        [4, 5, 9, 10],       # Black Rock/High Rock NV: spring + fall; scraped text was a ride date
    'new-mexico-off-road-runner':     None,                 # scraped text was publication history; no valid season info
    # ── Under-extracted: parser got too few months ───────────────────────────
    'henry-coe-trial-fire-overnighter': [11, 12, 1, 2, 3, 4],  # "winter and spring most enjoyable" (Henry Coe CA); parser got [4] only
    'lincoln-national-forest-nm':     [2, 3, 4, 5],        # "late winter/spring escape" (Lincoln NF, NM); parser got [2] only
    'kootenay-confluence':            [6, 7, 8, 9],        # BC summer; parser got [6,7] (text truncated before "Summer is your best")
    'chilangos-tres-picos-overnighter': [3, 4, 5, 10, 11], # "Oct-Nov best; spring also good" — parser missed spring
}


# ── Manual tire overrides for routes where auto-extraction fails ───────────────
# Key: slug, Value: (min_mm, max_mm, display_label)
TIRE_OVERRIDES: dict[str, tuple[int | None, int | None, str | None]] = {
    'red-feather-ramble': (35, 48, '48mm'),     # "running 35s... recommend 48s"
    'norcal-outback':     (45, 50, '45–50c'),   # 45/50c drop bar optimal (c = French road size)
}


# ── Manual bike overrides for routes where the scraper captured incomplete text ─
# Key: slug, Value: (llm_ideal_bike, llm_bike_tooltip)
BIKE_OVERRIDES: dict[str, tuple[str | None, str | None]] = {
    'oh-boyaca-colombia': (
        'Rigid or Hardtail MTB',
        'A range of bikes would work on this route, and they\'ll all be the right bike at some point. '
        'Rigid is fine, but a hardtail wouldn\'t be over the top. A gravel rig is okay too. '
        'It might be a little underbiked at times, particularly if you run into some dreaded Colombian mud. '
        'Around 2” tires or bigger are recommended. We had 2.3” on rigid bikes.',
    ),
    'red-feather-ramble': (
        'Gravel Bike',
        'While you could certainly get away with running 35s for most of the route, '
        'I\'d recommend 48s for the extra stability they afford a loaded bike. '
        'Any all-road bike will do, so long as it has a decent granny gear.',
    ),
    'basin-and-batholith': (
        'Rigid MTB or ATB',
        'The ideal bike would be a Rigid MTB/ATB with at least 2.4″ tires.',
    ),
    'bear-lake-shakedown': (
        'MTB',
        'Preferred bike: Anything with 2” tires or greater. '
        'People have done it on gravel bikes with 40mm tires, but there are sections with technical descents and climbs. '
        'Due to the grades, wide range gearing is recommended.',
    ),
    'meandros-en-mitla-mexico': (
        'MTB or Gravel Bike',
        'Best bike: You can ride this weekend tour on any mountain bike, be it rigid or with front suspension. '
        'Whatever you choose, the route is almost completely rideable, bar the odd dismount and push. '
        'However, take note of the trail leading down Huayapam, which has a few technical moves. '
        'A gravel bike will be ok for most of the route, though a bike with larger volume tyres is definitely '
        'recommended, as is low gearing for the climb up to Hierve el Agua.',
    ),
    'swell-night-out': (
        'MTB',
        'Due to significant sections of the trail containing loose rock, sand and/or occasional mud, '
        'the route should not be attempted on anything less than a mountain bike. '
        'The authors completed development of the route on plus bikes with 3 inch tires. '
        'Fatbikes would be equally suitable for the entirety of this route.',
    ),
    'la-observer': (
        'Hardtail MTB or Gravel Bike',
        'A standard hardtail, rigid or otherwise, is probably about perfect for this ride. '
        'But you\'d be fine on a gravel/adventure bike with 40mm+ tyres or so, if you take it easy on the '
        'singletrack descent and watch out for watersnakes and loose patches '
        '(locals love to \'underbike\' in the National Forest). Pack light and bring your low gears!',
    ),
    'death-valley-dustup': (
        'Hardtail MTB',
        'Much like the ideal season for this route, the best tire is also a bit of a goldilocks. '
        'Less than 2.5″ will have you suffering through the sandy sections, but a fat bike is likely '
        'overkill due to the long pavement stretches crossing the Inyos. '
        'Though a skilled rider could manage this route on a rigid, front suspension will be much more '
        'comfortable, especially on chunky, loose, and steep descents.',
    ),
    'zillertal-trail': (
        'Hardtail MTB or Gravel Bike',
        'The loop can also be done on a hardtail, rigid travel bike, or gravel bike, though you\'ll '
        'experience more bumps, less comfort, and—depending on your bike and luggage—more weight to '
        'carry on the hike-a-bike sections.',
    ),
    'kenya-bike-odyssey': (
        'MTB',
        'A mountain bike with 2.2"–2.4" tires is recommended for this route.',
    ),
}


def process_route(r: dict) -> dict:
    slug = r['slug']

    # ── Season ────────────────────────────────────────────────────────
    if slug in SEASON_OVERRIDES:
        months = SEASON_OVERRIDES[slug]
    else:
        # Use the fixed parse_best_season_months on the best_season text
        months = parse_best_season_months(r.get('best_season') or '') or None
        if months == []:
            months = None

    # ── Tire widths ────────────────────────────────────────────────────
    # Prefer tire_width_notes over ideal_bike text for tire extraction
    tire_text = r.get('tire_width_notes') or r.get('ideal_bike') or ''
    t_min, t_max, t_notes = _parse_tire_widths_from_text(tire_text)

    # If tire notes extracted nothing but bike text has it, try bike text
    if t_min is None and r.get('ideal_bike'):
        t_min, t_max, t_notes = _parse_tire_widths_from_text(r['ideal_bike'])

    # Apply manual tire overrides
    if slug in TIRE_OVERRIDES:
        t_min, t_max, t_notes = TIRE_OVERRIDES[slug]

    # ── Ideal bike ─────────────────────────────────────────────────────
    if slug in BIKE_OVERRIDES:
        bike_label, bike_tip = BIKE_OVERRIDES[slug]
    else:
        bike_label, bike_tip = _extract_ideal_bike(r.get('ideal_bike'))
        # Fix scraped texts that start mid-sentence (scraper captured wrong sentence boundary)
        if bike_tip:
            if re.match(r'^for\s+this\s+route\b', bike_tip, re.I):
                bike_tip = 'The ideal bike ' + bike_tip
            elif re.match(r'^to\s+[a-z]', bike_tip):
                bike_tip = 'The ideal bike ' + bike_tip
            elif re.match(r'^would\s+be\b', bike_tip, re.I):
                bike_tip = 'The ideal bike ' + bike_tip

    return {
        'slug': slug,
        'llm_best_season_months': months,
        'llm_ideal_bike': bike_label,
        'llm_bike_tooltip': bike_tip,
        'llm_tire_width_min_mm': t_min,
        'llm_tire_width_max_mm': t_max,
        'llm_tire_width_notes': t_notes,
    }


def main() -> None:
    in_path = Path('llm_input.json')
    out_path = Path('llm_output.json')

    data = json.loads(in_path.read_text())
    results = []

    for r in data:
        out = process_route(r)
        # Only include routes where we have at least one LLM field
        if any(v is not None for k, v in out.items() if k != 'slug'):
            results.append(out)

    out_path.write_text(json.dumps(results, indent=2))
    print(f'Processed {len(results)}/{len(data)} routes with LLM data → {out_path}')

    # Print a sample
    for r in results[:5]:
        print(f"  {r['slug']}: months={r['llm_best_season_months']}, bike={r['llm_ideal_bike']}, "
              f"tire={r['llm_tire_width_min_mm']}-{r['llm_tire_width_max_mm']}mm")


if __name__ == '__main__':
    main()
