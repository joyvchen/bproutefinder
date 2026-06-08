'use client'

import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Route } from '@/lib/types'
import { MAP_DEFAULTS } from '@/lib/map-utils'

interface MapViewProps {
  routes: Route[]
  selectedRouteId: string | null
  hoveredRouteId: string | null
  onRouteSelect: (id: string | null) => void
  onMapReady: () => void
  flyToRoute?: Route | null
  onPinPosition?: (pos: { x: number; y: number } | null) => void
  onRoutesRendered?: () => void
}

const SOURCE_ID = 'routes'
const POINTS_LAYER = 'route-points'
const LINES_SOURCE = 'route-lines'
const LINES_LAYER = 'route-lines-layer'

const CACHE_KEY = 'rwgps_traces_v1'
const CACHE_MAX_PTS = 200

function readCachedTraces(): Map<string, [number, number][]> {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return new Map()
    return new Map(Object.entries(JSON.parse(raw) as Record<string, [number, number][]>))
  } catch { return new Map() }
}

function setCachedTrace(id: string, coords: [number, number][]) {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    const obj: Record<string, [number, number][]> = raw ? JSON.parse(raw) : {}
    const step = Math.max(1, Math.ceil(coords.length / CACHE_MAX_PTS))
    obj[id] = coords.filter((_, i) => i % step === 0)
    localStorage.setItem(CACHE_KEY, JSON.stringify(obj))
  } catch {}
}

function buildPointsGeoJSON(
  routes: Route[],
  startCoords: Map<string, [number, number]>,
) {
  const features = []
  for (const r of routes) {
    const override = startCoords.get(r.id)
    const lng = override?.[0] ?? r.lng
    const lat = override?.[1] ?? r.lat
    if (lng == null || lat == null) continue
    features.push({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [lng, lat] },
      properties: { id: r.id, name: r.name, is_top_pick: r.is_top_pick ?? false },
    })
  }
  return { type: 'FeatureCollection' as const, features }
}

function buildLinesGeoJSON(linesMap: Map<string, [number, number][]>, activeIds?: Set<string>) {
  return {
    type: 'FeatureCollection' as const,
    features: Array.from(linesMap.entries())
      .filter(([id]) => !activeIds || activeIds.has(id))
      .map(([id, coords]) => ({
        type: 'Feature' as const,
        geometry: { type: 'LineString' as const, coordinates: coords },
        properties: { id },
      })),
  }
}

function loadPinImage(color: string): Promise<HTMLImageElement> {
  return new Promise((resolve) => {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 32 40">
      <path d="M16 1C8.82 1 3 6.82 3 14c0 9.38 13 25 13 25S29 23.38 29 14C29 6.82 23.18 1 16 1z"
            fill="${color}" stroke="white" stroke-width="1.5"/>
      <circle cx="16" cy="14" r="5" fill="white" opacity="0.95"/>
    </svg>`
    const img = new Image(64, 80)
    img.onload = () => resolve(img)
    img.src = 'data:image/svg+xml,' + encodeURIComponent(svg)
  })
}

export default function MapView({
  routes,
  selectedRouteId,
  hoveredRouteId,
  onRouteSelect,
  onMapReady,
  flyToRoute,
  onPinPosition,
  onRoutesRendered,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const routesRef = useRef<Route[]>(routes)
  routesRef.current = routes
  const onRouteSelectRef = useRef(onRouteSelect)
  onRouteSelectRef.current = onRouteSelect
  const onPinPositionRef = useRef(onPinPosition)
  onPinPositionRef.current = onPinPosition
  const onRoutesRenderedRef = useRef(onRoutesRendered)
  onRoutesRenderedRef.current = onRoutesRendered
  const selectedRouteIdRef = useRef(selectedRouteId)
  selectedRouteIdRef.current = selectedRouteId
  const routeLinesRef = useRef<Map<string, [number, number][]>>(new Map())
  const routeStartCoordsRef = useRef<Map<string, [number, number]>>(new Map())
  const [mapReady, setMapReady] = useState(false)

  // Initialize map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    // Seed from localStorage before map creation so first render has traces
    const cached = readCachedTraces()
    cached.forEach((coords, id) => {
      if (!coords.length) return
      const [lng, lat] = coords[0]
      if (typeof lng !== 'number' || !isFinite(lng) || typeof lat !== 'number' || !isFinite(lat)) return
      routeLinesRef.current.set(id, coords)
      routeStartCoordsRef.current.set(id, coords[0])
    })

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_DEFAULTS.style,
      center: MAP_DEFAULTS.center,
      zoom: MAP_DEFAULTS.zoom,
      attributionControl: false,
    })

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left')

    map.on('load', async () => {
      const [pinGreen, pinAmber, pinDark] = await Promise.all([
        loadPinImage('#22c55e'),
        loadPinImage('#f59e0b'),
        loadPinImage('#16a34a'),
      ])
      map.addImage('pin-green', pinGreen, { pixelRatio: 2 })
      map.addImage('pin-amber', pinAmber, { pixelRatio: 2 })
      map.addImage('pin-dark', pinDark, { pixelRatio: 2 })

      // Lines source — pre-seeded from cache, filtered to current routes
      map.addSource(LINES_SOURCE, {
        type: 'geojson',
        data: buildLinesGeoJSON(routeLinesRef.current, new Set(routesRef.current.map((r) => r.id))),
      })
      map.addLayer({
        id: LINES_LAYER,
        type: 'line',
        source: LINES_SOURCE,
        paint: {
          'line-color': '#22c55e',
          'line-width': 1.5,
          'line-opacity': 0.5,
        },
      })

      // Pin markers — symbol layer
      map.addSource(SOURCE_ID, {
        type: 'geojson',
        data: buildPointsGeoJSON(routesRef.current, routeStartCoordsRef.current),
      })
      map.addLayer({
        id: POINTS_LAYER,
        type: 'symbol',
        source: SOURCE_ID,
        layout: {
          'icon-image': ['case', ['get', 'is_top_pick'], 'pin-dark', 'pin-green'],
          'icon-anchor': 'bottom',
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
          'icon-size': 1,
        },
      })

      setMapReady(true)
      onMapReady()
    })

    // Emit updated pin screen position on every map move (covers fly animation too)
    map.on('move', () => {
      const selId = selectedRouteIdRef.current
      if (!selId) return
      const route = routesRef.current.find((r) => r.id === selId)
      const start = routeStartCoordsRef.current.get(selId)
      const lng = start?.[0] ?? route?.lng
      const lat = start?.[1] ?? route?.lat
      if (lng == null || lat == null) return
      const pt = map.project([lng, lat])
      onPinPositionRef.current?.({ x: pt.x, y: pt.y })
    })

    // Unified click: select pin or deselect on empty area
    map.on('click', (e) => {
      const features = map.queryRenderedFeatures(e.point, { layers: [POINTS_LAYER] })
      if (features.length > 0) {
        const id = (features[0].properties as { id: string }).id
        onRouteSelectRef.current(id)
        selectedRouteIdRef.current = id  // sync ref immediately so move handler sees it
        // Emit pin position right away — don't wait for move event or effect
        const route = routesRef.current.find((r) => r.id === id)
        const start = routeStartCoordsRef.current.get(id)
        const pinLng = start?.[0] ?? route?.lng
        const pinLat = start?.[1] ?? route?.lat
        if (pinLng != null && pinLat != null) {
          const pt = map.project([pinLng, pinLat])
          onPinPositionRef.current?.({ x: pt.x, y: pt.y })
        }
        // Fly to show full route trace, or zoom to pin if no trace loaded yet
        const coords = routeLinesRef.current.get(id)
        if (coords && coords.length > 1) {
          const lngs = coords.map((c) => c[0])
          const lats = coords.map((c) => c[1])
          map.fitBounds(
            [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
            { padding: { top: 80, bottom: 80, left: 80, right: 400 }, maxZoom: 12, duration: 900 },
          )
        } else if (route?.lat && route?.lng) {
          map.flyTo({ center: [route.lng, route.lat], zoom: Math.max(map.getZoom(), 9), duration: 800 })
        }
      } else {
        onRouteSelectRef.current(null)
        onPinPositionRef.current?.(null)
      }
    })

    map.on('mouseenter', POINTS_LAYER, () => { map.getCanvas().style.cursor = 'pointer' })
    map.on('mouseleave', POINTS_LAYER, () => { map.getCanvas().style.cursor = '' })

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Update point and line GeoJSON when routes change (or map becomes ready)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    const activeIds = new Set(routes.map((r) => r.id))
    const pointsSource = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined
    if (pointsSource) pointsSource.setData(buildPointsGeoJSON(routes, routeStartCoordsRef.current))
    const linesSource = map.getSource(LINES_SOURCE) as maplibregl.GeoJSONSource | undefined
    if (linesSource) linesSource.setData(buildLinesGeoJSON(routeLinesRef.current, activeIds))
    // Wait for MapLibre to finish rendering the new pins — 'idle' fires after all
    // pending source processing and draw calls are complete.
    const handleIdle = () => onRoutesRenderedRef.current?.()
    map.once('idle', handleIdle)
    return () => { map.off('idle', handleIdle) }
  }, [routes, mapReady])

  // Load RWGPS traces progressively — skip already-cached, 5 concurrent, 150 ms between batches
  useEffect(() => {
    if (!mapReady) return
    const map = mapRef.current
    if (!map) return

    const pending = routes.filter((r) => r.rwgps_route_id && !routeLinesRef.current.has(r.id))
    if (!pending.length) return

    let cancelled = false

    const loadOne = async (route: Route) => {
      if (cancelled || !route.rwgps_route_id) return
      try {
        const res = await fetch(`/api/rwgps/${route.rwgps_route_id}`)
        if (!res.ok || cancelled) return
        const data = await res.json()
        const pts = data.route?.track_points as Array<{ x: number; y: number }> | undefined
        if (!pts?.length || cancelled) return
        const startX = pts[0].x
        const startY = pts[0].y
        if (typeof startX !== 'number' || !isFinite(startX) || typeof startY !== 'number' || !isFinite(startY)) return
        const step = Math.max(1, Math.ceil(pts.length / 2000))
        const coords = pts.filter((_, i) => i % step === 0).map((p) => [p.x, p.y] as [number, number])
        routeLinesRef.current.set(route.id, coords)
        routeStartCoordsRef.current.set(route.id, [startX, startY])
        setCachedTrace(route.id, coords)
        if (cancelled) return
        const activeIds = new Set(routesRef.current.map((r) => r.id))
        const linesSource = map.getSource(LINES_SOURCE) as maplibregl.GeoJSONSource | undefined
        if (linesSource) linesSource.setData(buildLinesGeoJSON(routeLinesRef.current, activeIds))
        const pointsSource = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined
        if (pointsSource) pointsSource.setData(buildPointsGeoJSON(routesRef.current, routeStartCoordsRef.current))
      } catch {}
    }

    ;(async () => {
      for (let i = 0; i < pending.length; i += 5) {
        if (cancelled) break
        await Promise.all(pending.slice(i, i + 5).map(loadOne))
        if (!cancelled && i + 5 < pending.length) {
          await new Promise((r) => setTimeout(r, 150))
        }
      }
    })()

    return () => { cancelled = true }
  }, [routes, mapReady])

  // Highlight selected route + emit initial pin position for external selections
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return

    const sel = selectedRouteId ?? ''

    if (map.getLayer(POINTS_LAYER)) {
      map.setLayoutProperty(POINTS_LAYER, 'icon-image', [
        'case',
        ['==', ['get', 'id'], sel], 'pin-amber',
        ['get', 'is_top_pick'], 'pin-dark',
        'pin-green',
      ])
      map.setLayoutProperty(POINTS_LAYER, 'icon-size', [
        'case', ['==', ['get', 'id'], sel], 1.3, 1,
      ])
    }

    if (map.getLayer(LINES_LAYER)) {
      map.setPaintProperty(LINES_LAYER, 'line-color', [
        'case', ['==', ['get', 'id'], sel], '#f59e0b', '#22c55e',
      ])
      map.setPaintProperty(LINES_LAYER, 'line-width', [
        'case', ['==', ['get', 'id'], sel], 3.5, 1.5,
      ])
      map.setPaintProperty(LINES_LAYER, 'line-opacity', [
        'case', ['==', ['get', 'id'], sel], 1, 0.5,
      ])
    }

    // Emit initial position (e.g. route selected from list view before map moves)
    if (selectedRouteId) {
      const route = routesRef.current.find((r) => r.id === selectedRouteId)
      const start = routeStartCoordsRef.current.get(selectedRouteId)
      const lng = start?.[0] ?? route?.lng
      const lat = start?.[1] ?? route?.lat
      if (lng != null && lat != null) {
        const pt = map.project([lng, lat])
        onPinPositionRef.current?.({ x: pt.x, y: pt.y })
      }
    } else {
      onPinPositionRef.current?.(null)
    }
  }, [selectedRouteId])

  // Fly to selected route
  useEffect(() => {
    const map = mapRef.current
    if (!map || !flyToRoute?.lat || !flyToRoute?.lng) return
    map.flyTo({
      center: [flyToRoute.lng, flyToRoute.lat],
      zoom: Math.max(map.getZoom(), 8),
      duration: 800,
    })
  }, [flyToRoute])

  function handleResetView() {
    mapRef.current?.flyTo({
      center: MAP_DEFAULTS.center,
      zoom: MAP_DEFAULTS.zoom,
      duration: 900,
    })
  }

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      <button
        onClick={handleResetView}
        className="absolute top-3 left-3 z-10 bg-white border border-gray-200 rounded-lg shadow-sm p-2 hover:bg-gray-50 transition-colors"
        title="Zoom to overview"
        aria-label="Zoom to overview"
      >
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-gray-600">
          <circle cx="10" cy="10" r="8" />
          <path d="M2 10h16M10 2a12 12 0 010 16M10 2a12 12 0 000 16" strokeLinecap="round"/>
        </svg>
      </button>
    </div>
  )
}
