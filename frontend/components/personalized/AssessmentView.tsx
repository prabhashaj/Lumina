'use client'

import { useState } from 'react'
import { AssessmentQuestion } from '@/lib/types'
import {
  CheckCircle2,
  XCircle,
  ChevronRight,
  Brain,
  Sparkles,
  Target,
  Zap,
} from 'lucide-react'

interface AssessmentViewProps {
  topic: string
  questions: AssessmentQuestion[]
  onComplete: (answers: number[]) => void
}

const difficultyColors: Record<string, string> = {
  foundational: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30 text-emerald-400',
  intermediate: 'from-amber-500/20 to-amber-600/10 border-amber-500/30 text-amber-400',
  advanced: 'from-rose-500/20 to-rose-600/10 border-rose-500/30 text-rose-400',
}

const difficultyLabels: Record<string, string> = {
  foundational: '🟢 Foundational',
  intermediate: '🟡 Intermediate',
  advanced: '🔴 Advanced',
}

export default function AssessmentView({ topic, questions, onComplete }: AssessmentViewProps) {
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<number[]>(new Array(questions.length).fill(-1))
  const [selectedOption, setSelectedOption] = useState<number | null>(null)
  const [showResult, setShowResult] = useState(false)

  const current = questions[currentIdx]
  const isLast = currentIdx === questions.length - 1
  const answeredCount = answers.filter((a) => a !== -1).length

  const handleSelect = (optionIdx: number) => {
    if (showResult) return
    setSelectedOption(optionIdx)
  }

  const handleConfirm = () => {
    if (selectedOption === null) return

    const newAnswers = [...answers]
    newAnswers[currentIdx] = selectedOption
    setAnswers(newAnswers)
    setShowResult(true)
  }

  const handleNext = () => {
    if (isLast) {
      onComplete(answers)
      return
    }
    setCurrentIdx((prev) => prev + 1)
    setSelectedOption(null)
    setShowResult(false)
  }

  const isCorrect = showResult && selectedOption === current.correctIndex

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-[hsl(73,31%,45%)]/15 to-[hsl(73,40%,38%)]/15 border border-[hsl(73,31%,45%)]/20 mb-4">
            <Brain className="w-4 h-4 text-[hsl(73,31%,50%)]" />
            <span className="text-sm font-medium text-[hsl(73,31%,55%)]">
              Knowledge Assessment
            </span>
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">
            Let&apos;s see what you know about
          </h2>
          <p className="text-lg text-[hsl(73,31%,50%)] font-semibold">{topic}</p>
          <p className="text-sm text-muted-foreground mt-2">
            Answer these questions so we can personalize your learning journey
          </p>
        </div>

        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Question {currentIdx + 1} of {questions.length}</span>
            <span>{answeredCount} answered</span>
          </div>
          <div className="h-2 rounded-full bg-muted/30 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,55%)] transition-all duration-500"
              style={{ width: `${((currentIdx + (showResult ? 1 : 0)) / questions.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Question Card */}
        <div className="rounded-2xl border border-border/30 bg-card/50 backdrop-blur-sm overflow-hidden">
          {/* Difficulty badge */}
          <div className="px-6 pt-5 pb-3 flex items-center gap-3">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r border ${difficultyColors[current.difficulty] || difficultyColors.foundational}`}>
              {difficultyLabels[current.difficulty] || current.difficulty}
            </span>
            <span className="text-xs text-muted-foreground">
              {current.subTopic}
            </span>
          </div>

          {/* Question */}
          <div className="px-6 pb-4">
            <h3 className="text-lg font-semibold text-foreground leading-relaxed">
              {current.question}
            </h3>
          </div>

          {/* Options */}
          <div className="px-6 pb-6 space-y-3">
            {current.options.map((option, idx) => {
              let optionStyle = 'border-border/30 hover:border-[hsl(73,31%,45%)]/40 hover:bg-[hsl(73,31%,45%)]/5'

              if (showResult) {
                if (idx === current.correctIndex) {
                  optionStyle = 'border-emerald-500/50 bg-emerald-500/10'
                } else if (idx === selectedOption && idx !== current.correctIndex) {
                  optionStyle = 'border-rose-500/50 bg-rose-500/10'
                } else {
                  optionStyle = 'border-border/20 opacity-50'
                }
              } else if (selectedOption === idx) {
                optionStyle = 'border-[hsl(73,31%,45%)]/60 bg-[hsl(73,31%,45%)]/10 ring-1 ring-[hsl(73,31%,45%)]/30'
              }

              return (
                <button
                  key={idx}
                  onClick={() => handleSelect(idx)}
                  disabled={showResult}
                  className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl border text-left transition-all duration-200 ${optionStyle}`}
                >
                  <span className="flex-shrink-0 w-8 h-8 rounded-lg bg-muted/40 flex items-center justify-center text-sm font-bold text-muted-foreground">
                    {String.fromCharCode(65 + idx)}
                  </span>
                  <span className="text-sm text-foreground flex-1">{option}</span>
                  {showResult && idx === current.correctIndex && (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                  )}
                  {showResult && idx === selectedOption && idx !== current.correctIndex && (
                    <XCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
                  )}
                </button>
              )
            })}
          </div>

          {/* Result feedback */}
          {showResult && (
            <div className={`px-6 py-4 border-t ${isCorrect ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-rose-500/5 border-rose-500/20'}`}>
              <div className="flex items-center gap-2 mb-1">
                {isCorrect ? (
                  <>
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-semibold text-emerald-400">Excellent!</span>
                  </>
                ) : (
                  <>
                    <Target className="w-4 h-4 text-rose-400" />
                    <span className="text-sm font-semibold text-rose-400">Not quite — we&apos;ll cover this!</span>
                  </>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {isCorrect
                  ? 'This shows strong understanding in this area.'
                  : `The correct answer is: ${current.options[current.correctIndex]}. Don't worry — your personalized plan will address this.`
                }
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="px-6 py-4 border-t border-border/20 flex items-center justify-between">
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <Zap className="w-3.5 h-3.5" />
              {current.cognitiveLevel}
            </div>

            {!showResult ? (
              <button
                onClick={handleConfirm}
                disabled={selectedOption === null}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white shadow-lg shadow-[hsl(73,31%,45%)]/25 hover:shadow-[hsl(73,31%,45%)]/40 transition-all duration-200 disabled:opacity-40 disabled:shadow-none"
              >
                Confirm Answer
              </button>
            ) : (
              <button
                onClick={handleNext}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white shadow-lg shadow-[hsl(73,31%,45%)]/25 hover:shadow-[hsl(73,31%,45%)]/40 transition-all duration-200"
              >
                {isLast ? 'See My Learning Plan' : 'Next Question'}
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
