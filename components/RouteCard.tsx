'use client'

import Image from 'next/image'
import Link from 'next/link'
import type { Route } from '@/lib/types'
import BadgeTopPick from './BadgeTopPick'
import { formatDistance, formatDays, formatDifficulty, formatElevation, formatBikeType } from '@/lib/map-utils'

interface RouteCardProps {
  route: Route
  isSelected?: boolean
  onHover?: (id: string | null) => void
  onClick?: (route: Route) => void
  layout?: 'sidebar' | 'grid'
}

export default function RouteCard({
  route,
  isSelected,
  onHover,
  onClick,
  layout = 'sidebar',
}: RouteCardProps) {
  if (layout === 'grid') {
    return (
      <Link
        href={`/routes/${route.slug}`}
        className={`group block rounded-xl overflow-hidden border transition-all duration-150 hover:shadow-md ${
          isSelected ? 'border-green-500 shadow-md' : 'border-gray-200'
        }`}
        onMouseEnter={() => onHover?.(route.id)}
        onMouseLeave={() => onHover?.(null)}
      >
        <div className="relative h-44 bg-gray-100">
          {route.image_url ? (
            <Image
              src={route.image_url}
              alt={route.image_alt ?? route.name}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-300"
              sizes="(max-width: 768px) 100vw, 400px"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-green-800 to-green-600 flex items-center justify-center">
              <span className="text-white/60 text-sm">No image</span>
            </div>
          )}
          {route.is_top_pick && (
            <div className="absolute top-2 left-2">
              <BadgeTopPick score={route.recommendation_score} size="sm" />
            </div>
          )}
        </div>
        <div className="p-3">
          <h3 className="font-semibold text-gray-900 text-sm leading-tight line-clamp-2">
            {route.name}
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {[route.state, route.country].filter(Boolean).join(', ')}
          </p>
          <StatRow route={route} />
        </div>
      </Link>
    )
  }

  // Sidebar layout
  return (
    <div
      className={`group flex gap-3 p-3 rounded-lg cursor-pointer transition-colors duration-100 ${
        isSelected ? 'bg-green-50 border border-green-200' : 'hover:bg-gray-50 border border-transparent'
      }`}
      onMouseEnter={() => onHover?.(route.id)}
      onMouseLeave={() => onHover?.(null)}
      onClick={() => onClick?.(route)}
    >
      <div className="relative w-20 h-16 flex-shrink-0 rounded-md overflow-hidden bg-gray-100">
        {route.image_url ? (
          <Image
            src={route.image_url}
            alt={route.image_alt ?? route.name}
            fill
            className="object-cover"
            sizes="80px"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-green-800 to-green-600" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-1 justify-between">
          <Link
            href={`/routes/${route.slug}`}
            className="font-semibold text-sm text-gray-900 leading-tight hover:text-green-700 line-clamp-2"
            onClick={(e) => e.stopPropagation()}
          >
            {route.name}
          </Link>
          {route.is_top_pick && <BadgeTopPick score={route.recommendation_score} size="sm" />}
        </div>

        <p className="text-xs text-gray-500 mt-0.5">
          {[route.state, route.country].filter(Boolean).join(', ')}
        </p>

        <StatRow route={route} compact />
      </div>
    </div>
  )
}

function StatRow({ route, compact }: { route: Route; compact?: boolean }) {
  const stats = [
    route.distance_mi ? formatDistance(route.distance_mi, route.distance_km) : null,
    route.days_min ? formatDays(route.days_min, route.days_max) : null,
    route.difficulty ? `Difficulty ${formatDifficulty(route.difficulty)}` : null,
    !compact && route.elevation_gain_ft ? formatElevation(route.elevation_gain_ft) : null,
    !compact && route.bike_type?.length ? formatBikeType(route.bike_type) : null,
  ].filter(Boolean)

  return (
    <div className="flex flex-wrap gap-x-2 gap-y-0.5 mt-1.5">
      {stats.map((s) => (
        <span key={s} className="text-xs text-gray-600">{s}</span>
      ))}
    </div>
  )
}
