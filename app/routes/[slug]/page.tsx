import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { createServerClient } from '@/lib/supabase-server'
import RouteDetail from '@/components/RouteDetail'
import type { Route } from '@/lib/types'

export const revalidate = 3600 // ISR: rebuild detail pages every hour

interface Props {
  params: { slug: string }
}

async function getRoute(slug: string): Promise<Route | null> {
  const supabase = createServerClient()
  const { data, error } = await supabase
    .from('routes')
    .select('*')
    .eq('slug', slug)
    .single()
  if (error || !data) return null
  return data as Route
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const route = await getRoute(params.slug)
  if (!route) return { title: 'Route not found' }

  return {
    title: `${route.name} — Bikepacking Route Finder`,
    description: route.description
      ?? `Explore the ${route.name} bikepacking route${route.state ? ` in ${route.state}` : ''}.`,
    openGraph: {
      title: route.name,
      description: route.description ?? '',
      images: route.image_url ? [{ url: route.image_url }] : [],
    },
  }
}

export default async function RoutePage({ params }: Props) {
  const route = await getRoute(params.slug)
  if (!route) notFound()
  return <RouteDetail route={route} />
}
