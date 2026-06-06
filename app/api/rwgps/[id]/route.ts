import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'edge'

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const res = await fetch(
      `https://ridewithgps.com/routes/${params.id}.json?apikey=testkey1`,
      { headers: { 'User-Agent': 'Mozilla/5.0' } }
    )
    if (!res.ok) return NextResponse.json({}, { status: res.status })
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({}, { status: 502 })
  }
}
