'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { Sparkles } from 'lucide-react'
import LandingPage from './(landing)/page'

export default function RootPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && user) {
      router.replace('/app')
    }
  }, [user, isLoading, router])

  if (isLoading || user) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center animate-pulse-glow">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
      </div>
    )
  }

  return <LandingPage />
}
