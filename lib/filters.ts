import { FilterState, DEFAULT_FILTERS, SortOption } from './types'

export function filtersToParams(filters: FilterState): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.q) params.q = filters.q
  if (filters.regions.length) params.regions = filters.regions.join(',')
  if (filters.states.length) params.states = filters.states.join('|')
  if (filters.bike_type.length) params.bike_type = filters.bike_type.join(',')
  if (filters.difficulty_min != null) params.difficulty_min = String(filters.difficulty_min)
  if (filters.difficulty_max != null) params.difficulty_max = String(filters.difficulty_max)
  if (filters.climbing_scale_min != null) params.climbing_scale_min = String(filters.climbing_scale_min)
  if (filters.climbing_scale_max != null) params.climbing_scale_max = String(filters.climbing_scale_max)
  if (filters.technical_difficulty_min != null) params.technical_difficulty_min = String(filters.technical_difficulty_min)
  if (filters.technical_difficulty_max != null) params.technical_difficulty_max = String(filters.technical_difficulty_max)
  if (filters.physical_demand_min != null) params.physical_demand_min = String(filters.physical_demand_min)
  if (filters.physical_demand_max != null) params.physical_demand_max = String(filters.physical_demand_max)
  if (filters.resupply_logistics_min != null) params.resupply_logistics_min = String(filters.resupply_logistics_min)
  if (filters.resupply_logistics_max != null) params.resupply_logistics_max = String(filters.resupply_logistics_max)
  if (filters.days_min != null) params.days_min = String(filters.days_min)
  if (filters.days_max != null) params.days_max = String(filters.days_max)
  if (filters.distance_min != null) params.distance_min = String(filters.distance_min)
  if (filters.distance_max != null) params.distance_max = String(filters.distance_max)
  if (filters.elevation_min != null) params.elevation_min = String(filters.elevation_min)
  if (filters.elevation_max != null) params.elevation_max = String(filters.elevation_max)
  if (filters.unpaved_min != null) params.unpaved_min = String(filters.unpaved_min)
  if (filters.unpaved_max != null) params.unpaved_max = String(filters.unpaved_max)
  if (filters.singletrack_min != null) params.singletrack_min = String(filters.singletrack_min)
  if (filters.singletrack_max != null) params.singletrack_max = String(filters.singletrack_max)
  if (filters.tire_width_min != null) params.tire_width_min = String(filters.tire_width_min)
  if (filters.tire_width_max != null) params.tire_width_max = String(filters.tire_width_max)
  if (filters.months.length) params.months = filters.months.join(',')
  if (filters.top_pick_only) params.top_pick_only = 'true'
  if (filters.sort !== 'recommended') params.sort = filters.sort
  return params
}

export function paramsToFilters(searchParams: URLSearchParams): FilterState {
  return {
    q: searchParams.get('q') ?? '',
    regions: searchParams.get('regions')?.split(',').filter(Boolean) ?? [],
    states: searchParams.get('states')?.split('|').filter(Boolean) ?? [],
    bike_type: searchParams.get('bike_type')?.split(',').filter(Boolean) ?? [],
    difficulty_min: parseNum(searchParams.get('difficulty_min')),
    difficulty_max: parseNum(searchParams.get('difficulty_max')),
    climbing_scale_min: parseNum(searchParams.get('climbing_scale_min')),
    climbing_scale_max: parseNum(searchParams.get('climbing_scale_max')),
    technical_difficulty_min: parseNum(searchParams.get('technical_difficulty_min')),
    technical_difficulty_max: parseNum(searchParams.get('technical_difficulty_max')),
    physical_demand_min: parseNum(searchParams.get('physical_demand_min')),
    physical_demand_max: parseNum(searchParams.get('physical_demand_max')),
    resupply_logistics_min: parseNum(searchParams.get('resupply_logistics_min')),
    resupply_logistics_max: parseNum(searchParams.get('resupply_logistics_max')),
    days_min: parseNum(searchParams.get('days_min')),
    days_max: parseNum(searchParams.get('days_max')),
    distance_min: parseNum(searchParams.get('distance_min')),
    distance_max: parseNum(searchParams.get('distance_max')),
    elevation_min: parseNum(searchParams.get('elevation_min')),
    elevation_max: parseNum(searchParams.get('elevation_max')),
    unpaved_min: parseNum(searchParams.get('unpaved_min')),
    unpaved_max: parseNum(searchParams.get('unpaved_max')),
    singletrack_min: parseNum(searchParams.get('singletrack_min')),
    singletrack_max: parseNum(searchParams.get('singletrack_max')),
    tire_width_min: parseNum(searchParams.get('tire_width_min')),
    tire_width_max: parseNum(searchParams.get('tire_width_max')),
    months: searchParams.get('months')?.split(',').map(Number).filter(Boolean) ?? [],
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
  if (filters.regions.length || filters.states.length) count++
  if (filters.bike_type.length) count++
  if (filters.difficulty_min != null || filters.difficulty_max != null) count++
  if (filters.climbing_scale_min != null || filters.climbing_scale_max != null) count++
  if (filters.technical_difficulty_min != null || filters.technical_difficulty_max != null) count++
  if (filters.physical_demand_min != null || filters.physical_demand_max != null) count++
  if (filters.resupply_logistics_min != null || filters.resupply_logistics_max != null) count++
  if (filters.days_min != null || filters.days_max != null) count++
  if (filters.distance_min != null || filters.distance_max != null) count++
  if (filters.elevation_min != null || filters.elevation_max != null) count++
  if (filters.unpaved_min != null || filters.unpaved_max != null) count++
  if (filters.singletrack_min != null || filters.singletrack_max != null) count++
  if (filters.tire_width_min != null || filters.tire_width_max != null) count++
  if (filters.months.length) count++
  if (filters.top_pick_only) count++
  return count
}

function parseNum(val: string | null): number | null {
  if (!val) return null
  const n = parseFloat(val)
  return isNaN(n) ? null : n
}

export const SORT_LABELS: Record<SortOption, string> = {
  recommended: 'Recommended First',
  distance_asc: 'Shortest First',
  distance_desc: 'Longest First',
  elevation_asc: 'Least Climbing',
  elevation_desc: 'Most Climbing',
  days_asc: 'Fewest Days',
  days_desc: 'Most Days',
  difficulty_asc: 'Easiest First',
  difficulty_desc: 'Hardest First',
}

export const CANADA_PROVINCES = [
  'Alberta', 'British Columbia', 'Manitoba', 'Maritimes', 'New Brunswick',
  'Newfoundland', 'Nova Scotia', 'Ontario', 'Quebec', 'Saskatchewan',
  'Northwest Territories', 'Nunavut', 'Yukon',
]

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

export const REGIONS = [
  'United States', 'Canada', 'Europe', 'Asia', 'Latin America', 'Africa', 'Middle East', 'Oceania',
] as const

export const REGION_COUNTRIES: Record<string, string[]> = {
  'United States': ['USA'],
  'Canada': ['Canada'],
  'Europe': [
    'UK', 'France', 'Spain', 'Italy', 'Germany', 'Switzerland', 'Austria',
    'Norway', 'Sweden', 'Finland', 'Denmark', 'Iceland', 'Netherlands', 'Belgium',
    'Portugal', 'Poland', 'Czech Republic', 'Slovakia', 'Hungary', 'Romania', 'Bulgaria',
    'Greece', 'Croatia', 'Slovenia', 'Serbia', 'Albania', 'North Macedonia', 'Montenegro',
    'Bosnia and Herzegovina', 'Kosovo', 'Ireland', 'Scotland', 'Wales', 'Georgia',
    'Armenia', 'Azerbaijan', 'Ukraine', 'Latvia', 'Lithuania', 'Estonia', 'Greenland',
    'Cyprus', 'Europe', 'Eastern Europe',
  ],
  'Asia': [
    'Japan', 'Nepal', 'China', 'India', 'Thailand', 'Mongolia', 'Kyrgyzstan', 'Tajikistan',
    'Kazakhstan', 'Vietnam', 'Cambodia', 'Laos', 'Myanmar', 'Bhutan', 'Pakistan',
    'Sri Lanka', 'Bangladesh', 'Philippines', 'Malaysia', 'Indonesia', 'Taiwan',
    'South Korea', 'Uzbekistan', 'Turkmenistan', 'Asia', 'East Asia', 'Central Asia',
  ],
  'Latin America': [
    'Mexico', 'Colombia', 'Peru', 'Brazil', 'Chile', 'Argentina', 'Bolivia', 'Ecuador',
    'Venezuela', 'Paraguay', 'Uruguay', 'Guatemala', 'Honduras', 'El Salvador',
    'Nicaragua', 'Costa Rica', 'Panama', 'Cuba', 'Dominican Republic',
    'Latin America', 'Central America',
  ],
  'Africa': [
    'South Africa', 'Kenya', 'Morocco', 'Ethiopia', 'Tanzania', 'Uganda', 'Rwanda',
    'Madagascar', 'Namibia', 'Botswana', 'Zimbabwe', 'Mozambique', 'Zambia', 'Malawi',
    'Egypt', 'Tunisia', 'Algeria', 'Senegal', 'Ghana', 'Nigeria',
    'East Africa', 'North Africa',
  ],
  'Middle East': [
    'Iran', 'Jordan', 'Israel', 'Oman', 'Turkey', 'Lebanon', 'Syria', 'Iraq',
    'Saudi Arabia', 'UAE', 'Kuwait', 'Qatar', 'Bahrain', 'Yemen', 'Middle East',
  ],
  'Oceania': [
    'New Zealand', 'Australia', 'Papua New Guinea', 'Fiji', 'Vanuatu',
  ],
}
