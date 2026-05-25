# Bikepacking Route Finder

A map-first discovery app for [Bikepacking.com](https://bikepacking.com) routes. Search, filter, and explore routes by location, difficulty, distance, bike type, and more — all on an interactive map.

Every route links back to the original Bikepacking.com page. This app stores structured metadata only.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14 (App Router), React, TypeScript, Tailwind CSS |
| Database | Supabase (PostgreSQL) |
| Maps | Mapbox GL JS |
| Data fetching | SWR |
| Scraper | Python + Playwright + BeautifulSoup |
| Deploy | Vercel |

## Quick Start

### 1. Supabase setup

1. Create a project at [supabase.com](https://supabase.com)
2. Open **SQL Editor** → paste and run `supabase/schema.sql`
3. Copy your **Project URL** and **anon public** key

### 2. Mapbox setup

1. Get a token at [account.mapbox.com](https://account.mapbox.com)
2. In production, restrict the token to your Vercel domain

### 3. Environment variables

```bash
cp .env.example .env.local
# Fill in:
#   NEXT_PUBLIC_SUPABASE_URL
#   NEXT_PUBLIC_SUPABASE_ANON_KEY
#   NEXT_PUBLIC_MAPBOX_TOKEN
```

### 4. Install and run

```bash
npm install
npm run dev
# → http://localhost:3000
```

### 5. Run the scraper

See [scraper/README.md](scraper/README.md) for full instructions.

```bash
cd scraper
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # fill in SUPABASE_URL + SUPABASE_SERVICE_KEY

# Test scraper (no DB writes)
python main.py --pass listing --limit 10 --dry-run

# Full pipeline
python main.py --pass all
```

## Scraper passes

| Pass | What it does |
|------|-------------|
| `listing` | Scrapes all route cards from `/bikepacking-routes/` (Playwright for JS pagination) |
| `detail` | Enriches each route with difficulty, ascent, % stats, bike type, tire width |
| `editorial` | Assigns Top Pick badges from editorial roundup pages |

## Deploy to Vercel

```bash
npm install -g vercel
vercel login
vercel --prod

# Set env vars in Vercel dashboard or:
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
vercel env add NEXT_PUBLIC_MAPBOX_TOKEN
```

## Features

- **Map-first UI** — full-screen Mapbox map with clustered route markers
- **Real filters** using Bikepacking.com's own data: Difficulty (1–10), Unpaved %, Singletrack %, Rideable %, Ascent (ft), Tire Width (mm), Bike Type
- **Top Pick badges** — routes featured in Bikepacking.com editorial roundups
- **List view** — responsive grid of route cards
- **Route detail page** — stats + excerpt + link to original Bikepacking.com page
- **ISR** — detail pages cached and auto-revalidated hourly
- **Edge runtime** — API routes run at Vercel edge for fast response
