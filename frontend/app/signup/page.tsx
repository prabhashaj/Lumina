'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { Sparkles, Eye, EyeOff, ArrowRight, Mail, Lock, User, AlertCircle, CheckCircle2, Loader2, ShieldCheck, ArrowLeft } from 'lucide-react'

type Step = 'form' | 'verify'

export default function SignupPage() {
  const router = useRouter()
  const { user, isLoading, signup, loginWithProvider, sendVerificationCode, verifyEmail } = useAuth()
  const [step, setStep] = useState<Step>('form')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [oauthLoading, setOauthLoading] = useState<'google' | 'github' | null>(null)

  // Verification state
  const [verificationCode, setVerificationCode] = useState('')
  const [codeDigits, setCodeDigits] = useState(['', '', '', '', '', ''])
  const [generatedCode, setGeneratedCode] = useState('')
  const [resendTimer, setResendTimer] = useState(0)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    if (!isLoading && user) {
      router.push('/app')
    }
  }, [user, isLoading, router])

  // Resend timer countdown
  useEffect(() => {
    if (resendTimer > 0) {
      const t = setTimeout(() => setResendTimer(resendTimer - 1), 1000)
      return () => clearTimeout(t)
    }
  }, [resendTimer])

  const passwordChecks = [
    { label: '8+ characters', valid: password.length >= 8 },
    { label: 'A number', valid: /\d/.test(password) },
    { label: 'A letter', valid: /[a-zA-Z]/.test(password) },
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!name || !email || !password || !confirmPassword) {
      setError('Please fill in all fields')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (!passwordChecks.every((c) => c.valid)) {
      setError('Please meet all password requirements')
      return
    }

    setIsSubmitting(true)
    const result = await signup(name, email, password)
    setIsSubmitting(false)

    if (result.success) {
      // Send verification code
      const code = sendVerificationCode(email)
      setGeneratedCode(code)
      setResendTimer(60)
      setStep('verify')
    } else {
      setError(result.error || 'Something went wrong')
    }
  }

  const handleVerify = async () => {
    const code = codeDigits.join('')
    if (code.length !== 6) {
      setError('Please enter the 6-digit code')
      return
    }

    setError('')
    setIsSubmitting(true)

    // Small delay for UX
    await new Promise(resolve => setTimeout(resolve, 600))

    const success = verifyEmail(email, code)
    setIsSubmitting(false)

    if (success) {
      router.push('/app')
    } else {
      setError('Invalid or expired code. Please try again.')
    }
  }

  const handleResend = () => {
    if (resendTimer > 0) return
    const code = sendVerificationCode(email)
    setGeneratedCode(code)
    setResendTimer(60)
    setCodeDigits(['', '', '', '', '', ''])
    setError('')
  }

  const handleDigitChange = (index: number, value: string) => {
    if (value.length > 1) value = value.slice(-1)
    if (value && !/^\d$/.test(value)) return

    const newDigits = [...codeDigits]
    newDigits[index] = value
    setCodeDigits(newDigits)

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus()
    }

    // Auto-submit when all digits are filled
    if (newDigits.every(d => d !== '') && newDigits.join('').length === 6) {
      setTimeout(() => handleVerify(), 200)
    }
  }

  const handleDigitKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !codeDigits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handleDigitPaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (pasted.length === 6) {
      const digits = pasted.split('')
      setCodeDigits(digits)
      inputRefs.current[5]?.focus()
      setTimeout(() => {
        const code = digits.join('')
        if (code.length === 6) handleVerify()
      }, 300)
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
        setError(`Failed to sign up with ${provider === 'google' ? 'Google' : 'GitHub'}`)
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
    <div className="min-h-screen bg-background flex items-center justify-center relative overflow-hidden py-8">
      {/* Background effects */}
      <div className="orb orb-primary w-[400px] h-[400px] -top-32 -left-32 animate-float opacity-60" />
      <div className="orb orb-secondary w-[300px] h-[300px] bottom-8 -right-32 animate-float opacity-40" style={{ animationDelay: '1.5s' }} />

      <div className="relative z-10 w-full max-w-sm mx-auto px-5">
        {/* Logo */}
        <div className="text-center mb-6 animate-fadeInUp">
          <Link href="/" className="inline-flex flex-col items-center gap-2 group">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-xl shadow-[hsl(73,31%,45%)]/25 group-hover:shadow-[hsl(73,31%,45%)]/40 transition-shadow duration-300">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-gradient">Lumina</span>
          </Link>
        </div>

        {/* Card */}
        <div className="bg-card/60 border border-border/30 rounded-2xl p-6 backdrop-blur-xl shadow-2xl animate-fadeInUp" style={{ animationDelay: '0.1s' }}>

          {step === 'form' ? (
            <>
              <div className="text-center mb-5">
                <h1 className="text-xl font-bold mb-1">Create your account</h1>
                <p className="text-xs text-muted-foreground">Start learning smarter with Lumina</p>
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
                  <span className="px-3 bg-card/60 text-muted-foreground/60 backdrop-blur-sm">or sign up with email</span>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-3">
                {error && (
                  <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs animate-fadeIn">
                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                    {error}
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground/70">Full Name</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/50" />
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full pl-9 pr-3 py-2.5 rounded-lg bg-muted/30 border border-border/30 text-sm placeholder:text-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-[hsl(73,31%,45%)]/30 focus:border-[hsl(73,31%,45%)]/50 transition-all"
                      placeholder="John Doe"
                    />
                  </div>
                </div>

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
                  <label className="text-xs font-medium text-foreground/70">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/50" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full pl-9 pr-10 py-2.5 rounded-lg bg-muted/30 border border-border/30 text-sm placeholder:text-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-[hsl(73,31%,45%)]/30 focus:border-[hsl(73,31%,45%)]/50 transition-all"
                      placeholder="Create a password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-foreground transition-colors"
                    >
                      {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  {/* Password requirements — inline */}
                  {password.length > 0 && (
                    <div className="flex items-center gap-3 mt-1.5 animate-fadeIn">
                      {passwordChecks.map((check, i) => (
                        <div key={i} className="flex items-center gap-1">
                          <CheckCircle2 className={`w-3 h-3 ${check.valid ? 'text-[hsl(73,31%,55%)]' : 'text-muted-foreground/25'}`} />
                          <span className={`text-[10px] ${check.valid ? 'text-[hsl(73,31%,55%)]' : 'text-muted-foreground/40'}`}>{check.label}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground/70">Confirm Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/50" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className={`w-full pl-9 pr-3 py-2.5 rounded-lg bg-muted/30 border text-sm placeholder:text-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-[hsl(73,31%,45%)]/30 focus:border-[hsl(73,31%,45%)]/50 transition-all ${
                        confirmPassword && confirmPassword !== password
                          ? 'border-destructive/50'
                          : confirmPassword && confirmPassword === password
                          ? 'border-[hsl(73,31%,45%)]/50'
                          : 'border-border/30'
                      }`}
                      placeholder="Confirm your password"
                    />
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
                      Continue
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </form>

              <p className="mt-4 text-center text-[11px] text-muted-foreground/50">
                By signing up, you agree to our{' '}
                <span className="underline cursor-pointer hover:text-foreground/60">Terms</span> and{' '}
                <span className="underline cursor-pointer hover:text-foreground/60">Privacy Policy</span>
              </p>

              <p className="mt-3 text-center text-xs text-muted-foreground">
                Already have an account?{' '}
                <Link href="/login" className="font-semibold text-[hsl(73,31%,55%)] hover:text-[hsl(73,31%,65%)] transition-colors">
                  Sign in
                </Link>
              </p>
            </>
          ) : (
            /* Email Verification Step */
            <div className="animate-fadeIn">
              <div className="text-center mb-6">
                <div className="w-14 h-14 rounded-2xl bg-[hsl(73,31%,45%)]/10 border border-[hsl(73,31%,45%)]/20 flex items-center justify-center mx-auto mb-4">
                  <ShieldCheck className="w-7 h-7 text-[hsl(73,31%,55%)]" />
                </div>
                <h1 className="text-xl font-bold mb-1">Verify your email</h1>
                <p className="text-xs text-muted-foreground">
                  We sent a 6-digit code to <span className="font-medium text-foreground/80">{email}</span>
                </p>
              </div>

              {/* Show code hint (since this is simulated) */}
              <div className="mb-5 px-3 py-2.5 rounded-lg bg-[hsl(73,31%,45%)]/8 border border-[hsl(73,31%,45%)]/15 text-center">
                <p className="text-[10px] text-muted-foreground/60 mb-0.5">Demo verification code</p>
                <p className="text-lg font-mono font-bold text-[hsl(73,31%,55%)] tracking-[0.3em]">{generatedCode}</p>
              </div>

              {error && (
                <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs animate-fadeIn mb-4">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                  {error}
                </div>
              )}

              {/* 6-digit code input */}
              <div className="flex justify-center gap-2 mb-5" onPaste={handleDigitPaste}>
                {codeDigits.map((digit, i) => (
                  <input
                    key={i}
                    ref={(el) => { inputRefs.current[i] = el }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleDigitChange(i, e.target.value)}
                    onKeyDown={(e) => handleDigitKeyDown(i, e)}
                    className="w-11 h-12 text-center text-lg font-semibold rounded-lg bg-muted/30 border border-border/40 text-foreground focus:outline-none focus:ring-2 focus:ring-[hsl(73,31%,45%)]/40 focus:border-[hsl(73,31%,45%)]/60 transition-all"
                    autoFocus={i === 0}
                  />
                ))}
              </div>

              <button
                onClick={handleVerify}
                disabled={isSubmitting || codeDigits.some(d => !d)}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,55%)] text-white text-sm font-semibold rounded-lg hover:shadow-lg hover:shadow-[hsl(73,31%,45%)]/25 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    Verify & Continue
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>

              <div className="flex items-center justify-between mt-4">
                <button
                  onClick={() => { setStep('form'); setError('') }}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ArrowLeft className="w-3 h-3" />
                  Back
                </button>
                <button
                  onClick={handleResend}
                  disabled={resendTimer > 0}
                  className="text-xs text-[hsl(73,31%,55%)] hover:text-[hsl(73,31%,65%)] disabled:text-muted-foreground/40 disabled:cursor-not-allowed transition-colors"
                >
                  {resendTimer > 0 ? `Resend in ${resendTimer}s` : 'Resend code'}
                </button>
              </div>
            </div>
          )}
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
