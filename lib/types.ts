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
  unpaved_pct: number | null     // 0–100
  singletrack_pct: number | null // 0–100
  rideable_pct: number | null    // 0–100

  bike_type: string[] | null
  tire_width_min_mm: number | null
  tire_width_max_mm: number | null

  image_url: string | null
  image_alt: string | null

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
  state: string
  bike_type: string[]
  difficulty_min: number | null
  difficulty_max: number | null
  days_min: number | null
  days_max: number | null
  distance_min: number | null
  distance_max: number | null
  elevation_max: number | null
  unpaved_min: number | null
  singletrack_min: number | null
  tire_width_min: number | null
  tire_width_max: number | null
  top_pick_only: boolean
  sort: SortOption
}

export const DEFAULT_FILTERS: FilterState = {
  q: '',
  state: '',
  bike_type: [],
  difficulty_min: null,
  difficulty_max: null,
  days_min: null,
  days_max: null,
  distance_min: null,
  distance_max: null,
  elevation_max: null,
  unpaved_min: null,
  singletrack_min: null,
  tire_width_min: null,
  tire_width_max: null,
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
    state: string | null
    distance_mi: number | null
    days_min: number | null
    days_max: number | null
    difficulty: number | null
    is_top_pick: boolean
    image_url: string | null
  }
}
