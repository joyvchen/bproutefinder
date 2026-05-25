'use client'

import { useCallback, useEffect, useRef } from 'react'
import type { Route, FilterState } from '@/lib/types'
import FilterPanel from './FilterPanel'
import RouteCard from './RouteCard'
import ViewToggle from './ViewToggle'

interface SidebarProps {
  filters: FilterState
  routes: Route[]
  total: number
  isLoading: boolean
  hasMore: boolean
  selectedRouteId: string | null
  view: 'map' | 'list'
  onViewChange: (v: 'map' | 'list') => void
  onFilterUpdate: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
  onToggleBikeType: (type: string) => void
  onFilterReset: () => void
  onRouteHover: (id: string | null) => void
  onRouteClick: (route: Route) => void
  onLoadMore: () => void
}

export default function Sidebar({
  filters,
  routes,
  total,
  isLoading,
  hasMore,
  selectedRouteId,
  view,
  onViewChange,
  onFilterUpdate,
  onToggleBikeType,
  onFilterReset,
  onRouteHover,
  onRouteClick,
  onLoadMore,
}: SidebarProps) {
  const sentinelRef = useRef<HTMLDivElement>(null)

  // Infinite scroll sentinel
  useEffect(() => {
    if (!sentinelRef.current || !hasMore) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isLoading) onLoadMore()
      },
      { threshold: 0.1 }
    )
    observer.observe(sentinelRef.current)
    return () => observer.disconnect()
  }, [hasMore, isLoading, onLoadMore])

  return (
    <div className="flex flex-col h-full overflow-hidden bg-white">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-gray-100 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-base font-bold text-gray-900">Route Finder</h1>
            <p className="text-xs text-gray-500">
              {isLoading ? 'Loading…' : `${total.toLocaleString()} routes`}
            </p>
          </div>
          <ViewToggle view={view} onChange={onViewChange} />
        </div>

        {/* Search */}
        <div className="relative">
          <svg
            className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="search"
            placeholder="Search routes…"
            value={filters.q}
            onChange={(e) => onFilterUpdate('q', e.target.value)}
            className="w-full rounded-lg border border-gray-200 pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>
      </div>

      {/* Filters */}
      <div className="flex-shrink-0 overflow-y-auto border-b border-gray-200" style={{ maxHeight: '45%' }}>
        <FilterPanel
          filters={filters}
          onUpdate={onFilterUpdate}
          onToggleBikeType={onToggleBikeType}
          onReset={onFilterReset}
        />
      </div>

      {/* Route List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && routes.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-sm text-gray-400">
            Loading routes…
          </div>
        ) : routes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-sm text-gray-400 text-center px-4">
            <p className="font-medium text-gray-600">No routes found</p>
            <p className="text-xs mt-1">Try adjusting your filters</p>
          </div>
        ) : (
          <div className="p-2 flex flex-col gap-1">
            {routes.map((route) => (
              <RouteCard
                key={route.id}
                route={route}
                isSelected={route.id === selectedRouteId}
                onHover={onRouteHover}
                onClick={onRouteClick}
                layout="sidebar"
              />
            ))}
            {hasMore && (
              <div ref={sentinelRef} className="py-4 flex justify-center">
                {isLoading ? (
                  <span className="text-xs text-gray-400">Loading more…</span>
                ) : (
                  <button
                    onClick={onLoadMore}
                    className="text-xs text-green-600 hover:text-green-700 font-medium"
                  >
                    Load more
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
