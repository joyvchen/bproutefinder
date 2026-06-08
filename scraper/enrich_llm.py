#!/usr/bin/env python3
"""
LLM enrichment helper.

  python enrich_llm.py --mode fetch [--out llm_input.json]
      Fetch all routes from Supabase and write raw text fields to a JSON file
      for in-conversation Claude processing.

  python enrich_llm.py --mode write --in llm_output.json [--dry-run]
      Read Claude's interpreted values from a JSON file and write them back
      to Supabase (only the llm_* columns are touched).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from upsert import get_client, update_route_detail


def fetch(out_path: Path) -> None:
    client = get_client()
    # Page through all routes (Supabase default limit is 1000)
    rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        result = (
            client.table("routes")
            .select(
                "slug, name, source_url, "
                "best_season, best_season_months, "
                "ideal_bike, tire_width_notes, "
                "tire_width_min_mm, tire_width_max_mm"
            )
            .order("name")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = result.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    out_path.write_text(json.dumps(rows, indent=2))
    print(f"Fetched {len(rows)} routes → {out_path}")


def write_back(in_path: Path, dry_run: bool) -> None:
    data = json.loads(in_path.read_text())
    if not isinstance(data, list):
        print("ERROR: expected a JSON array", file=sys.stderr)
        sys.exit(1)

    llm_keys = {
        "llm_best_season_months",
        "llm_ideal_bike",
        "llm_bike_tooltip",
        "llm_tire_width_min_mm",
        "llm_tire_width_max_mm",
        "llm_tire_width_notes",
    }

    updated = 0
    skipped = 0
    for row in data:
        slug = row.get("slug")
        if not slug:
            print(f"  WARNING: row missing slug, skipping: {row}")
            skipped += 1
            continue
        payload = {k: row[k] for k in llm_keys if k in row}
        if not payload:
            skipped += 1
            continue
        if dry_run:
            print(f"  [dry-run] {slug}: {list(payload.keys())}")
        else:
            update_route_detail(slug, payload)
        updated += 1

    print(f"{'[dry-run] ' if dry_run else ''}Updated {updated} routes, skipped {skipped}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["fetch", "write"], required=True)
    parser.add_argument("--out", default="llm_input.json")
    parser.add_argument("--in", dest="in_file", default="llm_output.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.mode == "fetch":
        fetch(Path(args.out))
    else:
        write_back(Path(args.in_file), args.dry_run)


if __name__ == "__main__":
    main()
