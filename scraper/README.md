# Bikepacking Route Finder — Scraper

A three-pass Python scraper that populates the Supabase database with route data from Bikepacking.com.

## Setup

```bash
cd scraper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Copy and fill in your env vars
cp .env.example .env
```

## Environment Variables

Edit `scraper/.env`:
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...   # service_role key from Supabase project settings
```

## Running the Scraper

```bash
# Full pipeline (all 3 passes)
python main.py --pass all

# Individual passes
python main.py --pass listing     # Pass 1: get all routes from the listing page
python main.py --pass detail      # Pass 2: enrich routes with detail page data
python main.py --pass editorial   # Pass 3: assign Top Pick badges

# Test with a small sample (no DB writes)
python main.py --pass listing --limit 10 --dry-run
```

## Pass Overview

| Pass | Source | Extracts |
|------|--------|----------|
| 1 — listing | `/bikepacking-routes/` | name, URL, image, location, distance, days |
| 2 — detail | Individual route pages | difficulty, ascent, unpaved/singletrack/rideable %, bike type, tire width, description |
| 3 — editorial | Roundup pages (see `config.py`) | Top Pick badge assignments |

## Respecting Bikepacking.com

- Pass 1 uses Playwright (JS-rendered pagination)
- Passes 2 & 3 use `requests` with a 2–5 second random delay between requests
- The User-Agent identifies this scraper
- Robots.txt is respected (route content is not blocked)
- Only structured metadata is stored — no full editorial content is duplicated
