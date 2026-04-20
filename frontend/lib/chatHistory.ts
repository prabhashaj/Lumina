import { ChatSession, UnifiedHistoryItem } from './types'
import { loadExamPrepSessions } from './examPrepStorage'
import { loadPersonalizedSessions } from './personalizedStorage'
import { loadDoubtSolverSessions } from './doubtSolverStorage'
import { loadVideoLectureSessions } from './videoLectureStorage'

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
export function groupSessionsByDate<T extends { updatedAt: string }>(sessions: T[]): { label: string; sessions: T[] }[] {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const last7 = new Date(today.getTime() - 7 * 86400000)
  const last30 = new Date(today.getTime() - 30 * 86400000)

  const groups: Record<string, T[]> = {
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

export function loadUnifiedHistoryItems(): UnifiedHistoryItem[] {
  const chatItems: UnifiedHistoryItem[] = loadChatSessions().map((s) => ({
    id: `chat:${s.id}`,
    mode: 'chat',
    sessionId: s.id,
    title: s.title,
    subtitle: 'Research',
    createdAt: s.createdAt,
    updatedAt: s.updatedAt,
  }))

  const examPrepItems: UnifiedHistoryItem[] = loadExamPrepSessions().map((s) => ({
    id: `exam-prep:${s.id}`,
    mode: 'exam-prep',
    sessionId: s.id,
    title: s.subject,
    subtitle: `${s.chapters.length} chapters • ${s.overallProgress}% complete`,
    createdAt: s.createdAt,
    updatedAt: s.updatedAt,
  }))

  const personalizedItems: UnifiedHistoryItem[] = loadPersonalizedSessions().map((s) => ({
    id: `personalized:${s.id}`,
    mode: 'personalized',
    sessionId: s.id,
    title: s.subject,
    subtitle: `${s.profile.knowledgeLevel} • ${s.overallProgress}% complete`,
    createdAt: s.createdAt,
    updatedAt: s.updatedAt,
  }))

  const videoItems: UnifiedHistoryItem[] = loadVideoLectureSessions().map((s) => ({
    id: `video-lecture:${s.id}`,
    mode: 'video-lecture',
    sessionId: s.id,
    title: s.title || s.topic || 'Video Lecture',
    subtitle: s.presentation ? `${s.presentation.total_slides} slides` : 'Draft lecture',
    createdAt: s.createdAt,
    updatedAt: s.updatedAt,
  }))

  const doubtItems: UnifiedHistoryItem[] = loadDoubtSolverSessions().map((s) => ({
    id: `doubt-solver:${s.id}`,
    mode: 'doubt-solver',
    sessionId: s.id,
    title: s.title,
    subtitle: `${s.messages.length} messages`,
    createdAt: s.createdAt,
    updatedAt: s.updatedAt,
  }))

  return [...chatItems, ...examPrepItems, ...personalizedItems, ...videoItems, ...doubtItems].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  )
}
