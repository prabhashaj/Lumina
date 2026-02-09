'use client'

import { Chapter, Topic } from '@/lib/types'
import {
  BookOpen,
  CheckCircle2,
  Lock,
  CircleDot,
  Loader2,
  ChevronDown,
  ChevronRight,
  Trophy,
  Sparkles,
  ArrowLeft,
  Target,
} from 'lucide-react'
import { useState } from 'react'

interface RoadmapViewProps {
  subject: string
  chapters: Chapter[]
  overallProgress: number
  onSelectTopic: (chapterIdx: number, topicIdx: number) => void
  onBack: () => void
}

export default function RoadmapView({
  subject,
  chapters,
  overallProgress,
  onSelectTopic,
  onBack,
}: RoadmapViewProps) {
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(() => {
    const expanded = new Set<string>()
    chapters.forEach((ch) => {
      if (ch.topics.some((t) => t.status === 'available' || t.status === 'generating' || t.status === 'completed' || t.status === 'quiz-pending')) {
        expanded.add(ch.id)
      }
    })
    if (expanded.size === 0 && chapters.length > 0) expanded.add(chapters[0].id)
    return expanded
  })

  const toggleChapter = (chId: string) => {
    setExpandedChapters((prev) => {
      const next = new Set(prev)
      if (next.has(chId)) next.delete(chId)
      else next.add(chId)
      return next
    })
  }

  const getChapterProgress = (ch: Chapter) => {
    const done = ch.topics.filter((t) => t.status === 'quiz-done').length
    return { done, total: ch.topics.length, pct: ch.topics.length > 0 ? Math.round((done / ch.topics.length) * 100) : 0 }
  }

  const getStatusIcon = (status: Topic['status']) => {
    switch (status) {
      case 'locked':
        return <Lock className="w-3.5 h-3.5 text-muted-foreground/30" />
      case 'available':
        return <CircleDot className="w-3.5 h-3.5 text-[hsl(73,31%,45%)]" />
      case 'generating':
        return <Loader2 className="w-3.5 h-3.5 text-[hsl(73,31%,45%)] animate-spin" />
      case 'completed':
        return <Target className="w-3.5 h-3.5 text-amber-400" />
      case 'quiz-pending':
        return <Target className="w-3.5 h-3.5 text-amber-400" />
      case 'quiz-done':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
    }
  }

  const getStatusLabel = (status: Topic['status']) => {
    switch (status) {
      case 'locked': return 'Locked'
      case 'available': return 'Start'
      case 'generating': return 'Generating...'
      case 'completed': return 'Take Quiz'
      case 'quiz-pending': return 'Take Quiz'
      case 'quiz-done': return 'Done'
    }
  }

  const completedChapters = chapters.filter(
    (ch) => ch.topics.every((t) => t.status === 'quiz-done')
  ).length

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 animate-fadeIn">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-5 transition-colors group"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            Back to subjects
          </button>

          {/* Subject hero */}
          <div className="bg-gradient-to-br from-card/80 to-card/40 rounded-2xl border border-border/30 p-6 shadow-lg shadow-black/5">
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">{subject}</h1>
                <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <BookOpen className="w-3.5 h-3.5" />
                    {chapters.length} chapters
                  </span>
                  <span className="text-border">|</span>
                  <span>{chapters.reduce((sum, ch) => sum + ch.topics.length, 0)} topics</span>
                  <span className="text-border">|</span>
                  <span className="text-emerald-500 font-medium">{completedChapters} completed</span>
                </div>
              </div>

              {/* Circular progress */}
              <div className="relative w-16 h-16 flex-shrink-0">
                <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
                  <circle
                    cx="18" cy="18" r="14"
                    fill="none"
                    stroke="hsl(0 0% 16%)"
                    strokeWidth="2.5"
                  />
                  <circle
                    cx="18" cy="18" r="14"
                    fill="none"
                    stroke="hsl(73 31% 45%)"
                    strokeWidth="2.5"
                    strokeDasharray={`${overallProgress * 0.88} 88`}
                    strokeLinecap="round"
                    className="transition-all duration-700"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  {overallProgress === 100 ? (
                    <Trophy className="w-5 h-5 text-amber-400" />
                  ) : (
                    <>
                      <span className="text-sm font-bold text-[hsl(73,31%,45%)] leading-none animate-countUp">{overallProgress}%</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Progress bar */}
            <div className="mt-4 h-1.5 rounded-full bg-muted/60 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,55%)] transition-all duration-700 ease-out"
                style={{ width: `${overallProgress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Chapters — Timeline style */}
        <div className="relative">
          {/* Vertical timeline line */}
          <div className="absolute left-[23px] top-0 bottom-0 w-[2px] bg-gradient-to-b from-[hsl(73,31%,45%)]/30 via-border/30 to-transparent" />

          <div className="space-y-3">
            {chapters.map((ch, chIdx) => {
              const { done, total, pct } = getChapterProgress(ch)
              const isExpanded = expandedChapters.has(ch.id)
              const isChapterDone = done === total && total > 0

              return (
                <div
                  key={ch.id}
                  className="relative pl-12 animate-fadeIn"
                  style={{ animationDelay: `${chIdx * 60}ms` }}
                >
                  {/* Timeline node */}
                  <div className={`absolute left-[14px] top-5 w-[20px] h-[20px] rounded-full border-2 flex items-center justify-center z-10 transition-all duration-300 ${
                    isChapterDone
                      ? 'bg-emerald-500 border-emerald-500 shadow-md shadow-emerald-500/20'
                      : done > 0
                      ? 'bg-[hsl(73,31%,45%)] border-[hsl(73,31%,45%)] shadow-md shadow-[hsl(73,31%,45%)]/20'
                      : 'bg-background border-border'
                  }`}>
                    {isChapterDone ? (
                      <CheckCircle2 className="w-3 h-3 text-white" />
                    ) : done > 0 ? (
                      <span className="w-2 h-2 rounded-full bg-white" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-muted-foreground/30" />
                    )}
                  </div>

                  {/* Chapter card */}
                  <div className={`bg-card/50 rounded-2xl border transition-all duration-300 overflow-hidden ${
                    isChapterDone
                      ? 'border-emerald-500/20 bg-emerald-500/[0.03]'
                      : isExpanded
                      ? 'border-[hsl(73,31%,45%)]/20 shadow-lg shadow-black/5'
                      : 'border-border/30 hover:border-border/50 hover:shadow-md hover:shadow-black/5'
                  }`}>
                    {/* Chapter header */}
                    <button
                      onClick={() => toggleChapter(ch.id)}
                      className="w-full flex items-center gap-3 px-5 py-4 hover:bg-muted/20 transition-colors text-left"
                    >
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                        isChapterDone
                          ? 'bg-emerald-500/15'
                          : 'bg-[hsl(73,31%,45%)]/10'
                      }`}>
                        <span className={`text-sm font-bold ${
                          isChapterDone ? 'text-emerald-500' : 'text-[hsl(73,31%,45%)]'
                        }`}>{chIdx + 1}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-foreground truncate">{ch.title}</h3>
                          {isChapterDone && (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-500 font-semibold">COMPLETE</span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground/70 mt-0.5 truncate">{ch.description}</p>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <span className="text-xs font-medium text-muted-foreground tabular-nums">
                          {done}/{total}
                        </span>
                        <div className={`transition-transform duration-200 ${isExpanded ? 'rotate-0' : '-rotate-90'}`}>
                          <ChevronDown className="w-4 h-4 text-muted-foreground/50" />
                        </div>
                      </div>
                    </button>

                    {/* Topics */}
                    {isExpanded && (
                      <div className="border-t border-border/30 px-3 py-2 stagger-children">
                        {ch.topics.map((topic, tIdx) => {
                          const isClickable = topic.status !== 'locked' && topic.status !== 'generating'

                          return (
                            <button
                              key={topic.id}
                              onClick={() => isClickable && onSelectTopic(chIdx, tIdx)}
                              disabled={!isClickable}
                              className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left transition-all duration-200 ${
                                isClickable
                                  ? 'hover:bg-[hsl(73,31%,45%)]/8 cursor-pointer'
                                  : 'opacity-40 cursor-not-allowed'
                              } ${
                                topic.status === 'quiz-done'
                                  ? 'bg-emerald-500/[0.04]'
                                  : ''
                              }`}
                            >
                              {/* Status indicator */}
                              <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                                topic.status === 'quiz-done'
                                  ? 'bg-emerald-500/15'
                                  : topic.status === 'available'
                                  ? 'bg-[hsl(73,31%,45%)]/10'
                                  : topic.status === 'completed' || topic.status === 'quiz-pending'
                                  ? 'bg-amber-400/15'
                                  : 'bg-muted/50'
                              }`}>
                                {getStatusIcon(topic.status)}
                              </div>

                              <span
                                className={`flex-1 text-sm ${
                                  topic.status === 'locked'
                                    ? 'text-muted-foreground/40'
                                    : topic.status === 'quiz-done'
                                    ? 'text-emerald-400'
                                    : 'text-foreground'
                                }`}
                              >
                                {topic.title}
                              </span>

                              <span
                                className={`text-[11px] font-medium px-2.5 py-1 rounded-lg transition-colors ${
                                  topic.status === 'available'
                                    ? 'bg-[hsl(73,31%,45%)]/10 text-[hsl(73,31%,45%)]'
                                    : topic.status === 'completed' || topic.status === 'quiz-pending'
                                    ? 'bg-amber-400/10 text-amber-500'
                                    : topic.status === 'quiz-done'
                                    ? 'bg-emerald-500/10 text-emerald-500'
                                    : 'text-muted-foreground/30'
                                }`}
                              >
                                {getStatusLabel(topic.status)}
                                {topic.status === 'quiz-done' && topic.quizScore !== undefined && (
                                  <> &middot; {topic.quizScore}%</>
                                )}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
