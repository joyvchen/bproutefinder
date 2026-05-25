'use client'

import { useState } from 'react'
import type { FilterState, SortOption } from '@/lib/types'
import { SORT_LABELS, US_STATES, INTERNATIONAL_REGIONS, activeFilterCount } from '@/lib/filters'

interface FilterPanelProps {
  filters: FilterState
  onUpdate: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
  onToggleBikeType: (type: string) => void
  onReset: () => void
}

const BIKE_TYPES = ['gravel', 'hardtail', 'full-sus', 'road', 'touring', 'fat-bike']
const BIKE_TYPE_LABELS: Record<string, string> = {
  gravel: 'Gravel',
  hardtail: 'Hardtail MTB',
  'full-sus': 'Full Suspension',
  road: 'Road',
  touring: 'Touring',
  'fat-bike': 'Fat Bike',
}

const ALL_LOCATIONS = [...US_STATES, ...INTERNATIONAL_REGIONS]

export default function FilterPanel({
  filters,
  onUpdate,
  onToggleBikeType,
  onReset,
}: FilterPanelProps) {
  const [openSections, setOpenSections] = useState<Set<string>>(
    new Set(['location', 'bike', 'stats'])
  )
  const count = activeFilterCount(filters)

  const toggle = (section: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev)
      next.has(section) ? next.delete(section) : next.add(section)
      return next
    })
  }

  return (
    <div className="flex flex-col gap-0 text-sm">
      {/* Sort */}
      <div className="px-4 py-3 border-b border-gray-100">
        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
          Sort By
        </label>
        <select
          value={filters.sort}
          onChange={(e) => onUpdate('sort', e.target.value as SortOption)}
          className="w-full rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          {Object.entries(SORT_LABELS).map(([val, label]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>
      </div>

      {/* Top Picks toggle */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <label className="text-sm font-medium text-gray-800 cursor-pointer" htmlFor="top-pick-toggle">
          Top Picks only ⭐
        </label>
        <button
          id="top-pick-toggle"
          role="switch"
          aria-checked={filters.top_pick_only}
          onClick={() => onUpdate('top_pick_only', !filters.top_pick_only)}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
            filters.top_pick_only ? 'bg-green-600' : 'bg-gray-300'
          }`}
        >
          <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
            filters.top_pick_only ? 'translate-x-4' : 'translate-x-0.5'
          }`} />
        </button>
      </div>

      {/* Location */}
      <Section label="Location" id="location" open={openSections.has('location')} onToggle={toggle}>
        <select
          value={filters.state}
          onChange={(e) => onUpdate('state', e.target.value)}
          className="w-full rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          <option value="">All locations</option>
          <optgroup label="US States">
            {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </optgroup>
          <optgroup label="International">
            {INTERNATIONAL_REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </optgroup>
        </select>
      </Section>

      {/* Bike Type */}
      <Section label="Bike Type" id="bike" open={openSections.has('bike')} onToggle={toggle}>
        <div className="flex flex-wrap gap-1.5">
          {BIKE_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => onToggleBikeType(type)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                filters.bike_type.includes(type)
                  ? 'bg-green-600 text-white border-green-600'
                  : 'bg-white text-gray-700 border-gray-200 hover:border-green-400'
              }`}
            >
              {BIKE_TYPE_LABELS[type]}
            </button>
          ))}
        </div>
      </Section>

      {/* Stats */}
      <Section label="Route Stats" id="stats" open={openSections.has('stats')} onToggle={toggle}>
        <div className="flex flex-col gap-3">
          {/* Difficulty 1–10 */}
          <RangeField
            label="Difficulty (1–10)"
            minVal={filters.difficulty_min}
            maxVal={filters.difficulty_max}
            min={1} max={10} step={0.5}
            onMin={(v) => onUpdate('difficulty_min', v)}
            onMax={(v) => onUpdate('difficulty_max', v)}
            format={(v) => v?.toFixed(1) ?? ''}
          />

          {/* Days */}
          <RangeField
            label="Days"
            minVal={filters.days_min}
            maxVal={filters.days_max}
            min={1} max={30} step={1}
            onMin={(v) => onUpdate('days_min', v)}
            onMax={(v) => onUpdate('days_max', v)}
            format={(v) => v != null ? `${v}d` : ''}
          />

          {/* Distance */}
          <RangeField
            label="Distance (mi)"
            minVal={filters.distance_min}
            maxVal={filters.distance_max}
            min={0} max={1000} step={10}
            onMin={(v) => onUpdate('distance_min', v)}
            onMax={(v) => onUpdate('distance_max', v)}
            format={(v) => v != null ? `${v}` : ''}
          />

          {/* Ascent */}
          <MaxField
            label="Max Ascent (ft)"
            value={filters.elevation_max}
            min={0} max={50000} step={500}
            onChange={(v) => onUpdate('elevation_max', v)}
            format={(v) => v != null ? `${v.toLocaleString()} ft` : 'Any'}
          />

          {/* Unpaved % */}
          <MinField
            label="Min Unpaved %"
            value={filters.unpaved_min}
            min={0} max={100} step={5}
            onChange={(v) => onUpdate('unpaved_min', v)}
            format={(v) => v != null ? `${v}%` : 'Any'}
          />

          {/* Singletrack % */}
          <MinField
            label="Min Singletrack %"
            value={filters.singletrack_min}
            min={0} max={100} step={5}
            onChange={(v) => onUpdate('singletrack_min', v)}
            format={(v) => v != null ? `${v}%` : 'Any'}
          />
        </div>
      </Section>

      {/* Tire Width */}
      <Section label="Tire Width (mm)" id="tire" open={openSections.has('tire')} onToggle={toggle}>
        <RangeField
          label=""
          minVal={filters.tire_width_min}
          maxVal={filters.tire_width_max}
          min={25} max={120} step={5}
          onMin={(v) => onUpdate('tire_width_min', v)}
          onMax={(v) => onUpdate('tire_width_max', v)}
          format={(v) => v != null ? `${v}mm` : ''}
        />
      </Section>

      {/* Clear */}
      {count > 0 && (
        <div className="px-4 py-3">
          <button
            onClick={onReset}
            className="w-full text-sm font-medium text-red-600 hover:text-red-700 py-1.5 rounded-md border border-red-200 hover:bg-red-50 transition-colors"
          >
            Clear all filters ({count})
          </button>
        </div>
      )}
    </div>
  )
}

function Section({
  label, id, open, onToggle, children,
}: {
  label: string
  id: string
  open: boolean
  onToggle: (id: string) => void
  children: React.ReactNode
}) {
  return (
    <div className="border-b border-gray-100">
      <button
        onClick={() => onToggle(id)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="px-4 pb-3">{children}</div>}
    </div>
  )
}

function RangeField({
  label, minVal, maxVal, min, max, step, onMin, onMax, format,
}: {
  label: string
  minVal: number | null
  maxVal: number | null
  min: number
  max: number
  step: number
  onMin: (v: number | null) => void
  onMax: (v: number | null) => void
  format: (v: number | null) => string
}) {
  return (
    <div>
      {label && (
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>{label}</span>
          <span className="text-gray-700">
            {minVal != null || maxVal != null
              ? `${format(minVal) || min} – ${format(maxVal) || max}`
              : 'Any'}
          </span>
        </div>
      )}
      <div className="flex gap-2 items-center">
        <NumberInput value={minVal} min={min} max={maxVal ?? max} step={step} placeholder={`${min}`}
          onChange={onMin} />
        <span className="text-gray-400 text-xs">–</span>
        <NumberInput value={maxVal} min={minVal ?? min} max={max} step={step} placeholder={`${max}`}
          onChange={onMax} />
      </div>
    </div>
  )
}

function MaxField({
  label, value, min, max, step, onChange, format,
}: {
  label: string
  value: number | null
  min: number
  max: number
  step: number
  onChange: (v: number | null) => void
  format: (v: number | null) => string
}) {
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span className="text-gray-700">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value ?? max}
        onChange={(e) => {
          const v = parseInt(e.target.value)
          onChange(v >= max ? null : v)
        }}
        className="w-full accent-green-600"
      />
    </div>
  )
}

function MinField({
  label, value, min, max, step, onChange, format,
}: {
  label: string
  value: number | null
  min: number
  max: number
  step: number
  onChange: (v: number | null) => void
  format: (v: number | null) => string
}) {
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span className="text-gray-700">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value ?? min}
        onChange={(e) => {
          const v = parseInt(e.target.value)
          onChange(v <= min ? null : v)
        }}
        className="w-full accent-green-600"
      />
    </div>
  )
}

function NumberInput({
  value, min, max, step, placeholder, onChange,
}: {
  value: number | null
  min: number
  max: number
  step: number
  placeholder: string
  onChange: (v: number | null) => void
}) {
  return (
    <input
      type="number"
      min={min} max={max} step={step}
      placeholder={placeholder}
      value={value ?? ''}
      onChange={(e) => {
        const v = e.target.value === '' ? null : parseFloat(e.target.value)
        onChange(v)
      }}
      className="w-full rounded border border-gray-200 px-2 py-1 text-xs text-gray-800 focus:outline-none focus:ring-1 focus:ring-green-500"
    />
  )
}
