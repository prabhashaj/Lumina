'use client'

import { useState, useCallback } from 'react'
import { ExamPrepSession, TopicContent, QuizQuestion, Chapter } from '@/lib/types'
import { generateRoadmap, streamTopicContent, generateQuiz } from '@/lib/api'
import {
  createExamPrepSession,
  saveExamPrepSession,
  loadExamPrepSessions,
  deleteExamPrepSession,
  unlockNextTopic,
} from '@/lib/examPrepStorage'
import RoadmapView from './RoadmapView'
import TopicContentView from './TopicContentView'
import QuizView from './QuizView'
import GuideChatbot from '../shared/GuideChatbot'
import {
  GraduationCap,
  Loader2,
  Search,
  Trash2,
  BookOpen,
  ArrowLeft,
  AlertTriangle,
  RefreshCw,
  Sparkles,
} from 'lucide-react'

type PrepView = 'landing' | 'roadmap' | 'topic' | 'quiz'

export default function ExamPrepMode() {
  const [view, setView] = useState<PrepView>('landing')
  const [session, setSession] = useState<ExamPrepSession | null>(null)
  const [savedSessions, setSavedSessions] = useState<ExamPrepSession[]>(() => loadExamPrepSessions())

  // Topic viewing state
  const [activeCh, setActiveCh] = useState(0)
  const [activeTopic, setActiveTopic] = useState(0)
  const [topicContent, setTopicContent] = useState<TopicContent | null>(null)
  const [isGeneratingContent, setIsGeneratingContent] = useState(false)
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([])
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState(false)
  const [contentError, setContentError] = useState<string | null>(null)

  // Subject input
  const [subjectInput, setSubjectInput] = useState('')
  const [isCreatingRoadmap, setIsCreatingRoadmap] = useState(false)

  // Create new exam prep session
  const handleCreateRoadmap = async () => {
    if (!subjectInput.trim() || isCreatingRoadmap) return
    setIsCreatingRoadmap(true)

    try {
      const roadmap = await generateRoadmap(subjectInput.trim())
      const newSession = createExamPrepSession(roadmap.subject || subjectInput.trim(), roadmap.chapters)
      saveExamPrepSession(newSession)
      setSession(newSession)
      setSavedSessions(loadExamPrepSessions())
      setView('roadmap')
      setSubjectInput('')
    } catch (err) {
      console.error('Roadmap generation failed:', err)
      alert('Failed to generate roadmap. Please try again.')
    } finally {
      setIsCreatingRoadmap(false)
    }
  }

  // Load an existing session
  const handleLoadSession = (s: ExamPrepSession) => {
    setSession(s)
    setView('roadmap')
  }

  // Delete a session
  const handleDeleteSession = (id: string) => {
    deleteExamPrepSession(id)
    setSavedSessions(loadExamPrepSessions())
    if (session?.id === id) {
      setSession(null)
      setView('landing')
    }
  }

  // Select a topic from the roadmap
  const handleSelectTopic = useCallback(
    async (chIdx: number, tIdx: number) => {
      if (!session) return
      setActiveCh(chIdx)
      setActiveTopic(tIdx)

      const topic = session.chapters[chIdx].topics[tIdx]

      // If topic already has content, show it
      if (topic.content && (topic.status === 'completed' || topic.status === 'quiz-pending' || topic.status === 'quiz-done')) {
        setTopicContent(topic.content)
        if (topic.status === 'quiz-done') {
          setView('topic') // Just view content
        } else {
          setView('topic')
        }
        return
      }

      // Generate content
      setView('topic')
      setTopicContent(null)
      setIsGeneratingContent(true)
      setContentError(null)

      // Mark as generating
      const updatedChapters = session.chapters.map((ch, ci) => ({
        ...ch,
        topics: ch.topics.map((t, ti) => ({
          ...t,
          status: ci === chIdx && ti === tIdx ? 'generating' as const : t.status,
        })),
      }))
      const updatedSession = { ...session, chapters: updatedChapters }
      setSession(updatedSession)
      saveExamPrepSession(updatedSession)

      try {
        const content: TopicContent = {}

        await streamTopicContent(
          session.subject,
          session.chapters[chIdx].title,
          topic.title,
          (chunk: any) => {
            switch (chunk.type) {
              case 'error':
                setContentError(chunk.data || 'An unknown error occurred during content generation.')
                break
              case 'tldr':
                content.tldr = chunk.data
                setTopicContent({ ...content })
                break
              case 'explanation':
                content.explanation = chunk.data
                setTopicContent({ ...content })
                break
              case 'image':
                content.images = [...(content.images || []), chunk.data]
                setTopicContent({ ...content })
                break
              case 'source':
                content.sources = [...(content.sources || []), chunk.data]
                setTopicContent({ ...content })
                break
              case 'analogy':
                content.analogy = chunk.data
                setTopicContent({ ...content })
                break
              case 'practice_question':
                content.practiceQuestions = [...(content.practiceQuestions || []), chunk.data]
                setTopicContent({ ...content })
                break
              case 'complete':
                // Mark topic as completed (ready for quiz)
                const doneChapters = updatedSession.chapters.map((ch, ci) => ({
                  ...ch,
                  topics: ch.topics.map((t, ti) => ({
                    ...t,
                    ...(ci === chIdx && ti === tIdx
                      ? { status: 'quiz-pending' as const, content: { ...content } }
                      : {}),
                  })),
                }))
                const doneSession = { ...updatedSession, chapters: doneChapters }
                setSession(doneSession)
                saveExamPrepSession(doneSession)
                setSavedSessions(loadExamPrepSessions())
                break
            }
          }
        )
      } catch (err) {
        console.error('Topic content generation failed:', err)
        setContentError('Failed to generate content. Make sure the backend server is running and try again.')
        // Revert topic status back to available
        const revertedChapters = session.chapters.map((ch, ci) => ({
          ...ch,
          topics: ch.topics.map((t, ti) => ({
            ...t,
            status: ci === chIdx && ti === tIdx ? 'available' as const : t.status,
          })),
        }))
        const revertedSession = { ...session, chapters: revertedChapters }
        setSession(revertedSession)
        saveExamPrepSession(revertedSession)
      } finally {
        setIsGeneratingContent(false)
      }
    },
    [session]
  )

  // Take quiz
  const handleTakeQuiz = async () => {
    if (!session) return
    setIsGeneratingQuiz(true)

    try {
      const topic = session.chapters[activeCh].topics[activeTopic]
      const result = await generateQuiz(
        session.subject,
        session.chapters[activeCh].title,
        topic.title
      )
      setQuizQuestions(result.questions)
      setView('quiz')
    } catch (err) {
      console.error('Quiz generation failed:', err)
      alert('Failed to generate quiz. Please try again.')
    } finally {
      setIsGeneratingQuiz(false)
    }
  }

  // Quiz completed
  const handleQuizComplete = (score: number, answers: number[]) => {
    if (!session) return

    let updatedChapters = session.chapters.map((ch, ci) => ({
      ...ch,
      topics: ch.topics.map((t, ti) => ({
        ...t,
        ...(ci === activeCh && ti === activeTopic
          ? { status: 'quiz-done' as const, quizScore: score, quizAnswers: answers, quiz: quizQuestions }
          : {}),
      })),
    }))

    // Unlock next topic if passed (>= 60%)
    if (score >= 60) {
      updatedChapters = unlockNextTopic(updatedChapters, activeCh, activeTopic)
    }

    const updatedSession = { ...session, chapters: updatedChapters }
    setSession(updatedSession)
    saveExamPrepSession(updatedSession)
    setSavedSessions(loadExamPrepSessions())
  }

  // Retry quiz
  const handleRetryQuiz = () => {
    setQuizQuestions([])
    handleTakeQuiz()
  }

  // Back to roadmap
  const handleBackToRoadmap = () => {
    setView('roadmap')
    setTopicContent(null)
    setQuizQuestions([])
  }

  // ── Compute guide context ──
  const guideContext = session
    ? `Subject: ${session.subject}. ${
        view === 'topic' && session.chapters[activeCh]?.topics[activeTopic]
          ? `Currently studying: ${session.chapters[activeCh]?.title} > ${session.chapters[activeCh]?.topics[activeTopic]?.title}`
          : view === 'quiz'
          ? `Taking quiz on: ${session.chapters[activeCh]?.topics[activeTopic]?.title}`
          : `Viewing roadmap with ${session.chapters.length} chapters, ${session.overallProgress}% complete`
      }`
    : 'Student is on the exam prep landing page.'

  // ── Landing View ──
  if (view === 'landing') {
    return (
      <>
      <div className="flex-1 overflow-y-auto relative">
        {/* Ambient orbs */}
        <div className="orb orb-primary w-[250px] h-[250px] top-[5%] right-[10%] animate-float" />
        <div className="orb orb-secondary w-[180px] h-[180px] bottom-[15%] left-[5%] animate-float" style={{ animationDelay: '1.5s' }} />

        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12 relative z-10">
          {/* Hero */}
          <div className="text-center mb-10 animate-fadeIn">
            <div className="relative inline-block mb-5">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-xl shadow-[hsl(73,31%,45%)]/20 animate-float">
                <GraduationCap className="w-9 h-9 text-white" />
              </div>
              <div className="absolute -inset-3 rounded-[28px] bg-[hsl(73,31%,45%)]/8 animate-pulse-glow" />
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
              Exam <span className="text-gradient">Prep</span>
            </h1>
            <p className="text-muted-foreground mt-3 max-w-md mx-auto leading-relaxed">
              Generate a structured study roadmap with AI‑powered content and quizzes
            </p>
          </div>

          {/* Feature pills */}
          <div className="flex items-center justify-center gap-2 mb-8 animate-fadeIn" style={{ animationDelay: '150ms' }}>
            {[
              { icon: '📚', label: 'Structured Chapters' },
              { icon: '🧠', label: 'AI Content' },
              { icon: '✅', label: 'Interactive Quizzes' },
            ].map((f) => (
              <span key={f.label} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-card/60 border border-border/40 text-[11px] text-muted-foreground">
                <span>{f.icon}</span> {f.label}
              </span>
            ))}
          </div>

          {/* Subject input */}
          <div className="bg-card/60 rounded-2xl border border-border/40 p-6 mb-8 animate-fadeIn shadow-lg shadow-black/5" style={{ animationDelay: '200ms' }}>
            <label className="text-sm font-semibold text-foreground mb-3 block">
              What subject do you want to study?
            </label>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleCreateRoadmap()
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
                  disabled={isCreatingRoadmap}
                />
              </div>
              <button
                type="submit"
                disabled={!subjectInput.trim() || isCreatingRoadmap}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white font-semibold text-sm hover:shadow-lg hover:shadow-[hsl(73,31%,45%)]/25 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none transition-all duration-300 flex items-center gap-2"
              >
                {isCreatingRoadmap ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Generate
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Saved sessions */}
          {savedSessions.length > 0 && (
            <div className="animate-fadeIn" style={{ animationDelay: '300ms' }}>
              <h2 className="text-xs font-bold text-muted-foreground/70 uppercase tracking-wider mb-3 px-1">
                Continue Studying
              </h2>
              <div className="space-y-2 stagger-children">
                {savedSessions.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center gap-4 bg-card/50 rounded-2xl border border-border/30 p-4 hover:bg-card hover:border-[hsl(73,31%,45%)]/20 hover:shadow-lg hover:shadow-black/5 transition-all duration-300 cursor-pointer group"
                    onClick={() => handleLoadSession(s)}
                  >
                    <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[hsl(73,31%,45%)]/15 to-[hsl(73,31%,45%)]/5 flex items-center justify-center group-hover:from-[hsl(73,31%,45%)]/25 group-hover:to-[hsl(73,31%,45%)]/10 transition-all duration-300">
                      <BookOpen className="w-5 h-5 text-[hsl(73,31%,45%)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold text-foreground truncate group-hover:text-[hsl(73,31%,45%)] transition-colors">{s.subject}</h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {s.chapters.length} chapters &middot; {s.overallProgress}% complete
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
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      </>
    )
  }

  // ── Roadmap View ──
  if (view === 'roadmap' && session) {
    return (
      <>
      <RoadmapView
        subject={session.subject}
        chapters={session.chapters}
        overallProgress={session.overallProgress}
        onSelectTopic={handleSelectTopic}
        onBack={() => {
          setView('landing')
          setSavedSessions(loadExamPrepSessions())
        }}
      />
      <GuideChatbot mode="exam-prep" context={guideContext} title="Study Guide" />
      </>
    )
  }

  // ── Topic Content View ──
  if (view === 'topic' && session) {
    const topic = session.chapters[activeCh]?.topics[activeTopic]

    return (
      <>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 animate-fadeIn">
          {/* Breadcrumb */}
          <button
            onClick={handleBackToRoadmap}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-5 transition-colors group"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            Back to Roadmap
          </button>

          <div className="mb-6">
            <p className="text-xs text-muted-foreground/70 mb-1.5 uppercase tracking-wider font-medium">
              {session.chapters[activeCh]?.title}
            </p>
            <h2 className="text-2xl font-bold text-foreground tracking-tight">{topic?.title}</h2>
          </div>

          {/* Loading state */}
          {isGeneratingContent && !topicContent?.tldr && (
            <div className="bg-card/60 rounded-2xl px-6 py-10 border border-border/40 flex flex-col items-center justify-center gap-4 animate-fadeIn">
              <div className="relative">
                <Loader2 className="w-8 h-8 animate-spin text-[hsl(73,31%,45%)]" />
                <div className="absolute inset-0 w-8 h-8 rounded-full bg-[hsl(73,31%,45%)]/20 animate-ping" />
              </div>
              <div className="text-center">
                <span className="text-foreground/80 font-medium text-sm">Generating content...</span>
                <p className="text-xs text-muted-foreground mt-1">This may take a moment while AI researches the topic</p>
              </div>
            </div>
          )}

          {/* Error state */}
          {contentError && (
            <div className="bg-red-500/10 rounded-2xl px-6 py-6 border border-red-500/30 animate-fadeIn">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-red-400 mb-1">Generation Failed</h3>
                  <p className="text-sm text-foreground/70 mb-4">{contentError}</p>
                  <button
                    onClick={() => {
                      setContentError(null)
                      handleSelectTopic(activeCh, activeTopic)
                    }}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/15 hover:bg-red-500/25 text-red-400 text-sm font-medium transition-colors border border-red-500/30"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Retry
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Topic content */}
          {topicContent && (
            <TopicContentView
              topicTitle={topic?.title || ''}
              content={topicContent}
              chapterTitle={session.chapters[activeCh]?.title || ''}
              onTakeQuiz={handleTakeQuiz}
            />
          )}

          {/* Quiz loading */}
          {isGeneratingQuiz && (
            <div className="mt-4 bg-card/60 rounded-2xl px-6 py-5 border border-border/40 flex items-center justify-center gap-3 animate-fadeIn">
              <Loader2 className="w-5 h-5 animate-spin text-[hsl(73,31%,45%)]" />
              <span className="text-muted-foreground text-sm">Preparing your quiz...</span>
            </div>
          )}
        </div>
      </div>
      <GuideChatbot mode="exam-prep" context={guideContext} title="Study Guide" />
      </>
    )
  }

  // ── Quiz View ──
  if (view === 'quiz' && session && quizQuestions.length > 0) {
    const topic = session.chapters[activeCh]?.topics[activeTopic]

    return (
      <>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 animate-fadeIn">
          {/* Breadcrumb */}
          <div className="pt-6 mb-4">
            <button
              onClick={handleBackToRoadmap}
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors group"
            >
              <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
              Back to Roadmap
            </button>
          </div>

          <QuizView
            topicTitle={topic?.title || ''}
            questions={quizQuestions}
            onComplete={handleQuizComplete}
            onRetry={handleRetryQuiz}
          />
        </div>
      </div>
      </>
    )
  }

  return null
}
