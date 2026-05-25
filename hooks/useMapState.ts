'use client'

import { useState, useCallback } from 'react'

export function useMapState() {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [hoveredRouteId, setHoveredRouteId] = useState<string | null>(null)
  const [mapReady, setMapReady] = useState(false)

  const selectRoute = useCallback((id: string | null) => {
    setSelectedRouteId(id)
  }, [])

  const hoverRoute = useCallback((id: string | null) => {
    setHoveredRouteId(id)
  }, [])

  const markMapReady = useCallback(() => {
    setMapReady(true)
  }, [])

  return {
    selectedRouteId,
    hoveredRouteId,
    mapReady,
    setMapReady: markMapReady,
    selectRoute,
    hoverRoute,
  }
}
