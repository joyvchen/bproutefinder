'use client'

import type { FilterState } from '@/lib/types'
import FilterPanel from './FilterPanel'
import ViewToggle from './ViewToggle'

interface SidebarProps {
  filters: FilterState
  total: number
  isLoading: boolean
  view: 'map' | 'list'
  onViewChange: (v: 'map' | 'list') => void
  onFilterUpdate: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
  onToggleBikeType: (type: string) => void
  onFilterReset: () => void
}

export default function Sidebar({
  filters,
  total,
  isLoading,
  view,
  onViewChange,
  onFilterUpdate,
  onToggleBikeType,
  onFilterReset,
}: SidebarProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden bg-white">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-gray-100 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-base font-bold text-gray-900 leading-tight">
              Bikepacking.com<br />Route Finder
            </h1>
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
      <div className="flex-1 overflow-y-auto">
        <FilterPanel
          filters={filters}
          onUpdate={onFilterUpdate}
          onToggleBikeType={onToggleBikeType}
          onReset={onFilterReset}
        />
      </div>
    </div>
  )
}
