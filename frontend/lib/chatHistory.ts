import { ChatSession, Message } from './types'

const STORAGE_KEY = 'ai-research-chat-history'

// Load all chat sessions from localStorage
export function loadChatSessions(): ChatSession[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const sessions: ChatSession[] = JSON.parse(raw)
    // Sort by most recently updated
    return sessions.sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
  } catch {
    return []
  }
}

// Save all sessions to localStorage
function saveSessions(sessions: ChatSession[]): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch (e) {
    console.error('Failed to save chat history:', e)
  }
}

// Create a new chat session
export function createChatSession(): ChatSession {
  const now = new Date().toISOString()
  return {
    id: Date.now().toString() + Math.random().toString(36).slice(2, 6),
    title: 'New Chat',
    messages: [],
    createdAt: now,
    updatedAt: now,
  }
}

// Save or update a single chat session
export function saveChatSession(session: ChatSession): void {
  const sessions = loadChatSessions()
  const idx = sessions.findIndex((s) => s.id === session.id)

  // Auto-generate title from first user message
  if (session.title === 'New Chat' && session.messages.length > 0) {
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

// Delete a chat session
export function deleteChatSession(sessionId: string): void {
  const sessions = loadChatSessions().filter((s) => s.id !== sessionId)
  saveSessions(sessions)
}

// Group sessions by relative date
export function groupSessionsByDate(sessions: ChatSession[]): { label: string; sessions: ChatSession[] }[] {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const last7 = new Date(today.getTime() - 7 * 86400000)
  const last30 = new Date(today.getTime() - 30 * 86400000)

  const groups: Record<string, ChatSession[]> = {
    Today: [],
    Yesterday: [],
    'Previous 7 Days': [],
    'Previous 30 Days': [],
    Older: [],
  }

  for (const s of sessions) {
    const d = new Date(s.updatedAt)
    if (d >= today) groups['Today'].push(s)
    else if (d >= yesterday) groups['Yesterday'].push(s)
    else if (d >= last7) groups['Previous 7 Days'].push(s)
    else if (d >= last30) groups['Previous 30 Days'].push(s)
    else groups['Older'].push(s)
  }

  return Object.entries(groups)
    .filter(([, list]) => list.length > 0)
    .map(([label, sessions]) => ({ label, sessions }))
}
