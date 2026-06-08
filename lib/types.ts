export interface Route {
  id: string
  slug: string
  source_url: string
  name: string
  description: string | null
  region: string | null
  state: string | null
  country: string
  lat: number | null
  lng: number | null

  distance_mi: number | null
  distance_km: number | null
  elevation_gain_ft: number | null
  elevation_gain_m: number | null
  days_min: number | null
  days_max: number | null

  difficulty: number | null      // 1–10 (Bikepacking.com scale)
  climbing_scale: number | null        // 1–10
  technical_difficulty: number | null  // 1–10
  physical_demand: number | null       // 1–10
  resupply_logistics: number | null    // 1–10
  unpaved_pct: number | null     // 0–100
  singletrack_pct: number | null // 0–100
  rideable_pct: number | null    // 0–100

  bike_type: string[] | null
  tire_width_min_mm: number | null
  tire_width_max_mm: number | null
  tire_width_notes: string | null

  image_url: string | null
  image_alt: string | null

  high_point_ft: number | null
  high_point_m: number | null
  best_season: string | null
  best_season_months: number[] | null
  ideal_bike: string | null

  llm_best_season_months: number[] | null
  llm_ideal_bike: string | null
  llm_bike_tooltip: string | null
  llm_tire_width_min_mm: number | null
  llm_tire_width_max_mm: number | null
  llm_tire_width_notes: string | null

  rwgps_route_id: string | null
  rwgps_embed_url: string | null

  editorial_source_url: string | null
  editorial_label: string | null

  is_top_pick: boolean
  recommendation_score: number

  scraped_at: string
  detail_scraped_at: string | null
  created_at: string
  updated_at: string
}

export type SortOption =
  | 'recommended'
  | 'distance_asc'
  | 'distance_desc'
  | 'elevation_asc'
  | 'elevation_desc'
  | 'days_asc'
  | 'days_desc'
  | 'difficulty_asc'
  | 'difficulty_desc'

export interface FilterState {
  q: string
  regions: string[]
  states: string[]
  bike_type: string[]
  difficulty_min: number | null
  difficulty_max: number | null
  climbing_scale_min: number | null
  climbing_scale_max: number | null
  technical_difficulty_min: number | null
  technical_difficulty_max: number | null
  physical_demand_min: number | null
  physical_demand_max: number | null
  resupply_logistics_min: number | null
  resupply_logistics_max: number | null
  days_min: number | null
  days_max: number | null
  distance_min: number | null
  distance_max: number | null
  elevation_min: number | null
  elevation_max: number | null
  unpaved_min: number | null
  unpaved_max: number | null
  singletrack_min: number | null
  singletrack_max: number | null
  tire_width_min: number | null
  tire_width_max: number | null
  months: number[]
  top_pick_only: boolean
  sort: SortOption
}

export const DEFAULT_FILTERS: FilterState = {
  q: '',
  regions: [],
  states: [],
  bike_type: [],
  difficulty_min: null,
  difficulty_max: null,
  climbing_scale_min: null,
  climbing_scale_max: null,
  technical_difficulty_min: null,
  technical_difficulty_max: null,
  physical_demand_min: null,
  physical_demand_max: null,
  resupply_logistics_min: null,
  resupply_logistics_max: null,
  days_min: null,
  days_max: null,
  distance_min: null,
  distance_max: null,
  elevation_min: null,
  elevation_max: null,
  unpaved_min: null,
  unpaved_max: null,
  singletrack_min: null,
  singletrack_max: null,
  tire_width_min: null,
  tire_width_max: null,
  months: [],
  top_pick_only: false,
  sort: 'recommended',
}

export interface RoutesResponse {
  routes: Route[]
  total: number
}

export interface RouteGeoJSON {
  type: 'FeatureCollection'
  features: RouteFeature[]
}

export interface RouteFeature {
  type: 'Feature'
  geometry: {
    type: 'Point'
    coordinates: [number, number] // [lng, lat]
  }
  properties: {
    id: string
    slug: string
    name: string
    source_url: string
    state: string | null
    country: string | null
    distance_mi: number | null
    days_min: number | null
    days_max: number | null
    difficulty: number | null
    is_top_pick: boolean
    editorial_source_url: string | null
    editorial_label: string | null
    image_url: string | null
    rwgps_route_id: string | null
  }
}
