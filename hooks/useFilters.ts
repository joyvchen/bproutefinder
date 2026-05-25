'use client'

import { useCallback, useMemo, useState } from 'react'
import { FilterState, DEFAULT_FILTERS } from '@/lib/types'

export function useFilters() {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS)

  const updateFilter = useCallback(<K extends keyof FilterState>(key: K, value: FilterState[K]) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }, [])

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS)
  }, [])

  const toggleBikeType = useCallback((type: string) => {
    setFilters((prev) => {
      const current = prev.bike_type
      const next = current.includes(type)
        ? current.filter((t) => t !== type)
        : [...current, type]
      return { ...prev, bike_type: next }
    })
  }, [])

  return { filters, updateFilter, resetFilters, toggleBikeType }
}
