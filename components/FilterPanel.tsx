'use client'

import { useState, useEffect, useRef } from 'react'
import type { FilterState, SortOption } from '@/lib/types'
import { SORT_LABELS, US_STATES, CANADA_PROVINCES, REGIONS, activeFilterCount } from '@/lib/filters'

interface FilterPanelProps {
  filters: FilterState
  onUpdate: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
  onToggleBikeType: (type: string) => void
  onReset: () => void
}

const BIKE_TYPES = ['gravel', 'hardtail', 'touring', 'fat-bike']
const BIKE_TYPE_LABELS: Record<string, string> = {
  gravel: 'Gravel/All-Road',
  hardtail: 'Singletrack/MTB',
  touring: 'Dirt-Road Touring',
  'fat-bike': 'Fat Bike',
}

export default function FilterPanel({
  filters,
  onUpdate,
  onToggleBikeType,
  onReset,
}: FilterPanelProps) {
  const [openSections, setOpenSections] = useState<Set<string>>(
    new Set(['location', 'bike', 'difficulty', 'stats', 'tire', 'season'])
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

      {/* Recommended Routes toggle */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <label className="text-sm font-medium text-gray-800 cursor-pointer" htmlFor="top-pick-toggle">
          Recommended Routes only ⭐
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
        <LocationFilter filters={filters} onUpdate={onUpdate} />
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

      {/* Difficulty */}
      <Section label="Difficulty" id="difficulty" open={openSections.has('difficulty')} onToggle={toggle}>
        <div className="flex flex-col gap-4">
          <DualRangeSlider
            label="Overall (1–10)"
            minVal={filters.difficulty_min} maxVal={filters.difficulty_max}
            min={1} max={10} step={0.5}
            onMin={(v) => onUpdate('difficulty_min', v)}
            onMax={(v) => onUpdate('difficulty_max', v)}
            format={(v) => `${v.toFixed(1)}`}
          />
          <details className="group">
            <summary className="flex items-center justify-between cursor-pointer select-none list-none py-0.5">
              <span className="text-xs text-gray-400 font-medium">Sub-ratings ▾</span>
              <svg className="w-3 h-3 text-gray-400 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </summary>
            <div className="flex flex-col gap-4 mt-3 pt-2 border-t border-gray-100">
              <DualRangeSlider
                label="Climbing Scale (1–10)"
                minVal={filters.climbing_scale_min} maxVal={filters.climbing_scale_max}
                min={1} max={10} step={0.5}
                onMin={(v) => onUpdate('climbing_scale_min', v)}
                onMax={(v) => onUpdate('climbing_scale_max', v)}
                format={(v) => `${v.toFixed(1)}`}
              />
              <DualRangeSlider
                label="Technical Difficulty (1–10)"
                minVal={filters.technical_difficulty_min} maxVal={filters.technical_difficulty_max}
                min={1} max={10} step={0.5}
                onMin={(v) => onUpdate('technical_difficulty_min', v)}
                onMax={(v) => onUpdate('technical_difficulty_max', v)}
                format={(v) => `${v.toFixed(1)}`}
              />
              <DualRangeSlider
                label="Physical Demand (1–10)"
                minVal={filters.physical_demand_min} maxVal={filters.physical_demand_max}
                min={1} max={10} step={0.5}
                onMin={(v) => onUpdate('physical_demand_min', v)}
                onMax={(v) => onUpdate('physical_demand_max', v)}
                format={(v) => `${v.toFixed(1)}`}
              />
              <DualRangeSlider
                label="Resupply & Logistics (1–10)"
                minVal={filters.resupply_logistics_min} maxVal={filters.resupply_logistics_max}
                min={1} max={10} step={0.5}
                onMin={(v) => onUpdate('resupply_logistics_min', v)}
                onMax={(v) => onUpdate('resupply_logistics_max', v)}
                format={(v) => `${v.toFixed(1)}`}
              />
            </div>
          </details>
        </div>
      </Section>

      {/* Stats */}
      <Section label="Route Stats" id="stats" open={openSections.has('stats')} onToggle={toggle}>
        <div className="flex flex-col gap-4">
          <DualRangeSlider
            label="Days"
            minVal={filters.days_min} maxVal={filters.days_max}
            min={1} max={150} step={1} scale="sqrt"
            onMin={(v) => onUpdate('days_min', v)}
            onMax={(v) => onUpdate('days_max', v)}
            format={(v) => `${v}d`}
          />
          <DualRangeSlider
            label="Distance (mi)"
            minVal={filters.distance_min} maxVal={filters.distance_max}
            min={0} max={6000} step={10}
            scale={{ pivot: 1500, pivotPct: 0.85 }}
            onMin={(v) => onUpdate('distance_min', v)}
            onMax={(v) => onUpdate('distance_max', v)}
            format={(v) => `${v}`}
          />
          <DualRangeSlider
            label="Ascent (ft)"
            minVal={filters.elevation_min} maxVal={filters.elevation_max}
            min={0} max={300000} step={1000}
            scale={{ pivot: 100000, pivotPct: 0.85 }}
            onMin={(v) => onUpdate('elevation_min', v)}
            onMax={(v) => onUpdate('elevation_max', v)}
            format={(v) => `${v.toLocaleString()}`}
          />
          <DualRangeSlider
            label="Unpaved %"
            minVal={filters.unpaved_min} maxVal={filters.unpaved_max}
            min={0} max={100} step={5}
            onMin={(v) => onUpdate('unpaved_min', v)}
            onMax={(v) => onUpdate('unpaved_max', v)}
            format={(v) => `${v}%`}
          />
          <DualRangeSlider
            label="Singletrack %"
            minVal={filters.singletrack_min} maxVal={filters.singletrack_max}
            min={0} max={100} step={5}
            onMin={(v) => onUpdate('singletrack_min', v)}
            onMax={(v) => onUpdate('singletrack_max', v)}
            format={(v) => `${v}%`}
          />
        </div>
      </Section>

      {/* Tire Width */}
      <Section label="Tire Width" id="tire" open={openSections.has('tire')} onToggle={toggle}>
        <DualRangeSlider
          label="Compatible tire width"
          minVal={filters.tire_width_min != null ? filters.tire_width_min / 25.4 : null}
          maxVal={filters.tire_width_max != null ? filters.tire_width_max / 25.4 : null}
          min={1.0} max={5.0} step={0.1}
          onMin={(v) => onUpdate('tire_width_min', v != null && v > 1.0 ? Math.round(v * 25.4) : null)}
          onMax={(v) => onUpdate('tire_width_max', v != null && v < 5.0 ? Math.round(v * 25.4) : null)}
          format={(v) => {
            const mm = Math.round(v * 25.4)
            return mm <= 47 ? `${mm}mm` : `${mm}mm (${v.toFixed(1)}")`
          }}
        />
      </Section>

      {/* Best Season */}
      <Section label="Best Season" id="season" open={openSections.has('season')} onToggle={toggle}>
        <MonthPicker
          selected={filters.months}
          onToggle={(m) => {
            const next = filters.months.includes(m)
              ? filters.months.filter((x) => x !== m)
              : [...filters.months, m]
            onUpdate('months', next)
          }}
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

// Piecewise scale: pivotPct (0–1) of the slider covers min→pivot; remainder covers pivot→max.
// Example: { pivot: 1500, pivotPct: 0.85 } puts 85 % of the slider on the 0–1500 mi range.
type Scale = 'linear' | 'sqrt' | { pivot: number; pivotPct: number }

function DualRangeSlider({
  label, minVal, maxVal, min, max, step, onMin, onMax, format, scale = 'linear',
}: {
  label: string
  minVal: number | null
  maxVal: number | null
  min: number
  max: number
  step: number
  onMin: (v: number | null) => void
  onMax: (v: number | null) => void
  format: (v: number) => string
  scale?: Scale
}) {
  const lo = minVal ?? min
  const hi = maxVal ?? max
  // Track which thumb is being dragged so it stays on top
  const [thumbDown, setThumbDown] = useState<'lo' | 'hi' | null>(null)

  // Release on global pointer up (handles drag-outside-element)
  useEffect(() => {
    if (!thumbDown) return
    const clear = () => setThumbDown(null)
    document.addEventListener('pointerup', clear)
    return () => document.removeEventListener('pointerup', clear)
  }, [thumbDown])

  // Convert actual value → slider position 0–100
  const toPos = (v: number): number => {
    const clamped = Math.max(min, Math.min(max, v))
    if (scale === 'linear') return ((clamped - min) / (max - min)) * 100
    if (scale === 'sqrt') return Math.sqrt(Math.max(0, (clamped - min) / (max - min))) * 100
    // Piecewise linear
    const { pivot, pivotPct } = scale
    if (clamped <= pivot) return ((clamped - min) / (pivot - min)) * pivotPct * 100
    return (pivotPct + ((clamped - pivot) / (max - pivot)) * (1 - pivotPct)) * 100
  }

  // Convert slider position 0–100 → actual value, rounded to step
  const fromPos = (p: number): number => {
    let v: number
    if (scale === 'linear') {
      v = min + (max - min) * (p / 100)
    } else if (scale === 'sqrt') {
      v = min + (max - min) * Math.pow(p / 100, 2)
    } else {
      // Piecewise linear
      const { pivot, pivotPct } = scale
      const pNorm = p / 100
      v = pNorm <= pivotPct
        ? min + (pivot - min) * (pNorm / pivotPct)
        : pivot + (max - pivot) * ((pNorm - pivotPct) / (1 - pivotPct))
    }
    return Math.max(min, Math.min(max, Math.round(v / step) * step))
  }

  const pctLo = toPos(lo)
  const pctHi = toPos(hi)
  const nonLinear = scale === 'sqrt' || typeof scale === 'object'
  const sMin = nonLinear ? 0 : min
  const sMax = nonLinear ? 100 : max
  const sStep = nonLinear ? 0.1 : step
  const sLo = nonLinear ? pctLo : lo
  const sHi = nonLinear ? pctHi : hi

  // Z-index: the active (dragging) thumb is always on top.
  // When nothing is dragged: at max lo must be on top (hi can't go right); otherwise hi on top.
  let loZ: number, hiZ: number
  if (thumbDown === 'lo') {
    loZ = 5; hiZ = 3
  } else if (thumbDown === 'hi') {
    hiZ = 5; loZ = 3
  } else if (sLo >= sMax) {
    // Both at max — lo needs to be grabbable to drag it down
    loZ = 5; hiZ = 3
  } else {
    loZ = 3; hiZ = 4
  }

  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-gray-500">{label}</span>
        <span className="text-gray-700 font-medium">
          {minVal == null && maxVal == null ? 'Any' : `${format(lo)} – ${format(hi)}`}
        </span>
      </div>
      <div className="relative h-5 flex items-center">
        <div className="absolute inset-x-0 h-1.5 bg-gray-200 rounded-full pointer-events-none" />
        <div
          className="absolute h-1.5 bg-green-500 rounded-full pointer-events-none"
          style={{ left: `${pctLo}%`, right: `${100 - pctHi}%` }}
        />
        <input
          type="range" min={sMin} max={sMax} step={sStep} value={sLo}
          onPointerDown={() => setThumbDown('lo')}
          onChange={(e) => {
            const raw = parseFloat(e.target.value)
            const v = nonLinear ? fromPos(raw) : raw
            onMin(v <= min ? null : Math.min(v, hi))
          }}
          className="range-thumb"
          style={{ zIndex: loZ }}
        />
        <input
          type="range" min={sMin} max={sMax} step={sStep} value={sHi}
          onPointerDown={() => setThumbDown('hi')}
          onChange={(e) => {
            const raw = parseFloat(e.target.value)
            const v = nonLinear ? fromPos(raw) : raw
            onMax(v >= max ? null : Math.max(v, lo))
          }}
          className="range-thumb"
          style={{ zIndex: hiZ }}
        />
      </div>
    </div>
  )
}

function LocationFilter({
  filters,
  onUpdate,
}: {
  filters: FilterState
  onUpdate: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
}) {
  const usActive = filters.regions.includes('United States')
  const caActive = filters.regions.includes('Canada')
  const hasUSStates = filters.states.some((s) => US_STATES.includes(s))
  const hasCAProvinces = filters.states.some((s) => CANADA_PROVINCES.includes(s))
  const showUSStates = usActive || hasUSStates
  const showCAProvinces = caActive || hasCAProvinces

  const toggleRegion = (r: string) => {
    const active = filters.regions.includes(r)
    if (active) {
      onUpdate('regions', filters.regions.filter((x) => x !== r))
    } else {
      // Activating "All USA" clears individual US states (they're redundant)
      // Activating "All Canada" clears individual CA provinces
      let newStates = filters.states
      if (r === 'United States') newStates = newStates.filter((s) => !US_STATES.includes(s))
      if (r === 'Canada') newStates = newStates.filter((s) => !CANADA_PROVINCES.includes(s))
      if (newStates !== filters.states) onUpdate('states', newStates)
      onUpdate('regions', [...filters.regions, r])
    }
  }

  const toggleState = (s: string) => {
    const active = filters.states.includes(s)
    if (active) {
      onUpdate('states', filters.states.filter((x) => x !== s))
    } else {
      // Selecting a specific state deactivates the parent "All" region
      let newRegions = filters.regions
      if (US_STATES.includes(s) && newRegions.includes('United States')) {
        newRegions = newRegions.filter((r) => r !== 'United States')
      }
      if (CANADA_PROVINCES.includes(s) && newRegions.includes('Canada')) {
        newRegions = newRegions.filter((r) => r !== 'Canada')
      }
      if (newRegions !== filters.regions) onUpdate('regions', newRegions)
      onUpdate('states', [...filters.states, s])
    }
  }

  const REGION_CHIP_LABELS: Record<string, string> = {
    'Latin America': 'Lat. Am.',
    'Middle East': 'Mid. East',
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Region chips */}
      <div className="flex flex-wrap gap-1.5">
        {REGIONS.map((r) => {
          const chipLabel = REGION_CHIP_LABELS[r] ?? r
          const active = filters.regions.includes(r)
          return (
            <button
              key={r}
              onClick={() => toggleRegion(r)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                active ? 'bg-green-600 text-white border-green-600' : 'bg-white text-gray-700 border-gray-200 hover:border-green-400'
              }`}
            >
              {chipLabel}
            </button>
          )
        })}
      </div>

      {/* US States — visible when "All USA" active or individual states selected */}
      {showUSStates && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">US States</p>
            {hasUSStates && (
              <button
                onClick={() => onUpdate('states', filters.states.filter((s) => !US_STATES.includes(s)))}
                className="text-[10px] text-red-400 hover:text-red-600"
              >
                clear states
              </button>
            )}
          </div>
          <div className="max-h-32 overflow-y-auto pr-0.5">
            <div className="flex flex-wrap gap-1">
              {US_STATES.map((s) => (
                <button
                  key={s}
                  onClick={() => toggleState(s)}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium border transition-colors ${
                    filters.states.includes(s)
                      ? 'bg-green-600 text-white border-green-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-green-400'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Canadian Provinces — visible when "All Canada" active or individual provinces selected */}
      {showCAProvinces && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Canadian Provinces</p>
            {hasCAProvinces && (
              <button
                onClick={() => onUpdate('states', filters.states.filter((s) => !CANADA_PROVINCES.includes(s)))}
                className="text-[10px] text-red-400 hover:text-red-600"
              >
                clear provinces
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1">
            {CANADA_PROVINCES.map((p) => (
              <button
                key={p}
                onClick={() => toggleState(p)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium border transition-colors ${
                  filters.states.includes(p)
                    ? 'bg-green-600 text-white border-green-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-green-400'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function MonthPicker({ selected, onToggle }: { selected: number[]; onToggle: (m: number) => void }) {
  return (
    <div>
      <p className="text-xs text-gray-500 mb-2">Routes whose best season includes any selected month</p>
      <div className="grid grid-cols-4 gap-1">
        {MONTH_ABBR.map((label, i) => {
          const month = i + 1
          const active = selected.includes(month)
          return (
            <button
              key={month}
              onClick={() => onToggle(month)}
              className={`py-1 rounded text-xs font-medium border transition-colors ${
                active
                  ? 'bg-green-600 text-white border-green-600'
                  : 'bg-white text-gray-700 border-gray-200 hover:border-green-400'
              }`}
            >
              {label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
