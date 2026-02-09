'use client'

import { LearnerProfile, LearningPhase, PlanTopic } from '@/lib/types'
import {
  Brain,
  Target,
  Sparkles,
  Clock,
  ChevronRight,
  CheckCircle2,
  Star,
  TrendingUp,
  Lightbulb,
  BookOpen,
  Zap,
  BarChart3,
  ArrowLeft,
} from 'lucide-react'

interface LearningPlanViewProps {
  subject: string
  profile: LearnerProfile
  onSelectTopic: (phaseIdx: number, topicIdx: number, topic: PlanTopic, phase: LearningPhase) => void
  onBack: () => void
}

const levelConfig: Record<string, { color: string; bg: string; icon: string; label: string }> = {
  beginner: {
    color: 'text-emerald-400',
    bg: 'from-emerald-500/15 to-emerald-600/10 border-emerald-500/25',
    icon: '🌱',
    label: 'Beginner',
  },
  intermediate: {
    color: 'text-amber-400',
    bg: 'from-amber-500/15 to-amber-600/10 border-amber-500/25',
    icon: '🌿',
    label: 'Intermediate',
  },
  advanced: {
    color: 'text-[hsl(73,31%,50%)]',
    bg: 'from-[hsl(73,31%,45%)]/15 to-[hsl(73,40%,38%)]/10 border-[hsl(73,31%,45%)]/25',
    icon: '🌳',
    label: 'Advanced',
  },
}

export default function LearningPlanView({ subject, profile, onSelectTopic, onBack }: LearningPlanViewProps) {
  const level = levelConfig[profile.knowledgeLevel] || levelConfig.beginner

  const totalTopics = profile.learningPlan.reduce((sum, p) => sum + p.topics.length, 0)
  const completedTopics = profile.learningPlan.reduce(
    (sum, p) => sum + p.topics.filter((t) => t.status === 'completed').length,
    0
  )
  const totalMinutes = profile.learningPlan.reduce(
    (sum, p) => sum + p.topics.reduce((s, t) => s + t.estimatedMinutes, 0),
    0
  )

  return (
    <div className="flex-1 overflow-y-auto relative">
      {/* Ambient orbs */}
      <div className="orb orb-primary w-[200px] h-[200px] top-[5%] right-[10%] animate-float" />
      <div className="orb orb-secondary w-[140px] h-[140px] bottom-[10%] left-[5%] animate-float" style={{ animationDelay: '1.5s' }} />

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8 relative z-10">
        {/* Back button */}
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors animate-fadeIn"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Personalized
        </button>

        {/* Profile Summary Card */}
        <div className="rounded-2xl border border-border/40 bg-card/60 backdrop-blur-sm overflow-hidden shadow-lg shadow-black/5 animate-fadeIn">
          <div className="bg-gradient-to-r from-[hsl(73,31%,45%)]/10 via-[hsl(73,40%,38%)]/10 to-[hsl(73,31%,50%)]/10 p-6 border-b border-border/20">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-foreground mb-1">
                  Your Personalized Plan
                </h2>
                <p className="text-sm text-muted-foreground">
                  Tailored for learning <span className="text-[hsl(73,31%,50%)] font-medium">{subject}</span>
                </p>
              </div>
              <div className={`flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r ${level.bg} border`}>
                <span className="text-lg">{level.icon}</span>
                <div>
                  <div className={`text-xs font-semibold ${level.color}`}>Your Level</div>
                  <div className="text-sm font-bold text-foreground">{level.label}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-4 divide-x divide-border/20">
            <div className="p-4 text-center">
              <div className="text-2xl font-bold text-foreground">{profile.overallScore}%</div>
              <div className="text-xs text-muted-foreground mt-0.5">Assessment Score</div>
            </div>
            <div className="p-4 text-center">
              <div className="text-2xl font-bold text-foreground">{profile.learningPlan.length}</div>
              <div className="text-xs text-muted-foreground mt-0.5">Learning Phases</div>
            </div>
            <div className="p-4 text-center">
              <div className="text-2xl font-bold text-foreground">{totalTopics}</div>
              <div className="text-xs text-muted-foreground mt-0.5">Topics to Learn</div>
            </div>
            <div className="p-4 text-center">
              <div className="text-2xl font-bold text-foreground">~{totalMinutes}m</div>
              <div className="text-xs text-muted-foreground mt-0.5">Estimated Time</div>
            </div>
          </div>

          {/* Progress bar */}
          {completedTopics > 0 && (
            <div className="px-6 py-3 border-t border-border/20 bg-muted/10">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-muted-foreground">Overall Progress</span>
                <span className="text-foreground font-medium">{completedTopics}/{totalTopics} completed</span>
              </div>
              <div className="h-2 rounded-full bg-muted/30 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,55%)] transition-all duration-500"
                  style={{ width: `${(completedTopics / totalTopics) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Motivational message */}
        <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-gradient-to-r from-[hsl(73,31%,45%)]/10 to-[hsl(73,40%,38%)]/10 border border-[hsl(73,31%,45%)]/20">
          <Sparkles className="w-5 h-5 text-[hsl(73,31%,50%)] flex-shrink-0 mt-0.5" />
          <p className="text-sm text-foreground/80 leading-relaxed">{profile.motivationalNote}</p>
        </div>

        {/* Strengths & Weaknesses */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {profile.strengthAreas.length > 0 && (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Star className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-emerald-400">Your Strengths</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {profile.strengthAreas.map((area, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">
                    {area}
                  </span>
                ))}
              </div>
            </div>
          )}

          {profile.weaknessAreas.length > 0 && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Target className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-amber-400">Focus Areas</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {profile.weaknessAreas.map((area, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300">
                    {area}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Tips */}
        {profile.personalizedTips.length > 0 && (
          <div className="rounded-xl border border-border/30 bg-card/30 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-foreground">Personalized Tips</h3>
            </div>
            <ul className="space-y-2">
              {profile.personalizedTips.map((tip, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="text-[hsl(73,31%,50%)] mt-1">•</span>
                  {tip}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Learning Phases */}
        <div className="space-y-5">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-[hsl(73,31%,50%)]" />
            <h3 className="text-lg font-bold text-foreground">Your Learning Journey</h3>
          </div>

          {profile.learningPlan.map((phase, phaseIdx) => {
            const phaseCompleted = phase.topics.filter((t) => t.status === 'completed').length
            const phaseTotal = phase.topics.length
            const phaseProgress = phaseTotal > 0 ? (phaseCompleted / phaseTotal) * 100 : 0
            const isPhaseComplete = phaseCompleted === phaseTotal

            return (
              <div
                key={phaseIdx}
                className={`rounded-2xl border overflow-hidden transition-all ${
                  isPhaseComplete
                    ? 'border-emerald-500/30 bg-emerald-500/5'
                    : 'border-border/30 bg-card/50'
                }`}
              >
                {/* Phase header */}
                <div className="px-5 py-4 border-b border-border/20">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold ${
                        isPhaseComplete
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-[hsl(73,31%,45%)]/20 text-[hsl(73,31%,50%)]'
                      }`}>
                        {isPhaseComplete ? <CheckCircle2 className="w-5 h-5" /> : phase.phase}
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground">{phase.title}</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">{phase.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded-lg bg-muted/30 text-xs text-muted-foreground">
                        <Zap className="w-3 h-3 inline mr-1" />
                        {phase.technique}
                      </span>
                    </div>
                  </div>

                  {/* Phase progress */}
                  {phaseCompleted > 0 && (
                    <div className="mt-3">
                      <div className="h-1.5 rounded-full bg-muted/30 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-[hsl(73,31%,45%)] to-emerald-500 transition-all duration-500"
                          style={{ width: `${phaseProgress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Topics */}
                <div className="divide-y divide-border/10">
                  {phase.topics.map((topic, topicIdx) => {
                    const isCompleted = topic.status === 'completed'
                    const isInProgress = topic.status === 'in-progress'

                    return (
                      <button
                        key={topicIdx}
                        onClick={() => onSelectTopic(phaseIdx, topicIdx, topic, phase)}
                        className={`w-full flex items-center gap-4 px-5 py-3.5 text-left transition-all duration-200 hover:bg-muted/20 group ${
                          isCompleted ? 'opacity-70' : ''
                        }`}
                      >
                        <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          isCompleted
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : isInProgress
                            ? 'bg-[hsl(73,31%,45%)]/20 text-[hsl(73,31%,50%)]'
                            : 'bg-muted/30 text-muted-foreground'
                        }`}>
                          {isCompleted ? (
                            <CheckCircle2 className="w-4 h-4" />
                          ) : isInProgress ? (
                            <TrendingUp className="w-4 h-4" />
                          ) : (
                            <BookOpen className="w-3.5 h-3.5" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-foreground group-hover:text-[hsl(73,31%,50%)] transition-colors">
                            {topic.title}
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                            {topic.reason}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {topic.estimatedMinutes}m
                          </span>
                          <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
