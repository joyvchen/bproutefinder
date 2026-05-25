import Image from 'next/image'
import Link from 'next/link'
import type { Route } from '@/lib/types'
import BadgeTopPick from './BadgeTopPick'
import {
  formatDistance, formatElevation, formatDays, formatDifficulty,
  formatPct, formatTireWidth, formatBikeType,
} from '@/lib/map-utils'

interface StatTileProps {
  label: string
  value: string
}

function StatTile({ label, value }: StatTileProps) {
  if (!value || value === '—') return null
  return (
    <div className="flex flex-col bg-gray-50 rounded-xl px-4 py-3 min-w-0">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">{label}</span>
      <span className="text-base font-bold text-gray-900 leading-tight">{value}</span>
    </div>
  )
}

export default function RouteDetail({ route }: { route: Route }) {
  return (
    <main className="min-h-screen bg-white">
      {/* Back nav */}
      <nav className="fixed top-0 left-0 right-0 z-10 bg-white/90 backdrop-blur-sm border-b border-gray-100">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to map
          </Link>
        </div>
      </nav>

      <div className="pt-14">
        {/* Hero image */}
        <div className="relative w-full h-64 sm:h-80 md:h-96 bg-gray-200">
          {route.image_url ? (
            <Image
              src={route.image_url}
              alt={route.image_alt ?? route.name}
              fill
              priority
              className="object-cover"
              sizes="100vw"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-green-900 via-green-700 to-green-500" />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
        </div>

        {/* Content */}
        <div className="max-w-3xl mx-auto px-4 py-8">
          {/* Title row */}
          <div className="flex flex-wrap items-start gap-3 mb-2">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex-1 leading-tight">
              {route.name}
            </h1>
            {route.is_top_pick && (
              <BadgeTopPick score={route.recommendation_score} size="md" />
            )}
          </div>

          {/* Location */}
          <p className="text-base text-gray-500 mb-6">
            {[route.region, route.state, route.country].filter(Boolean).join(' · ')}
          </p>

          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8">
            <StatTile label="Distance" value={formatDistance(route.distance_mi, route.distance_km)} />
            <StatTile label="Ascent" value={formatElevation(route.elevation_gain_ft)} />
            <StatTile label="Est. Days" value={formatDays(route.days_min, route.days_max)} />
            <StatTile label="Difficulty" value={route.difficulty ? `${formatDifficulty(route.difficulty)} out of 10` : '—'} />
            <StatTile label="Unpaved" value={route.unpaved_pct != null ? `${route.unpaved_pct}%` : '—'} />
            <StatTile label="Singletrack" value={route.singletrack_pct != null ? `${route.singletrack_pct}%` : '—'} />
            <StatTile label="Rideable" value={route.rideable_pct != null ? `${route.rideable_pct}%` : '—'} />
            <StatTile label="Bike Type" value={formatBikeType(route.bike_type)} />
            <StatTile label="Tire Width" value={formatTireWidth(route.tire_width_min_mm, route.tire_width_max_mm)} />
          </div>

          {/* Description excerpt */}
          {route.description && (
            <div className="mb-8">
              <p className="text-gray-700 leading-relaxed text-base">{route.description}</p>
              <p className="text-xs text-gray-400 mt-2 italic">
                Excerpt from Bikepacking.com — see the full route page for complete details.
              </p>
            </div>
          )}

          {/* Divider */}
          <hr className="border-gray-100 mb-8" />

          {/* CTA */}
          <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
            <a
              href={route.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-green-600 text-white font-semibold text-sm hover:bg-green-700 transition-colors shadow-sm"
            >
              View full route on Bikepacking.com
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
            <p className="text-xs text-gray-400">
              Route content © <a href="https://bikepacking.com" className="underline hover:text-gray-600" target="_blank" rel="noopener noreferrer">Bikepacking.com</a>
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
