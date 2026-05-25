import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@/lib/supabase-server'
import type { SortOption } from '@/lib/types'

export const runtime = 'edge'

const PAGE_SIZE = 24

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams
  const supabase = createServerClient()

  const q = sp.get('q')?.trim()
  const state = sp.get('state')?.trim()
  const bikeTypes = sp.get('bike_type')?.split(',').filter(Boolean) ?? []
  const diffMin = parseFloat(sp.get('difficulty_min') ?? '') || null
  const diffMax = parseFloat(sp.get('difficulty_max') ?? '') || null
  const daysMin = parseInt(sp.get('days_min') ?? '') || null
  const daysMax = parseInt(sp.get('days_max') ?? '') || null
  const distMin = parseFloat(sp.get('distance_min') ?? '') || null
  const distMax = parseFloat(sp.get('distance_max') ?? '') || null
  const elevMax = parseInt(sp.get('elevation_max') ?? '') || null
  const unpavedMin = parseInt(sp.get('unpaved_min') ?? '') || null
  const singleMin = parseInt(sp.get('singletrack_min') ?? '') || null
  const tireMin = parseInt(sp.get('tire_width_min') ?? '') || null
  const tireMax = parseInt(sp.get('tire_width_max') ?? '') || null
  const topPickOnly = sp.get('top_pick_only') === 'true'
  const sort = (sp.get('sort') as SortOption) ?? 'recommended'
  const limit = Math.min(parseInt(sp.get('limit') ?? '') || PAGE_SIZE, 100)
  const offset = parseInt(sp.get('offset') ?? '') || 0

  let query = supabase
    .from('routes')
    .select('*', { count: 'exact' })

  // Full-text search; fall back to ilike on zero results
  if (q) {
    query = query.textSearch('fts', q, { type: 'websearch', config: 'english' })
  }

  if (state) query = query.ilike('state', `%${state}%`)
  if (bikeTypes.length) query = query.overlaps('bike_type', bikeTypes)
  if (diffMin != null) query = query.gte('difficulty', diffMin)
  if (diffMax != null) query = query.lte('difficulty', diffMax)
  if (daysMin != null) query = query.gte('days_max', daysMin)
  if (daysMax != null) query = query.lte('days_min', daysMax)
  if (distMin != null) query = query.gte('distance_mi', distMin)
  if (distMax != null) query = query.lte('distance_mi', distMax)
  if (elevMax != null) query = query.lte('elevation_gain_ft', elevMax)
  if (unpavedMin != null) query = query.gte('unpaved_pct', unpavedMin)
  if (singleMin != null) query = query.gte('singletrack_pct', singleMin)
  if (tireMin != null) query = query.gte('tire_width_max_mm', tireMin)
  if (tireMax != null) query = query.lte('tire_width_min_mm', tireMax)
  if (topPickOnly) query = query.eq('is_top_pick', true)

  // Sorting
  switch (sort) {
    case 'distance_asc':   query = query.order('distance_mi', { ascending: true }); break
    case 'distance_desc':  query = query.order('distance_mi', { ascending: false }); break
    case 'elevation_asc':  query = query.order('elevation_gain_ft', { ascending: true }); break
    case 'elevation_desc': query = query.order('elevation_gain_ft', { ascending: false }); break
    case 'days_asc':       query = query.order('days_min', { ascending: true }); break
    case 'days_desc':      query = query.order('days_max', { ascending: false }); break
    case 'difficulty_asc': query = query.order('difficulty', { ascending: true }); break
    case 'difficulty_desc':query = query.order('difficulty', { ascending: false }); break
    default:
      query = query
        .order('recommendation_score', { ascending: false })
        .order('is_top_pick', { ascending: false })
  }

  query = query.range(offset, offset + limit - 1)

  const { data, count, error } = await query

  if (error) {
    // If FTS fails (e.g. empty query), retry with ilike
    if (q && error.code === 'PGRST103') {
      const fallback = await supabase
        .from('routes')
        .select('*', { count: 'exact' })
        .ilike('name', `%${q}%`)
        .range(offset, offset + limit - 1)
      return NextResponse.json({ routes: fallback.data ?? [], total: fallback.count ?? 0 })
    }
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ routes: data ?? [], total: count ?? 0 })
}
