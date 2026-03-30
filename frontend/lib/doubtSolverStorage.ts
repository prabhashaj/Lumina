import { DoubtMessage, DoubtSolverSession } from './types'

const STORAGE_KEY = 'lumina-doubt-solver-sessions'

export function loadDoubtSolverSessions(): DoubtSolverSession[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const sessions: DoubtSolverSession[] = JSON.parse(raw)
    return sessions.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
  } catch {
    return []
  }
}

function saveSessions(sessions: DoubtSolverSession[]): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch (e) {
    console.error('Failed to save doubt solver sessions:', e)
  }
}

export function createDoubtSolverSession(): DoubtSolverSession {
  const now = new Date().toISOString()
  return {
    id: Date.now().toString() + Math.random().toString(36).slice(2, 6),
    title: 'New Doubt Chat',
    messages: [],
    createdAt: now,
    updatedAt: now,
  }
}

export function saveDoubtSolverSession(session: DoubtSolverSession): void {
  const sessions = loadDoubtSolverSessions()
  const idx = sessions.findIndex((s) => s.id === session.id)

  if (session.title === 'New Doubt Chat' && session.messages.length > 0) {
    const firstUser = session.messages.find((m) => m.role === 'user')
    if (firstUser) {
      session.title = firstUser.content.slice(0, 60) + (firstUser.content.length > 60 ? '...' : '')
    }
  }

  session.updatedAt = new Date().toISOString()

  if (idx >= 0) {
    sessions[idx] = session
  } else {
    sessions.unshift(session)
  }

  saveSessions(sessions)
}

export function deleteDoubtSolverSession(sessionId: string): void {
  const sessions = loadDoubtSolverSessions().filter((s) => s.id !== sessionId)
  saveSessions(sessions)
}

export function serializeDoubtMessages(messages: DoubtMessage[]): DoubtMessage[] {
  return messages.map((m) => ({
    ...m,
    timestamp: m.timestamp instanceof Date ? m.timestamp : new Date(m.timestamp),
  }))
}