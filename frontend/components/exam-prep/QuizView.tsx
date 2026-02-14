'use client'

import { useState } from 'react'
import { QuizQuestion } from '@/lib/types'
import { CheckCircle2, XCircle, ArrowRight, Trophy, RotateCcw, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface QuizViewProps {
  topicTitle: string
  questions: QuizQuestion[]
  onComplete: (score: number, answers: number[]) => void
  onRetry: () => void
}

export default function QuizView({ topicTitle, questions, onComplete, onRetry }: QuizViewProps) {
  const [currentQ, setCurrentQ] = useState(0)
  const [selectedAnswers, setSelectedAnswers] = useState<(number | null)[]>(
    new Array(questions.length).fill(null)
  )
  const [showResult, setShowResult] = useState(false)
  const [isAnswered, setIsAnswered] = useState(false)

  const question = questions[currentQ]
  const selected = selectedAnswers[currentQ]
  const isCorrect = selected === question?.correctIndex

  const handleSelect = (optionIdx: number) => {
    if (isAnswered) return
    const updated = [...selectedAnswers]
    updated[currentQ] = optionIdx
    setSelectedAnswers(updated)
    setIsAnswered(true)
  }

  const handleNext = () => {
    if (currentQ < questions.length - 1) {
      setCurrentQ((p) => p + 1)
      setIsAnswered(false)
    } else {
      let correct = 0
      selectedAnswers.forEach((ans, i) => {
        if (ans === questions[i].correctIndex) correct++
      })
      const score = Math.round((correct / questions.length) * 100)
      setShowResult(true)
      onComplete(score, selectedAnswers as number[])
    }
  }

  // Results screen
  if (showResult) {
    let correct = 0
    selectedAnswers.forEach((ans, i) => {
      if (ans === questions[i].correctIndex) correct++
    })
    const score = Math.round((correct / questions.length) * 100)
    const passed = score >= 60

    return (
      <div className="max-w-2xl mx-auto py-8 animate-fadeInUp">
        <div className="bg-card/60 rounded-2xl border border-border/30 p-8 text-center shadow-xl shadow-black/5">
          {/* Result icon */}
          <div className={`relative w-24 h-24 rounded-3xl mx-auto mb-5 flex items-center justify-center ${
            passed
              ? 'bg-gradient-to-br from-emerald-500/20 to-emerald-500/5'
              : 'bg-gradient-to-br from-amber-500/20 to-amber-500/5'
          }`}>
            {passed ? (
              <Trophy className="w-11 h-11 text-emerald-500 animate-countUp" />
            ) : (
              <RotateCcw className="w-11 h-11 text-amber-500 animate-countUp" />
            )}
            {passed && (
              <div className="absolute -top-1 -right-1">
                <Sparkles className="w-5 h-5 text-amber-400 animate-float" />
              </div>
            )}
          </div>

          <h2 className="text-xl font-bold text-foreground mb-1">
            {passed ? 'Excellent work!' : 'Keep practicing!'}
          </h2>
          <p className="text-sm text-muted-foreground mb-6">{topicTitle}</p>

          <div className="text-5xl font-bold mb-2 animate-countUp" style={{ color: passed ? '#10b981' : '#f59e0b' }}>
            {score}%
          </div>
          <p className="text-sm text-muted-foreground mb-8">
            {correct} of {questions.length} correct
          </p>

          {/* Review answers */}
          <div className="text-left space-y-3 mb-8 stagger-children">
            {questions.map((q, i) => {
              const userAns = selectedAnswers[i]
              const wasCorrect = userAns === q.correctIndex

              return (
                <div
                  key={q.id}
                  className={`rounded-xl p-4 border transition-all ${
                    wasCorrect
                      ? 'bg-emerald-500/[0.04] border-emerald-500/15'
                      : 'bg-red-500/[0.04] border-red-500/15'
                  }`}
                >
                  <div className="flex items-start gap-2 mb-2">
                    {wasCorrect ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="text-sm font-medium text-foreground leading-relaxed prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ p: ({ children }) => <span>{children}</span> }}>{q.question}</ReactMarkdown></div>
                  </div>
                  {!wasCorrect && (
                    <div className="ml-6 space-y-1">
                      <div className="text-xs text-red-400/80">
                        Your answer: <ReactMarkdown remarkPlugins={[remarkGfm]} className="inline" components={{ p: ({ children }) => <span>{children}</span> }}>{q.options[userAns ?? 0]}</ReactMarkdown>
                      </div>
                      <div className="text-xs text-emerald-400">
                        Correct: <ReactMarkdown remarkPlugins={[remarkGfm]} className="inline" components={{ p: ({ children }) => <span>{children}</span> }}>{q.options[q.correctIndex]}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                  <div className="ml-6 text-xs text-muted-foreground/70 mt-1.5 leading-relaxed prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ p: ({ children }) => <span>{children}</span> }}>{q.explanation}</ReactMarkdown></div>
                </div>
              )
            })}
          </div>

          {!passed && (
            <button
              onClick={onRetry}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white font-semibold text-sm hover:shadow-lg hover:shadow-[hsl(73,31%,45%)]/25 transition-all duration-300"
            >
              Retry Quiz
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto py-8 animate-fadeIn">
      {/* Progress */}
      <div className="flex items-center justify-between mb-6">
        <span className="text-sm text-muted-foreground font-medium">
          Question {currentQ + 1} of {questions.length}
        </span>
        <div className="flex gap-1.5">
          {questions.map((_, i) => (
            <div
              key={i}
              className={`w-8 h-1.5 rounded-full transition-all duration-300 ${
                i < currentQ
                  ? selectedAnswers[i] === questions[i].correctIndex
                    ? 'bg-emerald-500'
                    : 'bg-red-500'
                  : i === currentQ
                  ? 'bg-[hsl(73,31%,45%)] shadow-sm shadow-[hsl(73,31%,45%)]/30'
                  : 'bg-muted/60'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Question card */}
      <div className="bg-card/60 rounded-2xl border border-border/30 p-6 shadow-lg shadow-black/5 animate-fadeInScale" key={currentQ}>
        <div className="text-base font-semibold text-foreground mb-6 leading-relaxed prose dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ p: ({ children }) => <span>{children}</span> }}>{question.question}</ReactMarkdown></div>

        <div className="space-y-2.5">
          {question.options.map((option, optIdx) => {
            let optionStyle = 'border-border/30 hover:border-[hsl(73,31%,45%)]/30 hover:bg-[hsl(73,31%,45%)]/[0.04]'

            if (isAnswered) {
              if (optIdx === question.correctIndex) {
                optionStyle = 'border-emerald-500/40 bg-emerald-500/[0.06] shadow-sm shadow-emerald-500/5'
              } else if (optIdx === selected && !isCorrect) {
                optionStyle = 'border-red-500/40 bg-red-500/[0.06]'
              } else {
                optionStyle = 'border-border/20 opacity-40'
              }
            } else if (selected === optIdx) {
              optionStyle = 'border-[hsl(73,31%,45%)]/50 bg-[hsl(73,31%,45%)]/[0.06]'
            }

            return (
              <button
                key={optIdx}
                onClick={() => handleSelect(optIdx)}
                disabled={isAnswered}
                className={`w-full flex items-center gap-3 p-4 rounded-xl border text-left transition-all duration-200 ${optionStyle}`}
              >
                <span
                  className={`w-7 h-7 rounded-lg border-2 flex items-center justify-center flex-shrink-0 text-xs font-bold transition-all duration-200 ${
                    isAnswered && optIdx === question.correctIndex
                      ? 'border-emerald-500 text-emerald-500 bg-emerald-500/10'
                      : isAnswered && optIdx === selected && !isCorrect
                      ? 'border-red-500 text-red-500 bg-red-500/10'
                      : selected === optIdx
                      ? 'border-[hsl(73,31%,45%)] text-[hsl(73,31%,45%)] bg-[hsl(73,31%,45%)]/10'
                      : 'border-border/50 text-muted-foreground/50'
                  }`}
                >
                  {String.fromCharCode(65 + optIdx)}
                </span>
                <span className="text-sm text-foreground flex-1 prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]} className="inline" components={{ p: ({ children }) => <span>{children}</span> }}>{option}</ReactMarkdown></span>
                {isAnswered && optIdx === question.correctIndex && (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 ml-auto flex-shrink-0 animate-fadeInScale" />
                )}
                {isAnswered && optIdx === selected && !isCorrect && (
                  <XCircle className="w-5 h-5 text-red-500 ml-auto flex-shrink-0 animate-fadeInScale" />
                )}
              </button>
            )
          })}
        </div>

        {/* Explanation */}
        {isAnswered && (
          <div
            className={`mt-5 p-4 rounded-xl border animate-fadeIn ${
              isCorrect
                ? 'bg-emerald-500/[0.04] border-emerald-500/15'
                : 'bg-amber-500/[0.04] border-amber-500/15'
            }`}
          >
            <div className="text-sm text-foreground/75 leading-relaxed prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ p: ({ children }) => <span>{children}</span> }}>{question.explanation}</ReactMarkdown></div>
          </div>
        )}

        {/* Next button */}
        {isAnswered && (
          <div className="mt-6 flex justify-end animate-fadeIn">
            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white font-semibold text-sm hover:shadow-lg hover:shadow-[hsl(73,31%,45%)]/25 transition-all duration-300"
            >
              {currentQ < questions.length - 1 ? (
                <>
                  Next <ArrowRight className="w-4 h-4" />
                </>
              ) : (
                'See Results'
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
