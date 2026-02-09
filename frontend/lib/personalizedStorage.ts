import { PersonalizedSession, LearningPhase, PlanTopic } from './types'

const STORAGE_KEY = 'lumina-personalized-sessions'

export function loadPersonalizedSessions(): PersonalizedSession[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const sessions: PersonalizedSession[] = JSON.parse(raw)
    return sessions.sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
  } catch {
    return []
  }
}

function saveSessions(sessions: PersonalizedSession[]): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch (e) {
    console.error('Failed to save personalized sessions:', e)
  }
}

export function savePersonalizedSession(session: PersonalizedSession): void {
  const sessions = loadPersonalizedSessions()
  const idx = sessions.findIndex((s) => s.id === session.id)

  session.updatedAt = new Date().toISOString()
  session.overallProgress = calculatePersonalizedProgress(session.profile.learningPlan)

  if (idx >= 0) {
    sessions[idx] = session
  } else {
    sessions.unshift(session)
  }

  saveSessions(sessions)
}

export function deletePersonalizedSession(sessionId: string): void {
  const sessions = loadPersonalizedSessions().filter((s) => s.id !== sessionId)
  saveSessions(sessions)
}

export function calculatePersonalizedProgress(phases: LearningPhase[]): number {
  let total = 0
  let done = 0
  for (const phase of phases) {
    for (const t of phase.topics) {
      total++
      if (t.status === 'completed') done++
    }
  }
  return total === 0 ? 0 : Math.round((done / total) * 100)
}

export function markTopicStatus(
  phases: LearningPhase[],
  phaseIdx: number,
  topicIdx: number,
  status: 'not-started' | 'in-progress' | 'completed'
): LearningPhase[] {
  return phases.map((phase, pi) => ({
    ...phase,
    topics: phase.topics.map((t, ti) => ({
      ...t,
      status: pi === phaseIdx && ti === topicIdx ? status : t.status,
    })),
  }))
}
