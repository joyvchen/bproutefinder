import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { hostname: 'bikepacking.com' },
      { hostname: '*.bikepacking.com' },
      { hostname: 'images.bikepacking.com' },
    ],
  },
  transpilePackages: ['mapbox-gl'],
}

export default nextConfig
