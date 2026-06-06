#!/usr/bin/env python3
"""
Quick regression test for parse_best_season_months.
Run: python test_season.py
"""
import sys
sys.path.insert(0, '.')
from utils import parse_best_season_months, MONTH_NAMES

MONTH_ABBR = {v: k.capitalize()[:3] for k, v in MONTH_NAMES.items() if len(k) == 3}
MONTH_ABBR[5] = 'May'


def fmt(months):
    return [MONTH_ABBR.get(m, str(m)) for m in months]


CASES = [
    # (label, text, expected_months)

    # ── Previously fixed ──────────────────────────────────────────────
    ("Year-round",
     "This route can be ridden year-round.",
     list(range(1, 13))),

    ("Simple range Jun-Oct",
     "Best ridden June through October.",
     [6, 7, 8, 9, 10]),

    ("Cross-year Sep-Jun",
     "Rideable September through June.",
     [1, 2, 3, 4, 5, 6, 9, 10, 11, 12]),

    ("Spring+fall union (sparse)",
     "Spring and fall are the ideal seasons. May and October are particularly good months.",
     [3, 4, 5, 9, 10, 11]),

    ("Season clause split",
     "Summer and fall are best since spring and winter are very wet and snowy.",
     [6, 7, 8, 9, 10, 11]),

    ("Anytime year-round",
     "You can ride this route anytime.",
     list(range(1, 13))),

    ("Positive range preference",
     "Winter brings snow and cold. Best ridden May through September.",
     [5, 6, 7, 8, 9]),

    # ── Fix 1: auxiliary 'may' ─────────────────────────────────────────
    ("Sea to Sky — auxiliary may",
     "The route may be rideable from June to October.",
     [6, 7, 8, 9, 10]),

    ("May as month (not auxiliary)",
     "Best ridden from May through September.",
     [5, 6, 7, 8, 9]),

    # ── Fix 2: season-to-season range ────────────────────────────────
    ("Lac du Bois — spring through fall",
     "Can be ridden from spring through fall.",
     [3, 4, 5, 6, 7, 8, 9, 10, 11]),

    ("Summer through fall",
     "Rideable summer through fall.",
     [6, 7, 8, 9, 10, 11]),

    ("Spring to summer",
     "Best from spring to summer.",
     [3, 4, 5, 6, 7, 8]),

    # ── Fix 3: consecutive months not expanded ────────────────────────
    ("Dollarhide — consecutive months not expanded",
     "The route is best ridden in the late spring, summer, and fall. "
     "The ideal window is June through September.",
     [6, 7, 8, 9]),

    ("Sparse months DO expand to season",
     "Spring and fall are ideal. May and October are the best months.",
     [3, 4, 5, 9, 10, 11]),
]

passed = 0
failed = 0
for label, text, expected in CASES:
    got = parse_best_season_months(text)
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
        print(f"[{status}] {label}")
    else:
        failed += 1
        print(f"[{status}] {label}")
        print(f"       text:     {text!r}")
        print(f"       expected: {fmt(expected)}")
        print(f"       got:      {fmt(got)}")

print(f"\n{passed}/{passed+failed} passed")
if failed:
    sys.exit(1)
