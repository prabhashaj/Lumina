'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { Sparkles, Eye, EyeOff, ArrowRight, Mail, Lock, AlertCircle, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const { user, isLoading, login, loginWithProvider } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [oauthLoading, setOauthLoading] = useState<'google' | 'github' | null>(null)

  useEffect(() => {
    if (!isLoading && user) {
      router.push('/app')
    }
  }, [user, isLoading, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!email || !password) {
      setError('Please fill in all fields')
      return
    }

    setIsSubmitting(true)
    const success = await login(email, password)
    setIsSubmitting(false)

    if (success) {
      router.push('/app')
    } else {
      setError('Invalid email or password')
    }
  }

  const handleOAuth = async (provider: 'google' | 'github') => {
    setError('')
    setOauthLoading(provider)
    try {
      const success = await loginWithProvider(provider)
      if (success) {
        router.push('/app')
      } else {
        setError(`Failed to sign in with ${provider === 'google' ? 'Google' : 'GitHub'}`)
      }
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setOauthLoading(null)
    }
  }

  if (isLoading || user) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center animate-pulse-glow">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center relative overflow-hidden">
      {/* Background effects */}
      <div className="orb orb-primary w-[400px] h-[400px] -top-32 -right-32 animate-float opacity-60" />
      <div className="orb orb-secondary w-[300px] h-[300px] bottom-16 -left-32 animate-float opacity-40" style={{ animationDelay: '1.5s' }} />

      <div className="relative z-10 w-full max-w-sm mx-auto px-5">
        {/* Logo */}
        <div className="text-center mb-7 animate-fadeInUp">
          <Link href="/" className="inline-flex flex-col items-center gap-2 group">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-xl shadow-[hsl(73,31%,45%)]/25 group-hover:shadow-[hsl(73,31%,45%)]/40 transition-shadow duration-300">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-gradient">Lumina</span>
          </Link>
        </div>

        {/* Login Card */}
        <div className="bg-card/60 border border-border/30 rounded-2xl p-6 backdrop-blur-xl shadow-2xl animate-fadeInUp" style={{ animationDelay: '0.1s' }}>
          <div className="text-center mb-5">
            <h1 className="text-xl font-bold mb-1">Welcome back</h1>
            <p className="text-xs text-muted-foreground">Sign in to continue learning</p>
          </div>

          {/* OAuth buttons */}
          <div className="flex gap-3 mb-5">
            <button
              type="button"
              onClick={() => handleOAuth('google')}
              disabled={!!oauthLoading || isSubmitting}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-white dark:bg-white/95 text-gray-800 text-sm font-medium rounded-lg border border-gray-200 dark:border-gray-300 hover:bg-gray-50 dark:hover:bg-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {oauthLoading === 'google' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              )}
              Google
            </button>
            <button
              type="button"
              onClick={() => handleOAuth('github')}
              disabled={!!oauthLoading || isSubmitting}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#24292e] text-white text-sm font-medium rounded-lg border border-[#24292e] hover:bg-[#2f363d] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {oauthLoading === 'github' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
                </svg>
              )}
              GitHub
            </button>
          </div>

          {/* Divider */}
          <div className="relative mb-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border/40"></div>
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-3 bg-card/60 text-muted-foreground/60 backdrop-blur-sm">or continue with email</span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5">
            {error && (
              <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs animate-fadeIn">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground/70">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/50" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2.5 rounded-lg bg-muted/30 border border-border/30 text-sm placeholder:text-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-[hsl(73,31%,45%)]/30 focus:border-[hsl(73,31%,45%)]/50 transition-all"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-foreground/70">Password</label>
                <button type="button" className="text-[11px] text-[hsl(73,31%,55%)] hover:text-[hsl(73,31%,65%)] transition-colors">
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/50" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-10 py-2.5 rounded-lg bg-muted/30 border border-border/30 text-sm placeholder:text-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-[hsl(73,31%,45%)]/30 focus:border-[hsl(73,31%,45%)]/50 transition-all"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !!oauthLoading}
              className="w-full flex items-center justify-center gap-2 py-2.5 mt-1 bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,55%)] text-white text-sm font-semibold rounded-lg hover:shadow-lg hover:shadow-[hsl(73,31%,45%)]/25 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  Sign in
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          <p className="mt-5 text-center text-xs text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link href="/signup" className="font-semibold text-[hsl(73,31%,55%)] hover:text-[hsl(73,31%,65%)] transition-colors">
              Sign up free
            </Link>
          </p>
        </div>

        <div className="text-center mt-5 animate-fadeInUp" style={{ animationDelay: '0.2s' }}>
          <Link href="/" className="text-[11px] text-muted-foreground/60 hover:text-foreground transition-colors">
            &larr; Back to home
          </Link>
        </div>
      </div>
    </div>
  )
}
