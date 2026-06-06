/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { hostname: 'bikepacking.com' },
      { hostname: '*.bikepacking.com' },
      { hostname: 'images.bikepacking.com' },
    ],
  },
}

module.exports = nextConfig
