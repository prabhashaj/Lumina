'use client'

import { useState, useCallback } from 'react'
import {
  PersonalizedSession,
  LearnerProfile,
  AssessmentQuestion,
  PlanTopic,
  LearningPhase,
  TopicContent,
} from '@/lib/types'
import { generateAssessment, analyzeLearnerProfile } from '@/lib/api'
import {
  loadPersonalizedSessions,
  savePersonalizedSession,
  deletePersonalizedSession,
  markTopicStatus,
} from '@/lib/personalizedStorage'
import AssessmentView from './AssessmentView'
import LearningPlanView from './LearningPlanView'
import PersonalizedContentView from './PersonalizedContentView'
import {
  Brain,
  Loader2,
  Search,
  Trash2,
  ArrowLeft,
  AlertTriangle,
  Sparkles,
  User,
} from 'lucide-react'

type PersonalizedView = 'landing' | 'assessing' | 'assessment' | 'analyzing' | 'plan' | 'content'

export default function PersonalizedMode() {
  const [view, setView] = useState<PersonalizedView>('landing')
  const [session, setSession] = useState<PersonalizedSession | null>(null)
  const [savedSessions, setSavedSessions] = useState<PersonalizedSession[]>(() =>
    loadPersonalizedSessions()
  )

  // Assessment state
  const [assessmentQuestions, setAssessmentQuestions] = useState<AssessmentQuestion[]>([])

  // Topic viewing state
  const [activePhaseIdx, setActivePhaseIdx] = useState(0)
  const [activeTopicIdx, setActiveTopicIdx] = useState(0)
  const [activeTopic, setActiveTopic] = useState<PlanTopic | null>(null)
  const [activePhase, setActivePhase] = useState<LearningPhase | null>(null)

  // Input state
  const [subjectInput, setSubjectInput] = useState('')
  const [isCreatingAssessment, setIsCreatingAssessment] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Start assessment for new topic
  const handleStartAssessment = async () => {
    if (!subjectInput.trim() || isCreatingAssessment) return

    setIsCreatingAssessment(true)
    setError(null)
    setView('assessing')

    try {
      const result = await generateAssessment(subjectInput.trim())
      setAssessmentQuestions(result.questions as AssessmentQuestion[])
      setView('assessment')
    } catch (err: any) {
      setError(err.message || 'Failed to generate assessment')
      setView('landing')
    } finally {
      setIsCreatingAssessment(false)
    }
  }

  // Handle assessment completion
  const handleAssessmentComplete = async (answers: number[]) => {
    setView('analyzing')
    setError(null)

    try {
      const profile: LearnerProfile = await analyzeLearnerProfile(
        subjectInput.trim(),
        assessmentQuestions,
        answers
      )

      // Initialize topic statuses
      profile.learningPlan = profile.learningPlan.map((phase) => ({
        ...phase,
        topics: phase.topics.map((t) => ({
          ...t,
          status: t.status || 'not-started',
        })),
      }))

      const newSession: PersonalizedSession = {
        id: Date.now().toString() + Math.random().toString(36).slice(2, 6),
        subject: subjectInput.trim(),
        profile,
        assessmentQuestions,
        assessmentAnswers: answers,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        overallProgress: 0,
      }

      savePersonalizedSession(newSession)
      setSession(newSession)
      setSavedSessions(loadPersonalizedSessions())
      setView('plan')
    } catch (err: any) {
      setError(err.message || 'Failed to analyze profile')
      setView('landing')
    }
  }

  // Select a topic from learning plan
  const handleSelectTopic = (
    phaseIdx: number,
    topicIdx: number,
    topic: PlanTopic,
    phase: LearningPhase
  ) => {
    setActivePhaseIdx(phaseIdx)
    setActiveTopicIdx(topicIdx)
    setActiveTopic(topic)
    setActivePhase(phase)

    // Mark as in-progress
    if (session && topic.status !== 'completed') {
      const updatedPlan = markTopicStatus(
        session.profile.learningPlan,
        phaseIdx,
        topicIdx,
        'in-progress'
      )
      const updatedSession = {
        ...session,
        profile: { ...session.profile, learningPlan: updatedPlan },
      }
      setSession(updatedSession)
      savePersonalizedSession(updatedSession)
      setSavedSessions(loadPersonalizedSessions())
    }

    setView('content')
  }

  // Mark topic complete
  const handleMarkComplete = () => {
    if (!session) return

    const updatedPlan = markTopicStatus(
      session.profile.learningPlan,
      activePhaseIdx,
      activeTopicIdx,
      'completed'
    )
    const updatedSession = {
      ...session,
      profile: { ...session.profile, learningPlan: updatedPlan },
    }
    setSession(updatedSession)
    savePersonalizedSession(updatedSession)
    setSavedSessions(loadPersonalizedSessions())
    setView('plan')
  }

  // Resume existing session
  const handleResumeSession = (s: PersonalizedSession) => {
    setSession(s)
    setSubjectInput(s.subject)
    setView('plan')
  }

  // Delete session
  const handleDeleteSession = (id: string) => {
    deletePersonalizedSession(id)
    setSavedSessions(loadPersonalizedSessions())
    if (session?.id === id) {
      setSession(null)
      setView('landing')
    }
  }

  // Go back to plan
  const handleBackToPlan = () => {
    setView('plan')
  }

  // ── Render ──────────────────────────────

  // Content view
  if (view === 'content' && session && activeTopic && activePhase) {
    return (
      <PersonalizedContentView
        subject={session.subject}
        topic={activeTopic}
        phase={activePhase}
        profile={session.profile}
        onBack={handleBackToPlan}
        onMarkComplete={handleMarkComplete}
      />
    )
  }

  // Assessment view
  if (view === 'assessment' && assessmentQuestions.length > 0) {
    return (
      <AssessmentView
        topic={subjectInput.trim()}
        questions={assessmentQuestions}
        onComplete={handleAssessmentComplete}
      />
    )
  }

  // Learning plan view
  if (view === 'plan' && session) {
    return (
      <LearningPlanView
        subject={session.subject}
        profile={session.profile}
        onSelectTopic={handleSelectTopic}
        onBack={() => {
          setView('landing')
          setSavedSessions(loadPersonalizedSessions())
        }}
      />
    )
  }

  // Loading: generating assessment
  if (view === 'assessing') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 relative">
        <div className="orb orb-primary w-[200px] h-[200px] top-[20%] right-[15%] animate-float" />
        <div className="relative animate-fadeIn">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-xl shadow-[hsl(73,31%,45%)]/20">
            <Loader2 className="w-7 h-7 text-white animate-spin" />
          </div>
          <div className="absolute -inset-3 rounded-[28px] bg-[hsl(73,31%,45%)]/8 animate-pulse-glow" />
        </div>
        <div className="text-center animate-fadeIn" style={{ animationDelay: '100ms' }}>
          <p className="text-foreground/80 font-medium text-sm">Creating your assessment...</p>
          <p className="text-xs text-muted-foreground mt-1">Preparing questions to gauge your knowledge</p>
        </div>
      </div>
    )
  }

  // Loading: analyzing profile
  if (view === 'analyzing') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 relative">
        <div className="orb orb-primary w-[200px] h-[200px] bottom-[20%] left-[10%] animate-float" />
        <div className="relative animate-fadeIn">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-xl shadow-[hsl(73,31%,45%)]/20">
            <Brain className="w-7 h-7 text-white animate-pulse" />
          </div>
          <div className="absolute -inset-3 rounded-[28px] bg-[hsl(73,31%,45%)]/8 animate-pulse-glow" />
        </div>
        <div className="text-center animate-fadeIn" style={{ animationDelay: '100ms' }}>
          <p className="text-foreground/80 font-medium text-sm">Analyzing your knowledge profile...</p>
          <p className="text-xs text-muted-foreground mt-1">Building a personalized learning plan just for you</p>
        </div>
      </div>
    )
  }

  // ── Landing View ──
  return (
    <div className="flex-1 overflow-y-auto relative">
      {/* Ambient orbs */}
      <div className="orb orb-primary w-[250px] h-[250px] top-[5%] right-[10%] animate-float" />
      <div className="orb orb-secondary w-[180px] h-[180px] bottom-[15%] left-[5%] animate-float" style={{ animationDelay: '1.5s' }} />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12 relative z-10">
        {/* Hero */}
        <div className="text-center mb-10 animate-fadeIn">
          <div className="relative inline-block mb-5">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-xl shadow-[hsl(73,31%,45%)]/20 animate-float">
              <User className="w-9 h-9 text-white" />
            </div>
            <div className="absolute -inset-3 rounded-[28px] bg-[hsl(73,31%,45%)]/8 animate-pulse-glow" />
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            Personalized <span className="text-gradient">Learning</span>
          </h1>
          <p className="text-muted-foreground mt-3 max-w-md mx-auto leading-relaxed">
            We assess your knowledge, identify gaps, and create a learning journey tailored to your level and style
          </p>
        </div>

        {/* Feature pills */}
        <div className="flex items-center justify-center gap-2 mb-8 flex-wrap animate-fadeIn" style={{ animationDelay: '150ms' }}>
          {[
            { icon: '🎯', label: 'Adaptive Assessment' },
            { icon: '🧠', label: 'Knowledge Profiling' },
            { icon: '✨', label: 'Style-Matched Content' },
            { icon: '📈', label: 'Progress Tracking' },
          ].map((f) => (
            <span key={f.label} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-card/60 border border-border/40 text-[11px] text-muted-foreground">
              <span>{f.icon}</span> {f.label}
            </span>
          ))}
        </div>

        {/* Subject input */}
        <div className="bg-card/60 rounded-2xl border border-border/40 p-6 mb-8 animate-fadeIn shadow-lg shadow-black/5" style={{ animationDelay: '200ms' }}>
          <label className="text-sm font-semibold text-foreground mb-3 block">
            What topic would you like to learn?
          </label>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleStartAssessment()
            }}
            className="flex gap-3"
          >
            <div className="flex-1 relative">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
              <input
                type="text"
                value={subjectInput}
                onChange={(e) => setSubjectInput(e.target.value)}
                placeholder="e.g., Machine Learning, Organic Chemistry, Data Structures..."
                className="w-full pl-10 pr-4 py-3 rounded-xl bg-background/60 border border-border/50 focus:border-[hsl(73,31%,45%)] focus:ring-2 focus:ring-[hsl(73,31%,45%)]/20 text-sm text-foreground placeholder:text-muted-foreground/40 outline-none transition-all duration-200"
                disabled={isCreatingAssessment}
              />
            </div>
            <button
              type="submit"
              disabled={!subjectInput.trim() || isCreatingAssessment}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white font-semibold text-sm hover:shadow-lg hover:shadow-[hsl(73,31%,45%)]/25 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none transition-all duration-300 flex items-center gap-2"
            >
              {isCreatingAssessment ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Start
                </>
              )}
            </button>
          </form>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 rounded-2xl px-6 py-6 border border-red-500/30 mb-6 animate-fadeIn">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-red-400 mb-1">Something went wrong</h3>
                <p className="text-sm text-foreground/70">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Saved sessions */}
        {savedSessions.length > 0 && (
          <div className="animate-fadeIn" style={{ animationDelay: '300ms' }}>
            <h2 className="text-xs font-bold text-muted-foreground/70 uppercase tracking-wider mb-3 px-1">
              Continue Learning
            </h2>
            <div className="space-y-2 stagger-children">
              {savedSessions.map((s) => {
                const levelIcon = s.profile.knowledgeLevel === 'advanced' ? '🌳' : s.profile.knowledgeLevel === 'intermediate' ? '🌿' : '🌱'
                return (
                  <div
                    key={s.id}
                    className="flex items-center gap-4 bg-card/50 rounded-2xl border border-border/30 p-4 hover:bg-card hover:border-[hsl(73,31%,45%)]/20 hover:shadow-lg hover:shadow-black/5 transition-all duration-300 cursor-pointer group"
                    onClick={() => handleResumeSession(s)}
                  >
                    <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[hsl(73,31%,45%)]/15 to-[hsl(73,31%,45%)]/5 flex items-center justify-center group-hover:from-[hsl(73,31%,45%)]/25 group-hover:to-[hsl(73,31%,45%)]/10 transition-all duration-300">
                      <User className="w-5 h-5 text-[hsl(73,31%,45%)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold text-foreground truncate group-hover:text-[hsl(73,31%,45%)] transition-colors">{s.subject}</h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {levelIcon} {s.profile.knowledgeLevel} &middot; {s.profile.recommendedStyle} style &middot; {s.overallProgress}% complete
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {/* Progress ring */}
                      <div className="relative w-10 h-10">
                        <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
                          <circle cx="18" cy="18" r="15" fill="none" stroke="hsl(0 0% 20%)" strokeWidth="2.5" />
                          <circle
                            cx="18" cy="18" r="15"
                            fill="none"
                            stroke="hsl(73 31% 45%)"
                            strokeWidth="2.5"
                            strokeDasharray={`${s.overallProgress * 0.942} 94.2`}
                            strokeLinecap="round"
                            className="transition-all duration-500"
                          />
                        </svg>
                        <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-[hsl(73,31%,45%)]">
                          {s.overallProgress}%
                        </span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteSession(s.id)
                        }}
                        className="p-2 rounded-xl opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all duration-200"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
