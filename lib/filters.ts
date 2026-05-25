import { FilterState, DEFAULT_FILTERS, SortOption } from './types'

export function filtersToParams(filters: FilterState): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.q) params.q = filters.q
  if (filters.state) params.state = filters.state
  if (filters.bike_type.length) params.bike_type = filters.bike_type.join(',')
  if (filters.difficulty_min != null) params.difficulty_min = String(filters.difficulty_min)
  if (filters.difficulty_max != null) params.difficulty_max = String(filters.difficulty_max)
  if (filters.days_min != null) params.days_min = String(filters.days_min)
  if (filters.days_max != null) params.days_max = String(filters.days_max)
  if (filters.distance_min != null) params.distance_min = String(filters.distance_min)
  if (filters.distance_max != null) params.distance_max = String(filters.distance_max)
  if (filters.elevation_max != null) params.elevation_max = String(filters.elevation_max)
  if (filters.unpaved_min != null) params.unpaved_min = String(filters.unpaved_min)
  if (filters.singletrack_min != null) params.singletrack_min = String(filters.singletrack_min)
  if (filters.tire_width_min != null) params.tire_width_min = String(filters.tire_width_min)
  if (filters.tire_width_max != null) params.tire_width_max = String(filters.tire_width_max)
  if (filters.top_pick_only) params.top_pick_only = 'true'
  if (filters.sort !== 'recommended') params.sort = filters.sort
  return params
}

export function paramsToFilters(searchParams: URLSearchParams): FilterState {
  return {
    q: searchParams.get('q') ?? '',
    state: searchParams.get('state') ?? '',
    bike_type: searchParams.get('bike_type')?.split(',').filter(Boolean) ?? [],
    difficulty_min: parseNum(searchParams.get('difficulty_min')),
    difficulty_max: parseNum(searchParams.get('difficulty_max')),
    days_min: parseNum(searchParams.get('days_min')),
    days_max: parseNum(searchParams.get('days_max')),
    distance_min: parseNum(searchParams.get('distance_min')),
    distance_max: parseNum(searchParams.get('distance_max')),
    elevation_max: parseNum(searchParams.get('elevation_max')),
    unpaved_min: parseNum(searchParams.get('unpaved_min')),
    singletrack_min: parseNum(searchParams.get('singletrack_min')),
    tire_width_min: parseNum(searchParams.get('tire_width_min')),
    tire_width_max: parseNum(searchParams.get('tire_width_max')),
    top_pick_only: searchParams.get('top_pick_only') === 'true',
    sort: (searchParams.get('sort') as SortOption) ?? 'recommended',
  }
}

export function isDefaultFilters(filters: FilterState): boolean {
  return JSON.stringify(filters) === JSON.stringify(DEFAULT_FILTERS)
}

export function activeFilterCount(filters: FilterState): number {
  let count = 0
  if (filters.q) count++
  if (filters.state) count++
  if (filters.bike_type.length) count++
  if (filters.difficulty_min != null || filters.difficulty_max != null) count++
  if (filters.days_min != null || filters.days_max != null) count++
  if (filters.distance_min != null || filters.distance_max != null) count++
  if (filters.elevation_max != null) count++
  if (filters.unpaved_min != null) count++
  if (filters.singletrack_min != null) count++
  if (filters.tire_width_min != null || filters.tire_width_max != null) count++
  if (filters.top_pick_only) count++
  return count
}

function parseNum(val: string | null): number | null {
  if (!val) return null
  const n = parseFloat(val)
  return isNaN(n) ? null : n
}

export const SORT_LABELS: Record<SortOption, string> = {
  recommended: 'Most Recommended',
  distance_asc: 'Shortest First',
  distance_desc: 'Longest First',
  elevation_asc: 'Least Climbing',
  elevation_desc: 'Most Climbing',
  days_asc: 'Fewest Days',
  days_desc: 'Most Days',
  difficulty_asc: 'Easiest First',
  difficulty_desc: 'Hardest First',
}

export const US_STATES = [
  'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut',
  'Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa',
  'Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan',
  'Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire',
  'New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio',
  'Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota',
  'Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia',
  'Wisconsin','Wyoming',
]

export const INTERNATIONAL_REGIONS = [
  'Canada','Mexico','Europe','United Kingdom','France','Spain','Italy','Switzerland',
  'Austria','Germany','Norway','Sweden','Iceland','New Zealand','Australia',
  'Japan','South America','Colombia','Peru','Nepal','South Africa',
]
