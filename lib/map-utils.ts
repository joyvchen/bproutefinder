import type { Route, RouteGeoJSON, RouteFeature } from './types'

export function routesToGeoJSON(routes: Route[]): RouteGeoJSON {
  return {
    type: 'FeatureCollection',
    features: routes
      .filter((r) => r.lat != null && r.lng != null)
      .map((r) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [r.lng!, r.lat!],
        },
        properties: {
          id: r.id,
          slug: r.slug,
          name: r.name,
          state: r.state,
          distance_mi: r.distance_mi,
          days_min: r.days_min,
          days_max: r.days_max,
          difficulty: r.difficulty,
          is_top_pick: r.is_top_pick,
          image_url: r.image_url,
        },
      })),
  }
}

export function formatDays(min: number | null, max: number | null): string {
  if (!min && !max) return '—'
  if (min === max || !max) return `${min} day${min === 1 ? '' : 's'}`
  return `${min}–${max} days`
}

export function formatDistance(mi: number | null, km: number | null): string {
  if (!mi && !km) return '—'
  if (mi) return `${mi.toFixed(0)} mi`
  return `${km!.toFixed(0)} km`
}

export function formatElevation(ft: number | null): string {
  if (!ft) return '—'
  return `${ft.toLocaleString()} ft`
}

export function formatDifficulty(d: number | null): string {
  if (d == null) return '—'
  return `${d}/10`
}

export function formatPct(pct: number | null, label: string): string {
  if (pct == null) return '—'
  return `${pct}% ${label}`
}

export function formatTireWidth(min: number | null, max: number | null): string {
  if (!min && !max) return '—'
  if (min && max && min !== max) return `${min}–${max}mm`
  return `${min ?? max}mm`
}

export function formatBikeType(types: string[] | null): string {
  if (!types || types.length === 0) return '—'
  return types.map(capitalize).join(', ')
}

function capitalize(s: string): string {
  return s.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export const MAP_DEFAULTS = {
  center: [-98.5795, 39.8283] as [number, number], // continental US center
  zoom: 4,
  style: 'mapbox://styles/mapbox/outdoors-v12',
}
