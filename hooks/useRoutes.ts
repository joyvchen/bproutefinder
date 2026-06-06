'use client'

import useSWRInfinite from 'swr/infinite'
import { FilterState, Route, RoutesResponse } from '@/lib/types'
import { filtersToParams } from '@/lib/filters'

const PAGE_SIZE = 24

function buildUrl(filters: FilterState, offset: number): string {
  const params = new URLSearchParams(filtersToParams(filters))
  params.set('limit', String(PAGE_SIZE))
  params.set('offset', String(offset))
  return `/api/routes?${params.toString()}`
}

async function fetcher(url: string): Promise<RoutesResponse> {
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch routes')
  return res.json()
}

export function useRoutes(filters: FilterState) {
  const getKey = (pageIndex: number, prev: RoutesResponse | null) => {
    if (prev && prev.routes.length < PAGE_SIZE) return null
    return buildUrl(filters, pageIndex * PAGE_SIZE)
  }

  const { data, error, isLoading, size, setSize } = useSWRInfinite<RoutesResponse>(
    getKey,
    fetcher,
    { revalidateOnFocus: false, revalidateFirstPage: false }
  )

  const routes: Route[] = data ? data.flatMap((page) => page.routes) : []
  const total = data?.[0]?.total ?? 0
  const hasMore = routes.length < total

  return {
    routes,
    total,
    isLoading,
    error,
    hasMore,
    loadMore: () => setSize(size + 1),
  }
}

export async function fetchAllRoutesForMap(filters: FilterState): Promise<Route[]> {
  const params = new URLSearchParams(filtersToParams(filters))
  params.set('limit', '1000')
  params.set('offset', '0')
  const res = await fetch(`/api/routes?${params.toString()}`)
  if (!res.ok) return []
  const data: RoutesResponse = await res.json()
  return data.routes
}
