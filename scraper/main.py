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
import asyncio
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
    return parser.parse_args()


async def run_listing(limit, dry_run):
    from browser import get_browser, new_page
    import scrape_listing

    async with get_browser() as browser:
        context, page = await new_page(browser)
        try:
            await scrape_listing.run(page, limit=limit, dry_run=dry_run)
        finally:
            await context.close()


def run_detail(limit, dry_run):
    import scrape_detail
    scrape_detail.run(limit=limit, dry_run=dry_run)


def run_editorial(dry_run):
    import scrape_editorial
    scrape_editorial.run(dry_run=dry_run)


def main():
    args = parse_args()
    pass_ = args.pass_
    limit = args.limit
    dry_run = args.dry_run

    if dry_run:
        print("=== DRY RUN — no database writes ===\n")

    if pass_ in ('listing', 'all'):
        asyncio.run(run_listing(limit, dry_run))

    if pass_ in ('detail', 'all'):
        run_detail(limit, dry_run)

    if pass_ in ('editorial', 'all'):
        run_editorial(dry_run)

    print("\nDone.")


if __name__ == '__main__':
    main()
