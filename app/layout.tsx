import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Bikepacking Route Finder',
  description:
    'Discover and filter Bikepacking.com routes by location, difficulty, bike type, distance, and more. A map-first search companion for bikepacking trip planning.',
  openGraph: {
    title: 'Bikepacking Route Finder',
    description: 'Find your next bikepacking adventure. Filter by location, difficulty, and bike type.',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans antialiased bg-white text-gray-900 overflow-hidden">
        {children}
      </body>
    </html>
  )
}
