'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import Image from 'next/image'
import type { Route } from '@/lib/types'
import BadgeTopPick from './BadgeTopPick'
import { formatDistance, formatDays, formatElevation, formatTireWidth } from '@/lib/map-utils'

interface RouteCardProps {
  route: Route
  isSelected?: boolean
  onHover?: (id: string | null) => void
  onClick?: (route: Route) => void
  layout?: 'sidebar' | 'grid'
}

// ── Bike type display labels ───────────────────────────────────────
const BIKE_TYPE_DISPLAY: Record<string, string> = {
  gravel: 'Gravel',
  hardtail: 'MTB',
  touring: 'Dirt Touring',
  'fat-bike': 'Fat Bike',
}

// ── Ideal bike type inference from free text ──────────────────────
function bikeTypeFromIdealBike(text: string | null): string | null {
  if (!text) return null
  const patterns: Array<[string, RegExp]> = [
    ['ATB', /\bATB\b/i],
    ['Full Sus MTB', /\bfull.?sus(?:pension)?\b/i],
    ['Hardtail MTB', /\bhard.?tail\b/i],
    ['Rigid MTB', /\brigid\s+(?:mountain|mtb|bike)\b/i],
    ['Gravel', /\b(?:gravel|all.road|cyclocross|cross\s*bike)\b/i],
    ['Touring', /\btouring\b/i],
    ['Fat Bike', /fat.?(?:bike|tire|tyre)/i],
    ['MTB', /\b(?:MTB|mountain\s*bike)\b/i],
  ]
  const hits: Array<[number, string]> = []
  for (const [label, re] of patterns) {
    const m = re.exec(text)
    if (!m) continue
    // Skip generic MTB if a sub-type was already found
    if (label === 'MTB' && hits.some(([, l]) => l.includes('MTB'))) continue
    hits.push([m.index, label])
  }
  if (!hits.length) return null
  hits.sort((a, b) => a[0] - b[0])
  return hits.map(([, l]) => l).join(', ')
}

// ── Season month parsing (frontend fallback when DB field is null) ─
const MONTH_MAP: Record<string, number> = {
  january: 1, jan: 1, february: 2, feb: 2, march: 3, mar: 3,
  april: 4, apr: 4, may: 5, june: 6, jun: 6,
  july: 7, jul: 7, august: 8, aug: 8, september: 9, sep: 9, sept: 9,
  october: 10, oct: 10, november: 11, nov: 11, december: 12, dec: 12,
}
const SEASON_MAP: Record<string, number[]> = {
  spring: [3, 4, 5], summer: [6, 7, 8],
  fall: [9, 10, 11], autumn: [9, 10, 11], winter: [12, 1, 2],
}

// Pass 1: explicit unit (mm, inch, double-quote) or "tire width"/"tyre width"
const TIRE_MEASUREMENT_RE = /\d+(?:\.\d+)?(?:\s*x\s*\d+(?:\.\d+)?)?\s*(?:mm|["""″]|inch(?:es)?(?:\b|(?=\s)))|tire\s*width|tyre\s*width/i
// Pass 2: bare decimal tire size — "2.1 or bigger", "3.0+", "45/50mm+", "2.4+"
const BARE_TIRE_SIZE_RE = /\b\d\.\d+\s*(?:or\s+(?:bigger|wider|larger)|\+|["""″])|\b\d{2,3}\/\d{2,3}(?:\s*mm)?\+/i
// Pass 3: tire-characteristic keywords — knobby, fat bike, wide tires, etc.
const TIRE_KEYWORD_RE = /\b(?:tires?|tyres?|knobby|fat\s+(?:tire|tyre|bike)|wide\s+(?:tire|tyre)|balloon|plus.?size)\b/i

// Returns the first tire-relevant sentence from text.
// strict=true → only measurement-based passes (safe for ideal_bike fallback,
// avoids sentences that only describe the bike with no tire sizing info).
function extractTireSentence(text: string | null | undefined, strict = false): string | null {
  if (!text?.trim()) return null
  const sentences = text.split(/(?<=[.!?])\s+/).map(s => s.trim()).filter(s => s.length > 10)
  for (const s of sentences) { if (TIRE_MEASUREMENT_RE.test(s)) return s }   // explicit units
  for (const s of sentences) { if (BARE_TIRE_SIZE_RE.test(s)) return s }     // bare decimal
  if (strict) return null  // ideal_bike fallback: stop here (skip keyword-only sentences)
  for (const s of sentences) { if (TIRE_KEYWORD_RE.test(s)) return s }       // tire keywords
  // Last resort: short text that mentions tires but didn't split into sentences cleanly
  if (/\btires?\b|\btyres?\b/i.test(text) && text.length <= 200) return text.trim()
  return null
}

function parseSeasonMonths(text: string | null): number[] {
  if (!text) return []
  const lower = text.toLowerCase()
  if (/year.?round|all year|any\s*time|anytime/.test(lower)) return Array.from({ length: 12 }, (_, i) => i + 1)

  const found: number[] = []
  for (const [name, num] of Object.entries(MONTH_MAP)) {
    if (new RegExp(`\\b${name}\\b`).test(lower) && !found.includes(num)) found.push(num)
  }
  if (found.length >= 2) {
    const lo = Math.min(...found), hi = Math.max(...found)
    return Array.from({ length: hi - lo + 1 }, (_, i) => lo + i)
  }
  if (found.length === 1) return found

  const seasonal = new Set<number>()
  for (const [season, months] of Object.entries(SEASON_MAP)) {
    if (new RegExp(`\\b${season}\\b`).test(lower)) months.forEach((m) => seasonal.add(m))
  }
  return Array.from(seasonal).sort((a, b) => a - b)
}

// ── Difficulty colour scale ────────────────────────────────────────
function diffColors(score: number) {
  if (score <= 3) return 'bg-emerald-100 text-emerald-800'
  if (score <= 5) return 'bg-yellow-100 text-yellow-800'
  if (score <= 7) return 'bg-orange-100 text-orange-800'
  return 'bg-red-100 text-red-800'
}

// ── Tooltip portal — flips below when near viewport top ───────────
function InfoTooltip({ text }: { text: string }) {
  const [visible, setVisible] = useState(false)
  const [pos, setPos] = useState({ top: 0, bottom: 0, left: 0, flipDown: false })
  const btnRef = useRef<HTMLButtonElement>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => { setMounted(true) }, [])

  const show = useCallback(() => {
    if (!btnRef.current) return
    const r = btnRef.current.getBoundingClientRect()
    setPos({
      top: r.top,
      bottom: r.bottom,
      left: r.left + r.width / 2,
      flipDown: r.top < 130,
    })
    setVisible(true)
  }, [])

  const hide = useCallback(() => setVisible(false), [])

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        onMouseEnter={show}
        onMouseLeave={hide}
        className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-gray-200 text-gray-500 text-[8px] font-bold leading-none hover:bg-gray-300 flex-shrink-0"
        aria-label="More info"
      >
        ?
      </button>
      {mounted && visible && (() => {
        const vw = typeof window !== 'undefined' ? window.innerWidth : 1200
        const tooltipLeft = Math.max(8, Math.min(vw - 296, pos.left - 144))
        const caretLeft = Math.max(10, Math.min(278, pos.left - tooltipLeft))
        return createPortal(
          <div
            className="fixed z-[9999] w-72 rounded-lg bg-gray-900 text-white text-xs px-3 py-2 shadow-xl pointer-events-none leading-relaxed"
            style={{ top: pos.flipDown ? pos.bottom + 8 : pos.top - 8, left: tooltipLeft }}
          >
            {text}
            {pos.flipDown ? (
              <div className="absolute bottom-full w-0 h-0" style={{
                left: caretLeft,
                borderLeft: '5px solid transparent',
                borderRight: '5px solid transparent',
                borderBottom: '5px solid #111827',
              }} />
            ) : (
              <div className="absolute top-full w-0 h-0" style={{
                left: caretLeft,
                borderLeft: '5px solid transparent',
                borderRight: '5px solid transparent',
                borderTop: '5px solid #111827',
              }} />
            )}
          </div>,
          document.body,
        )
      })()}
    </>
  )
}

// ── Icons ──────────────────────────────────────────────────────────
const cls = 'w-4 h-4 text-gray-400 flex-shrink-0'

const IconDistance = () => (
  <svg viewBox="0 0 24 24" fill="none" className={cls} aria-hidden>
    <path d="M6 16s-3-4-3-7a3 3 0 116 0c0 3-3 7-3 7z" fill="currentColor" fillOpacity=".65"/>
    <circle cx="6" cy="9" r="1.3" fill="white"/>
    <path d="M18 16s-3-4-3-7a3 3 0 116 0c0 3-3 7-3 7z" fill="currentColor" fillOpacity=".65"/>
    <circle cx="18" cy="9" r="1.3" fill="white"/>
    <path d="M9 13h6" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1.5" strokeLinecap="round"/>
  </svg>
)
const IconDays = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" className={cls} aria-hidden>
    <rect x="3" y="5" width="18" height="16" rx="2.5"/>
    <path d="M3 10h18"/><path d="M8 3v4M16 3v4"/>
    <circle cx="8.5" cy="15" r=".9" fill="currentColor" stroke="none"/>
    <circle cx="12" cy="15" r=".9" fill="currentColor" stroke="none"/>
    <circle cx="15.5" cy="15" r=".9" fill="currentColor" stroke="none"/>
  </svg>
)
const IconAscent = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={cls} aria-hidden>
    <polyline points="3,18 8,12 13,15 21,6"/><polyline points="16,6 21,6 21,11"/>
  </svg>
)
const IconRideable = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={cls} aria-hidden>
    <circle cx="6" cy="16" r="3.5"/><circle cx="18" cy="16" r="3.5"/>
    <path d="M6 16l4.5-8h5"/><path d="M13 8l2 4 3 4"/><path d="M11 5h4"/>
    <circle cx="13" cy="4.5" r="1.5" fill="currentColor" stroke="none"/>
  </svg>
)
const IconUnpaved = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={cls} aria-hidden>
    <path d="M3 20l4.5-14h9L21 20H3z"/>
    <path strokeDasharray="2 2" d="M10 14h4M9.5 17.5h5"/>
  </svg>
)
const IconSingletrack = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={cls} aria-hidden>
    <path d="M13 4c-2 4 2 8 0 12s-2 5-2 5"/><path d="M15 21c0 0-1-3 0-8"/>
  </svg>
)
const IconBike = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={cls} aria-hidden>
    <circle cx="5.5" cy="16.5" r="3.5"/><circle cx="18.5" cy="16.5" r="3.5"/>
    <path d="M5.5 16.5l5-8.5h3l4.5 4.5"/><path d="M10.5 8l2-3"/>
    <circle cx="13" cy="4.5" r="1.5" fill="currentColor" stroke="none"/>
    <path d="M13 8l1.5 4"/>
  </svg>
)
const IconTire = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" className={cls} aria-hidden>
    <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.5"/>
    <path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21"/>
  </svg>
)
const IconDifficulty = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" aria-hidden>
    <path d="M4 19l4-8 4 4 4-8 4 4"/>
  </svg>
)
const IconChevron = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3 text-gray-400 transition-transform group-open:rotate-180 shrink-0" aria-hidden>
    <path d="M19 9l-7 7-7-7"/>
  </svg>
)

// ── Stat grid cell ─────────────────────────────────────────────────
function StatCell({
  icon, value, label, tooltip,
}: {
  icon: React.ReactNode
  value: React.ReactNode
  label: string
  tooltip?: string
}) {
  return (
    <div className="flex flex-col items-center gap-0.5 px-1 py-2 min-w-0 overflow-hidden text-center">
      {icon}
      <div className="flex items-center justify-center gap-0.5 w-full">
        <span className="text-[10px] font-bold text-gray-900 leading-snug break-words min-w-0 flex-1 text-center">
          {value}
        </span>
        {tooltip && <InfoTooltip text={tooltip} />}
      </div>
      <div className="text-[9px] text-gray-400 leading-none whitespace-nowrap">{label}</div>
    </div>
  )
}

// ── Month row for best season ──────────────────────────────────────
const MONTH_LETTERS = ['J','F','M','A','M','J','J','A','S','O','N','D']

function MonthRow({ months }: { months: number[] }) {
  return (
    <div className="flex gap-0.5">
      {MONTH_LETTERS.map((m, i) => {
        const active = months.includes(i + 1)
        return (
          <div
            key={i}
            className={`flex-1 text-center text-[9px] py-1 rounded font-semibold select-none transition-colors ${
              active ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-400'
            }`}
          >
            {m}
          </div>
        )
      })}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
// Grid card — full detail
// ══════════════════════════════════════════════════════════════════
function GridCard({ route, isSelected, onHover }: RouteCardProps) {
  const bikeTypeDisplay = route.bike_type?.length
    ? route.bike_type.map((t) => BIKE_TYPE_DISPLAY[t] ?? t.replace(/-/g, ' ')).join(', ')
    : (route.llm_ideal_bike ?? bikeTypeFromIdealBike(route.ideal_bike))

  const bikeTip = route.llm_bike_tooltip?.trim()
    ?? (route.ideal_bike?.trim() ? `Best Bike: ${route.ideal_bike.trim()}` : undefined)
  // llm_tire_width_notes is the concise display label (e.g. "2.35"", "45mm–2.4"")
  // Tooltip: find the first sentence in either scraped field that contains an
  // actual tire measurement. Never fall back to bike-only content.
  const tireLabel = route.llm_tire_width_notes ?? null
  const tireTip = extractTireSentence(route.tire_width_notes)
    ?? extractTireSentence(route.llm_bike_tooltip)
    ?? undefined

  const tireMinMm = route.llm_tire_width_min_mm ?? route.tire_width_min_mm
  const tireMaxMm = route.llm_tire_width_max_mm ?? route.tire_width_max_mm

  // LLM months > scraped months > parse best_season text
  const seasonMonths = (route.llm_best_season_months?.length ?? 0) > 0
    ? route.llm_best_season_months!
    : parseSeasonMonths(route.best_season)

  return (
    <a
      href={route.source_url}
      target="_blank"
      rel="noopener noreferrer"
      className={`group flex flex-col rounded-xl overflow-hidden border bg-white transition-all duration-150 hover:shadow-lg ${
        isSelected ? 'border-green-500 shadow-md ring-1 ring-green-400' : 'border-gray-200'
      }`}
      onMouseEnter={() => onHover?.(route.id)}
      onMouseLeave={() => onHover?.(null)}
    >
      {/* ── Image ── */}
      <div className="relative w-full aspect-video shrink-0 overflow-hidden bg-gray-200">
        {route.image_url ? (
          <Image
            src={route.image_url}
            alt={route.image_alt ?? route.name}
            fill
            className="object-cover transition-transform duration-300 group-hover:scale-[1.03]"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-green-900 to-green-700 flex items-center justify-center">
            <span className="text-white/30 text-sm">No photo</span>
          </div>
        )}
        {route.is_top_pick && (
          <div className="absolute top-2 left-2">
            <BadgeTopPick label={route.editorial_label} href={route.editorial_source_url} size="sm" />
          </div>
        )}
      </div>

      {/* ── Body ── */}
      <div className="flex flex-col gap-2.5 p-3 flex-1">

        {/* Title + location */}
        <div>
          <h3 className="font-bold text-gray-900 text-sm leading-snug line-clamp-2 group-hover:text-green-700 transition-colors">
            {route.name}
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {[route.state, route.country].filter(Boolean).join(', ')}
          </p>
        </div>

        {/* ── Stats 2×4 merged grid ── */}
        <div className="border border-gray-100 rounded-lg overflow-hidden bg-gray-50/60">
          <div className="grid grid-cols-4 divide-x divide-gray-100">
            <StatCell icon={<IconDistance />} label="Distance" value={formatDistance(route.distance_mi, route.distance_km)} />
            <StatCell icon={<IconDays />} label="Days" value={formatDays(route.days_min, route.days_max)} />
            <StatCell icon={<IconAscent />} label="Ascent" value={route.elevation_gain_ft ? formatElevation(route.elevation_gain_ft) : '—'} />
            <StatCell icon={<IconRideable />} label="Rideable" value={route.rideable_pct != null ? `${route.rideable_pct}%` : '—'} />
          </div>
          <div className="grid grid-cols-4 divide-x divide-gray-100 border-t border-gray-100">
            <StatCell icon={<IconUnpaved />} label="Unpaved" value={route.unpaved_pct != null ? `${route.unpaved_pct}%` : '—'} />
            <StatCell icon={<IconSingletrack />} label="Singletrack" value={route.singletrack_pct != null ? `${route.singletrack_pct}%` : '—'} />
            <StatCell
              icon={<IconBike />}
              label="Ideal Bike"
              value={bikeTypeDisplay ?? '—'}
              tooltip={bikeTip}
            />
            <StatCell
              icon={<IconTire />}
              label="Tires"
              value={tireLabel ?? (tireMinMm != null ? formatTireWidth(tireMinMm, tireMaxMm) : '—')}
              tooltip={tireTip}
            />
          </div>
        </div>

        {/* ── Difficulty (collapsible sub-ratings) ── */}
        <details className="border border-gray-100 rounded-lg overflow-hidden group">
          <summary className="flex items-center justify-between px-3 py-2 bg-gray-50/60 cursor-pointer select-none list-none">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-1.5">
              <IconDifficulty />
              Difficulty
            </span>
            <div className="flex items-center gap-2">
              {route.difficulty != null ? (
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${diffColors(route.difficulty)}`}>
                  {route.difficulty}/10
                </span>
              ) : (
                <span className="text-xs text-gray-300 bg-gray-100 px-2 py-0.5 rounded-full font-semibold">—</span>
              )}
              <IconChevron />
            </div>
          </summary>
          <div className="grid grid-cols-2 divide-x divide-gray-100 border-t border-gray-100">
            {([
              { label: 'Climbing',  value: route.climbing_scale },
              { label: 'Technical', value: route.technical_difficulty },
              { label: 'Physical',  value: route.physical_demand },
              { label: 'Logistics', value: route.resupply_logistics },
            ] as const).map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between px-3 py-1.5">
                <span className="text-xs text-gray-500">{label}</span>
                {value != null ? (
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${diffColors(value)}`}>{value}</span>
                ) : (
                  <span className="text-xs font-semibold text-gray-300 bg-gray-100 px-1.5 py-0.5 rounded">—</span>
                )}
              </div>
            ))}
          </div>
        </details>

        {/* ── Best Season ── */}
        {seasonMonths.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Best Season</p>
            <MonthRow months={seasonMonths} />
          </div>
        )}
      </div>
    </a>
  )
}

// ══════════════════════════════════════════════════════════════════
// Compact sidebar / list card
// ══════════════════════════════════════════════════════════════════
function SidebarCard({ route, isSelected, onHover, onClick }: RouteCardProps) {
  return (
    <div
      className={`group flex gap-3 p-3 rounded-lg cursor-pointer transition-colors duration-100 ${
        isSelected ? 'bg-green-50 border border-green-200' : 'hover:bg-gray-50 border border-transparent'
      }`}
      onMouseEnter={() => onHover?.(route.id)}
      onMouseLeave={() => onHover?.(null)}
      onClick={() => onClick?.(route)}
    >
      <div className="relative w-20 h-16 shrink-0 rounded-md overflow-hidden bg-gray-200">
        {route.image_url ? (
          <Image src={route.image_url} alt={route.image_alt ?? route.name} fill className="object-cover" sizes="80px" />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-green-800 to-green-600" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-1 justify-between">
          <a
            href={route.source_url} target="_blank" rel="noopener noreferrer"
            className="font-semibold text-sm text-gray-900 leading-tight hover:text-green-700 line-clamp-2"
            onClick={(e) => e.stopPropagation()}
          >
            {route.name}
          </a>
          {route.is_top_pick && (
            <BadgeTopPick label={route.editorial_label} href={route.editorial_source_url} size="sm" />
          )}
        </div>
        <p className="text-xs text-gray-500 mt-0.5">{[route.state, route.country].filter(Boolean).join(', ')}</p>
        <div className="flex flex-wrap gap-x-2 gap-y-0.5 mt-1.5">
          <span className="text-xs text-gray-600">{formatDistance(route.distance_mi, route.distance_km)}</span>
          <span className="text-xs text-gray-600">{formatDays(route.days_min, route.days_max)}</span>
          {route.difficulty != null && (
            <span className={`text-xs font-semibold px-1.5 rounded ${diffColors(route.difficulty)}`}>
              {route.difficulty}/10
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Loading skeleton ───────────────────────────────────────────────
export function RouteCardSkeleton() {
  return (
    <div className="rounded-xl overflow-hidden border border-gray-100 bg-white animate-pulse">
      <div className="aspect-video bg-gray-200" />
      <div className="p-3 flex flex-col gap-2.5">
        <div className="h-3.5 bg-gray-200 rounded w-3/4" />
        <div className="h-2.5 bg-gray-100 rounded w-1/2" />
        <div className="h-14 bg-gray-100 rounded" />
        <div className="h-9 bg-gray-100 rounded" />
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
export default function RouteCard(props: RouteCardProps) {
  return props.layout === 'grid' ? <GridCard {...props} /> : <SidebarCard {...props} />
}
