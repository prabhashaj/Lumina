import { ExamPrepSession, Chapter, Topic } from './types'

const STORAGE_KEY = 'lumina-exam-prep-sessions'

export function loadExamPrepSessions(): ExamPrepSession[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const sessions: ExamPrepSession[] = JSON.parse(raw)
    return sessions.sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
  } catch {
    return []
  }
}

function saveSessions(sessions: ExamPrepSession[]): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch (e) {
    console.error('Failed to save exam prep sessions:', e)
  }
}

export function saveExamPrepSession(session: ExamPrepSession): void {
  const sessions = loadExamPrepSessions()
  const idx = sessions.findIndex((s) => s.id === session.id)

  session.updatedAt = new Date().toISOString()
  session.overallProgress = calculateProgress(session.chapters)

  if (idx >= 0) {
    sessions[idx] = session
  } else {
    sessions.unshift(session)
  }

  saveSessions(sessions)
}

export function deleteExamPrepSession(sessionId: string): void {
  const sessions = loadExamPrepSessions().filter((s) => s.id !== sessionId)
  saveSessions(sessions)
}

export function createExamPrepSession(
  subject: string,
  chaptersData: { title: string; description: string; topics: string[] }[]
): ExamPrepSession {
  const now = new Date().toISOString()

  const chapters: Chapter[] = chaptersData.map((ch, chIdx) => ({
    id: `ch_${chIdx}`,
    title: ch.title,
    description: ch.description,
    order: chIdx,
    topics: ch.topics.map((topicTitle, tIdx) => ({
      id: `ch${chIdx}_t${tIdx}`,
      title: topicTitle,
      status: chIdx === 0 && tIdx === 0 ? 'available' : 'locked',
    })),
  }))

  return {
    id: Date.now().toString() + Math.random().toString(36).slice(2, 6),
    subject,
    chapters,
    createdAt: now,
    updatedAt: now,
    overallProgress: 0,
  }
}

export function calculateProgress(chapters: Chapter[]): number {
  let total = 0
  let done = 0
  for (const ch of chapters) {
    for (const t of ch.topics) {
      total++
      if (t.status === 'quiz-done') done++
    }
  }
  return total === 0 ? 0 : Math.round((done / total) * 100)
}

// Unlock the next topic after completing a quiz
export function unlockNextTopic(chapters: Chapter[], chapterIdx: number, topicIdx: number): Chapter[] {
  const updated = chapters.map((ch) => ({
    ...ch,
    topics: ch.topics.map((t) => ({ ...t })),
  }))

  const currentChapter = updated[chapterIdx]
  if (!currentChapter) return updated

  // Try next topic in same chapter
  if (topicIdx + 1 < currentChapter.topics.length) {
    if (currentChapter.topics[topicIdx + 1].status === 'locked') {
      currentChapter.topics[topicIdx + 1].status = 'available'
    }
  } else {
    // Move to next chapter's first topic
    if (chapterIdx + 1 < updated.length) {
      const nextChapter = updated[chapterIdx + 1]
      if (nextChapter.topics.length > 0 && nextChapter.topics[0].status === 'locked') {
        nextChapter.topics[0].status = 'available'
      }
    }
  }

  return updated
}
