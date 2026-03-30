import { Presentation, VideoLectureHistorySession } from './types'

const STORAGE_KEY = 'lumina-video-lecture-sessions'

function stripAudioPayload(presentation: Presentation | null): Presentation | null {
  if (!presentation) return null
  return {
    ...presentation,
    slides: presentation.slides.map((slide) => {
      const { audio_base64, ...rest } = slide
      return rest
    }),
  }
}

export function loadVideoLectureSessions(): VideoLectureHistorySession[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const sessions: VideoLectureHistorySession[] = JSON.parse(raw)
    return sessions.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
  } catch {
    return []
  }
}

function saveSessions(sessions: VideoLectureHistorySession[]): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch (e) {
    console.error('Failed to save video lecture sessions:', e)
  }
}

export function createVideoLectureSession(topic: string): VideoLectureHistorySession {
  const now = new Date().toISOString()
  return {
    id: Date.now().toString() + Math.random().toString(36).slice(2, 6),
    topic,
    title: topic,
    presentation: null,
    createdAt: now,
    updatedAt: now,
    status: 'idle',
  }
}

export function saveVideoLectureSession(session: VideoLectureHistorySession): void {
  const sessions = loadVideoLectureSessions()
  const idx = sessions.findIndex((s) => s.id === session.id)

  session.updatedAt = new Date().toISOString()
  session.title = session.presentation?.title || session.topic || 'Video Lecture'
  session.presentation = stripAudioPayload(session.presentation)

  if (idx >= 0) {
    sessions[idx] = session
  } else {
    sessions.unshift(session)
  }

  saveSessions(sessions)
}

export function deleteVideoLectureSession(sessionId: string): void {
  const sessions = loadVideoLectureSessions().filter((s) => s.id !== sessionId)
  saveSessions(sessions)
}