'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import dynamic from 'next/dynamic'
import type { Route } from '@/lib/types'
import { useFilters } from '@/hooks/useFilters'
import { useRoutes, fetchAllRoutesForMap } from '@/hooks/useRoutes'
import { useMapState } from '@/hooks/useMapState'
import Sidebar from './Sidebar'
import RouteCard from './RouteCard'

const MapView = dynamic(() => import('./MapView'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-gray-100 flex items-center justify-center">
      <div className="text-sm text-gray-400">Loading map…</div>
    </div>
  ),
})

// ── List view panel with infinite scroll ──────────────────────────
function ListViewPanel({
  routes, total, isLoading, hasMore, selectedRouteId, onHover, onClick, onLoadMore,
}: {
  routes: Route[]
  total: number
  isLoading: boolean
  hasMore: boolean
  selectedRouteId: string | null
  onHover: (id: string | null) => void
  onClick: (route: Route) => void
  onLoadMore: () => void
}) {
  const sentinelRef = useRef<HTMLDivElement>(null)
  const loadMoreRef = useRef(onLoadMore)
  loadMoreRef.current = onLoadMore

  useEffect(() => {
    if (!hasMore || isLoading) return
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) loadMoreRef.current() },
      { threshold: 0.1 },
    )
    const el = sentinelRef.current
    if (el) observer.observe(el)
    return () => observer.disconnect()
  }, [hasMore, isLoading])

  return (
    <div className="absolute inset-0 overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700">
            {total.toLocaleString()} routes
          </h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {routes.map((route) => (
            <RouteCard
              key={route.id}
              route={route}
              isSelected={route.id === selectedRouteId}
              onHover={onHover}
              onClick={onClick}
              layout="grid"
            />
          ))}
        </div>
        <div ref={sentinelRef} className="mt-8 h-10 flex items-center justify-center">
          {isLoading && <span className="text-sm text-gray-400">Loading…</span>}
        </div>
      </div>
    </div>
  )
}

// ── Main explorer ─────────────────────────────────────────────────
const CARD_W = 340
const CARD_MARGIN = 16

export default function MapExplorer() {
  const [view, setView] = useState<'map' | 'list'>('map')
  const [flyToRoute, setFlyToRoute] = useState<Route | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const contentRef = useRef<HTMLDivElement>(null)

  const { filters, updateFilter, resetFilters, toggleBikeType } = useFilters()
  const { routes, total, isLoading, hasMore, loadMore } = useRoutes(filters)
  const { selectedRouteId, hoveredRouteId, setMapReady, selectRoute, hoverRoute } = useMapState()

  const cardRef = useRef<HTMLDivElement>(null)

  const [mapRoutes, setMapRoutes] = useState<Route[]>([])
  useEffect(() => {
    fetchAllRoutesForMap(filters).then(setMapRoutes)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)])

  const selectedRoute = mapRoutes.find((r) => r.id === selectedRouteId)
    ?? routes.find((r) => r.id === selectedRouteId)
    ?? null

  // ── Draggable card state ──────────────────────────────────────────
  // null = default position (top-right corner); set after first drag
  const [cardPos, setCardPos] = useState<{ x: number; y: number } | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const dragRef = useRef<{
    startMouse: { x: number; y: number }
    startCard: { x: number; y: number }
  } | null>(null)

  // Reset drag position when card is dismissed
  const handleDeselect = useCallback(() => {
    selectRoute(null)
    setCardPos(null)
  }, [selectRoute])

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return
    e.preventDefault()
    const cardEl = cardRef.current
    if (!cardEl) return
    const rect = cardEl.getBoundingClientRect()
    dragRef.current = {
      startMouse: { x: e.clientX, y: e.clientY },
      startCard: { x: rect.left, y: rect.top },
    }
    setIsDragging(true)
  }, [])

  useEffect(() => {
    function handleMouseMove(e: MouseEvent) {
      if (!dragRef.current) return
      const dx = e.clientX - dragRef.current.startMouse.x
      const dy = e.clientY - dragRef.current.startMouse.y
      const newX = dragRef.current.startCard.x + dx
      const newY = dragRef.current.startCard.y + dy
      setCardPos({
        x: Math.max(0, Math.min(window.innerWidth - CARD_W, newX)),
        y: Math.max(0, Math.min(window.innerHeight - 60, newY)),
      })
    }
    function handleMouseUp() {
      if (!dragRef.current) return
      dragRef.current = null
      setIsDragging(false)
    }
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [])

  // Card position: use dragged coords if set, otherwise snap to top-right viewport corner
  const cardPosStyle: React.CSSProperties = cardPos
    ? { top: cardPos.y, left: cardPos.x }
    : { top: CARD_MARGIN, right: CARD_MARGIN }

  const handleRouteClick = useCallback((route: Route) => {
    selectRoute(route.id)
    setFlyToRoute(route)
    if (view === 'list') setView('map')
  }, [selectRoute, view])

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
            total={total}
            isLoading={isLoading}
            view={view}
            onViewChange={setView}
            onFilterUpdate={updateFilter}
            onToggleBikeType={toggleBikeType}
            onFilterReset={resetFilters}
          />
        </div>
      </div>

      {/* Sidebar toggle */}
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

      {/* Main content */}
      <div ref={contentRef} className="flex-1 relative overflow-hidden">
        {/* Map (always mounted) */}
        <div className={`absolute inset-0 ${view === 'map' ? 'block' : 'hidden'}`}>
          <MapView
            routes={mapRoutes}
            selectedRouteId={selectedRouteId}
            hoveredRouteId={hoveredRouteId}
            onRouteSelect={selectRoute}
            onMapReady={setMapReady}
            flyToRoute={flyToRoute}
          />
        </div>

        {/* List view */}
        {view === 'list' && (
          <ListViewPanel
            routes={routes}
            total={total}
            isLoading={isLoading}
            hasMore={hasMore}
            selectedRouteId={selectedRouteId}
            onHover={hoverRoute}
            onClick={handleRouteClick}
            onLoadMore={loadMore}
          />
        )}

        {/* Selected route card — fixed to viewport, draggable */}
        {view === 'map' && selectedRoute && (
          <div
            ref={cardRef}
            className="fixed z-20 w-[340px] rounded-xl shadow-2xl border border-gray-200 bg-white overflow-hidden select-none"
            style={cardPosStyle}
          >
            {/* Drag handle bar */}
            <div
              className={`h-8 bg-gray-50 border-b border-gray-100 flex items-center px-3 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
              onMouseDown={handleDragStart}
            >
              {/* Centered grip dots */}
              <div className="flex-1 flex items-center justify-center gap-0.5">
                <div className="w-5 h-1 rounded-full bg-gray-300" />
              </div>
              {/* Close button */}
              <button
                className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
                onMouseDown={(e) => e.stopPropagation()}
                onClick={handleDeselect}
                aria-label="Close"
              >
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
                  <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
                </svg>
              </button>
            </div>
            <RouteCard route={selectedRoute} layout="grid" />
          </div>
        )}

        {/* Empty state */}
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
