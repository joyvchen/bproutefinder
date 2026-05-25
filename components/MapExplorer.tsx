'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import type { Route } from '@/lib/types'
import { useFilters } from '@/hooks/useFilters'
import { useRoutes } from '@/hooks/useRoutes'
import { useMapState } from '@/hooks/useMapState'
import Sidebar from './Sidebar'
import RouteCard from './RouteCard'

// Dynamically import MapView to avoid SSR (Mapbox needs window)
const MapView = dynamic(() => import('./MapView'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-gray-100 flex items-center justify-center">
      <div className="text-sm text-gray-400">Loading map…</div>
    </div>
  ),
})

export default function MapExplorer() {
  const [view, setView] = useState<'map' | 'list'>('map')
  const [flyToRoute, setFlyToRoute] = useState<Route | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const { filters, updateFilter, resetFilters, toggleBikeType } = useFilters()
  const { routes, total, isLoading, hasMore, loadMore } = useRoutes(filters)
  const { selectedRouteId, hoveredRouteId, setMapReady, selectRoute, hoverRoute } = useMapState()

  const handleRouteClick = useCallback((route: Route) => {
    selectRoute(route.id)
    setFlyToRoute(route)
    if (view === 'list') setView('map')
  }, [selectRoute, view])

  const handleRouteHover = useCallback((id: string | null) => {
    hoverRoute(id)
    if (id) {
      const route = routes.find((r) => r.id === id)
      if (route) setFlyToRoute(null) // Don't fly on hover, just highlight
    }
  }, [hoverRoute, routes])

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white">
      {/* Sidebar */}
      <div
        className={`flex-shrink-0 border-r border-gray-200 transition-all duration-300 overflow-hidden ${
          sidebarOpen ? 'w-96' : 'w-0'
        }`}
      >
        <div className="w-96 h-full">
          <Sidebar
            filters={filters}
            routes={routes}
            total={total}
            isLoading={isLoading}
            hasMore={hasMore}
            selectedRouteId={selectedRouteId}
            view={view}
            onViewChange={setView}
            onFilterUpdate={updateFilter}
            onToggleBikeType={toggleBikeType}
            onFilterReset={resetFilters}
            onRouteHover={handleRouteHover}
            onRouteClick={handleRouteClick}
            onLoadMore={loadMore}
          />
        </div>
      </div>

      {/* Sidebar toggle button */}
      <button
        onClick={() => setSidebarOpen((o) => !o)}
        className="absolute left-0 top-1/2 -translate-y-1/2 z-20 bg-white border border-gray-200 rounded-r-lg shadow-sm p-1.5 hover:bg-gray-50 transition-all"
        style={{ left: sidebarOpen ? '384px' : '0' }}
        aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${sidebarOpen ? '' : 'rotate-180'}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Main content: Map or List */}
      <div className="flex-1 relative overflow-hidden">
        {/* Map (always mounted to preserve state) */}
        <div className={`absolute inset-0 ${view === 'map' ? 'block' : 'hidden'}`}>
          <MapView
            routes={routes}
            selectedRouteId={selectedRouteId}
            hoveredRouteId={hoveredRouteId}
            onRouteSelect={selectRoute}
            onMapReady={setMapReady}
            flyToRoute={flyToRoute}
          />
        </div>

        {/* List view */}
        {view === 'list' && (
          <div className="absolute inset-0 overflow-y-auto bg-gray-50 p-6">
            <div className="max-w-6xl mx-auto">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-gray-700">
                  {total.toLocaleString()} routes
                </h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {routes.map((route) => (
                  <RouteCard
                    key={route.id}
                    route={route}
                    isSelected={route.id === selectedRouteId}
                    onHover={hoverRoute}
                    onClick={handleRouteClick}
                    layout="grid"
                  />
                ))}
              </div>
              {hasMore && (
                <div className="mt-8 flex justify-center">
                  <button
                    onClick={loadMore}
                    disabled={isLoading}
                    className="px-6 py-2 rounded-lg bg-green-600 text-white text-sm font-semibold hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {isLoading ? 'Loading…' : 'Load more routes'}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Empty state overlay on map */}
        {view === 'map' && !isLoading && routes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="bg-white rounded-xl shadow-lg px-6 py-4 text-center">
              <p className="font-semibold text-gray-700">No routes match your filters</p>
              <p className="text-sm text-gray-500 mt-1">Try adjusting the filters in the sidebar</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
