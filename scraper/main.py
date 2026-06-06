#!/usr/bin/env python3
"""
Bikepacking Route Finder — scraper CLI.

Usage:
  python main.py --pass all
  python main.py --pass listing
  python main.py --pass detail
  python main.py --pass editorial
  python main.py --pass listing --limit 20 --dry-run
"""
import argparse
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Bikepacking Route Finder scraper")
    parser.add_argument(
        '--pass',
        dest='pass_',
        choices=['listing', 'detail', 'editorial', 'all'],
        required=True,
        help='Which scraping pass to run',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit the number of routes processed (useful for testing)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse and print results without writing to the database',
    )
    parser.add_argument(
        '--force-null-fields',
        action='store_true',
        help='Re-scrape detail pages for routes missing ideal_bike or tire_width (ignores detail_scraped_at)',
    )
    parser.add_argument(
        '--force-all',
        action='store_true',
        help='Re-scrape detail pages for ALL routes, overwriting existing data (full rescrape)',
    )
    return parser.parse_args()


def run_listing(limit, dry_run):
    import scrape_listing
    scrape_listing.run(limit=limit, dry_run=dry_run)


def run_detail(limit, dry_run, force_null_fields=False, force_all=False):
    import scrape_detail
    scrape_detail.run(limit=limit, dry_run=dry_run,
                      force_null_fields=force_null_fields, force_all=force_all)


def run_editorial(dry_run):
    import scrape_editorial
    scrape_editorial.run(dry_run=dry_run)


def main():
    args = parse_args()
    pass_ = args.pass_
    limit = args.limit
    dry_run = args.dry_run
    force_null_fields = args.force_null_fields
    force_all = args.force_all

    if dry_run:
        print("=== DRY RUN — no database writes ===\n", flush=True)

    print(f"Running pass: {pass_}", flush=True)

    if pass_ in ('listing', 'all'):
        run_listing(limit, dry_run)

    if pass_ in ('detail', 'all'):
        run_detail(limit, dry_run, force_null_fields=force_null_fields, force_all=force_all)

    if pass_ in ('editorial', 'all'):
        run_editorial(dry_run)

    print("\nDone.")


if __name__ == '__main__':
    main()
