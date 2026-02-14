import type { Metadata } from 'next'
import { Inter, Caveat, Patrick_Hand } from 'next/font/google'
import '../styles/globals.css'
import { AuthProvider } from '@/lib/auth'

const inter = Inter({ subsets: ['latin'] })
const caveat = Caveat({ subsets: ['latin'], variable: '--font-caveat', weight: ['400', '500', '600', '700'] })
const patrickHand = Patrick_Hand({ subsets: ['latin'], variable: '--font-patrick', weight: '400' })

export const metadata: Metadata = {
  title: 'Lumina',
  description: 'Intelligent research assistant that helps you learn by combining web search with AI-powered teaching',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} ${caveat.variable} ${patrickHand.variable}`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
