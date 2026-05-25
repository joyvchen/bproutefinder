-- Bikepacking Route Finder — Supabase Schema
-- Run this in the Supabase SQL editor to initialize your database.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- routes
-- ============================================================
CREATE TABLE routes (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug              TEXT UNIQUE NOT NULL,          -- derived from bikepacking.com URL path
  source_url        TEXT NOT NULL,                 -- canonical bikepacking.com URL
  name              TEXT NOT NULL,
  description       TEXT,                          -- short excerpt from route page

  -- Location
  region            TEXT,                          -- e.g. "Pacific Northwest"
  state             TEXT,                          -- e.g. "Oregon", "British Columbia"
  country           TEXT DEFAULT 'USA',
  lat               DOUBLE PRECISION,              -- geocoded centroid (state level)
  lng               DOUBLE PRECISION,

  -- Route stats (as shown on Bikepacking.com)
  distance_mi       NUMERIC(8,2),
  distance_km       NUMERIC(8,2),
  elevation_gain_ft INTEGER,                       -- labeled "Ascent" on bikepacking.com
  elevation_gain_m  INTEGER,
  days_min          SMALLINT,
  days_max          SMALLINT,

  -- Bikepacking.com numeric ratings (scraped verbatim)
  difficulty        NUMERIC(3,1),                  -- 1–10 scale
  unpaved_pct       SMALLINT,                      -- 0–100
  singletrack_pct   SMALLINT,                      -- 0–100
  rideable_pct      SMALLINT,                      -- 0–100

  -- Gear recommendations (scraped from editorial body text)
  bike_type         TEXT[],                        -- e.g. ['gravel', 'hardtail', 'full-sus']
  tire_width_min_mm SMALLINT,                      -- e.g. 40
  tire_width_max_mm SMALLINT,                      -- e.g. 55

  -- Imagery
  image_url         TEXT,
  image_alt         TEXT,

  -- Editorial badges
  is_top_pick          BOOLEAN DEFAULT FALSE,
  recommendation_score INTEGER DEFAULT 0,          -- count of editorial appearances

  -- Scrape tracking
  scraped_at        TIMESTAMPTZ DEFAULT NOW(),
  detail_scraped_at TIMESTAMPTZ,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW(),

  -- Full-text search (auto-maintained)
  fts TSVECTOR GENERATED ALWAYS AS (
    to_tsvector('english',
      coalesce(name, '') || ' ' ||
      coalesce(region, '') || ' ' ||
      coalesce(state, '') || ' ' ||
      coalesce(country, '') || ' ' ||
      coalesce(description, ''))
  ) STORED
);

-- Indexes
CREATE INDEX idx_routes_fts         ON routes USING GIN(fts);
CREATE INDEX idx_routes_trgm        ON routes USING GIN(name gin_trgm_ops);
CREATE INDEX idx_routes_state       ON routes(state);
CREATE INDEX idx_routes_country     ON routes(country);
CREATE INDEX idx_routes_difficulty  ON routes(difficulty);
CREATE INDEX idx_routes_is_top_pick ON routes(is_top_pick);
CREATE INDEX idx_routes_distance_mi ON routes(distance_mi);
CREATE INDEX idx_routes_elevation   ON routes(elevation_gain_ft);
CREATE INDEX idx_routes_days        ON routes(days_min, days_max);
CREATE INDEX idx_routes_rec_score   ON routes(recommendation_score DESC);
CREATE INDEX idx_routes_coords      ON routes(lat, lng) WHERE lat IS NOT NULL AND lng IS NOT NULL;

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_routes_updated_at
  BEFORE UPDATE ON routes
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- editorial_features
-- ============================================================
CREATE TABLE editorial_features (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  route_id     UUID REFERENCES routes(id) ON DELETE CASCADE,
  source_url   TEXT NOT NULL,
  source_title TEXT,
  scraped_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(route_id, source_url)
);

CREATE INDEX idx_editorial_route_id ON editorial_features(route_id);

-- ============================================================
-- Sync recommendation_score after editorial scrape
-- Call this function after running Pass 3 of the scraper.
-- ============================================================
CREATE OR REPLACE FUNCTION sync_recommendation_scores()
RETURNS void AS $$
BEGIN
  -- Reset all scores
  UPDATE routes SET recommendation_score = 0, is_top_pick = FALSE
  WHERE recommendation_score > 0 OR is_top_pick = TRUE;

  -- Apply counts from editorial_features
  UPDATE routes r
  SET
    recommendation_score = subq.score,
    is_top_pick = TRUE
  FROM (
    SELECT route_id, COUNT(*) AS score
    FROM editorial_features
    GROUP BY route_id
  ) subq
  WHERE r.id = subq.route_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Row Level Security — public read-only
-- The scraper uses the service_role key (bypasses RLS).
-- The Next.js frontend uses the anon key (read-only via these policies).
-- ============================================================
ALTER TABLE routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE editorial_features ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read routes"
  ON routes FOR SELECT USING (true);

CREATE POLICY "Public read editorial_features"
  ON editorial_features FOR SELECT USING (true);
