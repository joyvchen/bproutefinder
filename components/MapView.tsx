'use client'

import { useEffect, useRef, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import type { Route } from '@/lib/types'
import { routesToGeoJSON, MAP_DEFAULTS, formatDistance, formatDays, formatDifficulty } from '@/lib/map-utils'

interface MapViewProps {
  routes: Route[]
  selectedRouteId: string | null
  hoveredRouteId: string | null
  onRouteSelect: (id: string | null) => void
  onMapReady: () => void
  flyToRoute?: Route | null
}

const SOURCE_ID = 'routes'
const CLUSTER_LAYER = 'clusters'
const CLUSTER_COUNT_LAYER = 'cluster-count'
const UNCLUSTERED_LAYER = 'unclustered-point'
const TOP_PICK_LAYER = 'top-pick-star'

export default function MapView({
  routes,
  selectedRouteId,
  hoveredRouteId,
  onRouteSelect,
  onMapReady,
  flyToRoute,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const popupRef = useRef<mapboxgl.Popup | null>(null)

  // Initialize map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: MAP_DEFAULTS.style,
      center: MAP_DEFAULTS.center,
      zoom: MAP_DEFAULTS.zoom,
      attributionControl: false,
    })

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'bottom-right')
    map.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-left')

    map.on('load', () => {
      // GeoJSON source with clustering
      map.addSource(SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
        cluster: true,
        clusterMaxZoom: 10,
        clusterRadius: 50,
      })

      // Cluster circles
      map.addLayer({
        id: CLUSTER_LAYER,
        type: 'circle',
        source: SOURCE_ID,
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': [
            'step', ['get', 'point_count'],
            '#4ade80', 10,
            '#22c55e', 30,
            '#16a34a',
          ],
          'circle-radius': ['step', ['get', 'point_count'], 18, 10, 24, 30, 30],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff',
        },
      })

      // Cluster count labels
      map.addLayer({
        id: CLUSTER_COUNT_LAYER,
        type: 'symbol',
        source: SOURCE_ID,
        filter: ['has', 'point_count'],
        layout: {
          'text-field': '{point_count_abbreviated}',
          'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
          'text-size': 13,
        },
        paint: { 'text-color': '#fff' },
      })

      // Individual route points
      map.addLayer({
        id: UNCLUSTERED_LAYER,
        type: 'circle',
        source: SOURCE_ID,
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': [
            'case',
            ['==', ['get', 'id'], selectedRouteId ?? ''], '#f59e0b',
            ['get', 'is_top_pick'], '#16a34a',
            '#22c55e',
          ],
          'circle-radius': [
            'case',
            ['==', ['get', 'id'], selectedRouteId ?? ''], 10,
            8,
          ],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff',
        },
      })

      onMapReady()
    })

    // Cluster click → zoom in
    map.on('click', CLUSTER_LAYER, (e) => {
      const features = map.queryRenderedFeatures(e.point, { layers: [CLUSTER_LAYER] })
      const clusterId = features[0].properties?.cluster_id
      const source = map.getSource(SOURCE_ID) as mapboxgl.GeoJSONSource
      source.getClusterExpansionZoom(clusterId, (err, zoom) => {
        if (err) return
        const center = (features[0].geometry as GeoJSON.Point).coordinates as [number, number]
        map.flyTo({ center, zoom: zoom! + 1 })
      })
    })

    // Route point click → show popup
    map.on('click', UNCLUSTERED_LAYER, (e) => {
      const feature = e.features?.[0]
      if (!feature) return
      const props = feature.properties as {
        id: string; slug: string; name: string; state: string | null
        distance_mi: number | null; days_min: number | null; days_max: number | null
        difficulty: number | null; is_top_pick: boolean; image_url: string | null
      }
      const coords = (feature.geometry as GeoJSON.Point).coordinates as [number, number]

      onRouteSelect(props.id)

      if (popupRef.current) popupRef.current.remove()

      const img = props.image_url
        ? `<img src="${props.image_url}" alt="${props.name}" class="w-full h-28 object-cover rounded-t-lg" />`
        : ''

      const badge = props.is_top_pick
        ? '<span class="inline-flex items-center gap-1 text-xs font-semibold text-amber-700 bg-amber-100 rounded-full px-2 py-0.5">⭐ Top Pick</span>'
        : ''

      const popup = new mapboxgl.Popup({ offset: 12, maxWidth: '240px', closeButton: true })
        .setLngLat(coords)
        .setHTML(`
          <div class="font-sans text-gray-800">
            ${img}
            <div class="p-3">
              <div class="flex items-start justify-between gap-2">
                <p class="font-semibold text-sm leading-tight">${props.name}</p>
                ${badge}
              </div>
              <p class="text-xs text-gray-500 mt-1">${props.state ?? ''}</p>
              <div class="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-xs text-gray-600">
                ${props.distance_mi ? `<span>${props.distance_mi.toFixed(0)} mi</span>` : ''}
                ${props.days_min ? `<span>${formatDays(props.days_min, props.days_max)}</span>` : ''}
                ${props.difficulty ? `<span>Difficulty ${formatDifficulty(props.difficulty)}</span>` : ''}
              </div>
              <a href="/routes/${props.slug}" class="mt-3 block text-center text-xs font-semibold text-white bg-green-600 hover:bg-green-700 rounded-md py-1.5 px-3 transition-colors">
                View Details →
              </a>
            </div>
          </div>
        `)
        .addTo(map)

      popupRef.current = popup
    })

    // Cursor styles
    map.on('mouseenter', CLUSTER_LAYER, () => { map.getCanvas().style.cursor = 'pointer' })
    map.on('mouseleave', CLUSTER_LAYER, () => { map.getCanvas().style.cursor = '' })
    map.on('mouseenter', UNCLUSTERED_LAYER, () => { map.getCanvas().style.cursor = 'pointer' })
    map.on('mouseleave', UNCLUSTERED_LAYER, () => { map.getCanvas().style.cursor = '' })

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Update GeoJSON when routes change
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    const source = map.getSource(SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    if (!source) return
    source.setData(routesToGeoJSON(routes))
  }, [routes])

  // Update selected point color
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    if (!map.getLayer(UNCLUSTERED_LAYER)) return
    map.setPaintProperty(UNCLUSTERED_LAYER, 'circle-color', [
      'case',
      ['==', ['get', 'id'], selectedRouteId ?? ''], '#f59e0b',
      ['get', 'is_top_pick'], '#16a34a',
      '#22c55e',
    ])
    map.setPaintProperty(UNCLUSTERED_LAYER, 'circle-radius', [
      'case',
      ['==', ['get', 'id'], selectedRouteId ?? ''], 10,
      8,
    ])
  }, [selectedRouteId])

  // Fly to a specific route
  useEffect(() => {
    const map = mapRef.current
    if (!map || !flyToRoute?.lat || !flyToRoute?.lng) return
    map.flyTo({
      center: [flyToRoute.lng, flyToRoute.lat],
      zoom: Math.max(map.getZoom(), 8),
      duration: 800,
    })
  }, [flyToRoute])

  return <div ref={containerRef} className="w-full h-full" />
}
