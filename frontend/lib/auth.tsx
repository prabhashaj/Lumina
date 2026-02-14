'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface User {
  id: string
  name: string
  email: string
  avatar?: string
  provider?: 'email' | 'google' | 'github'
  createdAt: string
}

function generateId(): string {
  return (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : (Math.random().toString(36).substring(2) + Date.now().toString(36))
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<boolean>
  signup: (name: string, email: string, password: string) => Promise<{ success: boolean; error?: string }>
  loginWithProvider: (provider: 'google' | 'github') => Promise<boolean>
  sendVerificationCode: (email: string) => string
  verifyEmail: (email: string, code: string) => boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('lumina_user')
    if (stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        localStorage.removeItem('lumina_user')
      }
    }
    setIsLoading(false)
  }, [])

  const login = async (email: string, password: string): Promise<boolean> => {
    const users = JSON.parse(localStorage.getItem('lumina_users') || '[]')
    const found = users.find((u: any) => u.email === email && u.password === password)
    if (found) {
      if (!found.verified) {
        return false
      }
      const userData: User = {
        id: found.id,
        name: found.name,
        email: found.email,
        avatar: found.avatar,
        provider: found.provider || 'email',
        createdAt: found.createdAt,
      }
      setUser(userData)
      localStorage.setItem('lumina_user', JSON.stringify(userData))
      return true
    }
    return false
  }

  const signup = async (name: string, email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    const users = JSON.parse(localStorage.getItem('lumina_users') || '[]')
    if (users.find((u: any) => u.email === email && u.verified)) {
      return { success: false, error: 'An account with this email already exists.' }
    }
    // Remove any unverified entry for same email
    const filtered = users.filter((u: any) => u.email !== email)
    const newUser = {
      id: generateId(),
      name,
      email,
      password,
      provider: 'email',
      verified: false,
      createdAt: new Date().toISOString(),
    }
    filtered.push(newUser)
    localStorage.setItem('lumina_users', JSON.stringify(filtered))
    return { success: true }
  }

  const sendVerificationCode = (email: string): string => {
    const code = Math.floor(100000 + Math.random() * 900000).toString()
    const pending = JSON.parse(localStorage.getItem('lumina_verification') || '{}')
    pending[email] = { code, expiresAt: Date.now() + 10 * 60 * 1000 } // 10 min
    localStorage.setItem('lumina_verification', JSON.stringify(pending))
    return code
  }

  const verifyEmail = (email: string, code: string): boolean => {
    const pending = JSON.parse(localStorage.getItem('lumina_verification') || '{}')
    const entry = pending[email]
    if (!entry || entry.code !== code || Date.now() > entry.expiresAt) {
      return false
    }
    // Mark user as verified
    const users = JSON.parse(localStorage.getItem('lumina_users') || '[]')
    const userIdx = users.findIndex((u: any) => u.email === email)
    if (userIdx === -1) return false
    users[userIdx].verified = true
    localStorage.setItem('lumina_users', JSON.stringify(users))

    // Log the user in
    const found = users[userIdx]
    const userData: User = {
      id: found.id,
      name: found.name,
      email: found.email,
      provider: 'email',
      createdAt: found.createdAt,
    }
    setUser(userData)
    localStorage.setItem('lumina_user', JSON.stringify(userData))

    // Clean up verification code
    delete pending[email]
    localStorage.setItem('lumina_verification', JSON.stringify(pending))
    return true
  }

  const loginWithProvider = async (provider: 'google' | 'github'): Promise<boolean> => {
    // Simulate OAuth flow with a delay
    await new Promise(resolve => setTimeout(resolve, 1200))

    const mockProfiles: Record<string, { name: string; email: string; avatar: string }> = {
      google: {
        name: 'Lumina User',
        email: `user.${Date.now()}@gmail.com`,
        avatar: `https://api.dicebear.com/7.x/initials/svg?seed=LU&backgroundColor=7c8a2e`,
      },
      github: {
        name: 'Lumina Dev',
        email: `dev.${Date.now()}@github.com`,
        avatar: `https://api.dicebear.com/7.x/initials/svg?seed=LD&backgroundColor=24292e`,
      },
    }

    const profile = mockProfiles[provider]
    const users = JSON.parse(localStorage.getItem('lumina_users') || '[]')

    // Check if a user with this provider already exists (by provider type, take the latest)
    const existingIdx = users.findIndex((u: any) => u.provider === provider)
    let userData: User

    if (existingIdx !== -1) {
      const found = users[existingIdx]
      userData = {
        id: found.id,
        name: found.name,
        email: found.email,
        avatar: found.avatar,
        provider,
        createdAt: found.createdAt,
      }
    } else {
      const newUser = {
        id: generateId(),
        name: profile.name,
        email: profile.email,
        avatar: profile.avatar,
        password: '',
        provider,
        verified: true,
        createdAt: new Date().toISOString(),
      }
      users.push(newUser)
      localStorage.setItem('lumina_users', JSON.stringify(users))
      userData = {
        id: newUser.id,
        name: newUser.name,
        email: newUser.email,
        avatar: newUser.avatar,
        provider,
        createdAt: newUser.createdAt,
      }
    }

    setUser(userData)
    localStorage.setItem('lumina_user', JSON.stringify(userData))
    return true
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('lumina_user')
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, signup, loginWithProvider, sendVerificationCode, verifyEmail, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
