'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import {
  Presentation as PresentationIcon,
  Sparkles,
  Loader2,
  AlertCircle,
  BookOpen,
  Clock,
  Layers,
  Play,
  ImageIcon,
  Mic,
  ArrowRight,
} from 'lucide-react'
import { Slide, Presentation } from '@/lib/types'
import { streamVideoLecture } from '@/lib/api'
import SlideViewer from './SlideViewer'
import VoiceNarration from './VoiceNarration'
import GuideChatbot from '../shared/GuideChatbot'

type GenerationStatus = 'idle' | 'generating' | 'ready' | 'error'

export default function VideoLectureMode() {
  const [topic, setTopic] = useState('')
  const [numSlides, setNumSlides] = useState(10)
  const [difficulty, setDifficulty] = useState('intermediate')
  const [status, setStatus] = useState<GenerationStatus>('idle')
  const [statusMessage, setStatusMessage] = useState('')
  const [error, setError] = useState('')
  const [presentation, setPresentation] = useState<Presentation | null>(null)
  const [currentSlide, setCurrentSlide] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [autoAdvance, setAutoAdvance] = useState(true)
  const inputRef = useRef<HTMLInputElement>(null)
  const [generatedSlideCount, setGeneratedSlideCount] = useState(0)

  // Handle streaming generation
  const handleGenerate = useCallback(async () => {
    if (!topic.trim()) return

    setStatus('generating')
    setError('')
    setStatusMessage('Initializing...')
    setPresentation(null)
    setCurrentSlide(0)
    setIsPlaying(false)
    setGeneratedSlideCount(0)

    const slides: Slide[] = []
    let metadata: Partial<Presentation> = {}

    try {
      await streamVideoLecture(topic.trim(), numSlides, difficulty, (chunk) => {
        switch (chunk.type) {
          case 'status':
            setStatusMessage(chunk.data)
            break
          case 'metadata':
            metadata = chunk.data
            break
          case 'slide':
            slides.push(chunk.data as Slide)
            setGeneratedSlideCount(slides.length)
            setStatusMessage(`Generated slide ${slides.length}...`)
            setPresentation({
              title: metadata.title || topic,
              subtitle: metadata.subtitle || '',
              total_slides: metadata.total_slides || numSlides,
              estimated_duration_minutes: metadata.estimated_duration_minutes || numSlides * 2,
              slides: [...slides],
            })
            break
          case 'complete':
            setStatus('ready')
            setStatusMessage('')
            break
          case 'error':
            setStatus('error')
            setError(chunk.data)
            break
        }
      })

      if (slides.length > 0 && status !== 'error') {
        setPresentation({
          title: metadata.title || topic,
          subtitle: metadata.subtitle || '',
          total_slides: slides.length,
          estimated_duration_minutes: metadata.estimated_duration_minutes || slides.length * 2,
          slides,
        })
        setStatus('ready')
      }
    } catch (err: any) {
      setStatus('error')
      setError(err.message || 'Failed to generate video lecture')
    }
  }, [topic, numSlides, difficulty])

  // Handle narration end -> auto-advance to next slide
  const handleNarrationEnd = useCallback(() => {
    if (autoAdvance && isPlaying && presentation) {
      if (currentSlide < presentation.slides.length - 1) {
        // Short pause between slides for natural feel
        setTimeout(() => setCurrentSlide((prev) => prev + 1), 500)
      } else {
        setIsPlaying(false)
      }
    }
  }, [autoAdvance, isPlaying, presentation, currentSlide])

  const togglePlay = useCallback(() => {
    setIsPlaying((prev) => !prev)
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleGenerate()
  }

  const currentSlideData = presentation?.slides[currentSlide]

  // ── Idle / Input State ──
  if (status === 'idle' || (status === 'error' && !presentation)) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-xl animate-fadeInUp">
          {/* Hero — text only */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[hsl(73,31%,45%)]/10 border border-[hsl(73,31%,45%)]/20 text-[11px] font-semibold text-[hsl(73,31%,55%)] uppercase tracking-widest mb-4">
              <span className="w-1.5 h-1.5 rounded-full bg-[hsl(73,31%,50%)] animate-pulse" />
              AI-Powered
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight leading-tight">
              Video <span className="text-gradient">Lecture</span>
            </h2>
            <p className="text-muted-foreground text-sm mt-3 max-w-md mx-auto leading-relaxed">
              Enter a topic and get an interactive slide presentation with narration, images, and smooth animations — all generated in seconds.
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-5 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3 animate-fadeIn">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-red-300 font-medium">Generation failed</p>
                <p className="text-xs text-red-400/70 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Input Card */}
          <div className="bg-card/50 backdrop-blur-xl rounded-2xl border border-border/20 p-6 space-y-5 shadow-xl shadow-black/5">
            {/* Topic */}
            <div>
              <label className="block text-[11px] font-bold text-muted-foreground/80 mb-2 uppercase tracking-[0.15em]">
                Topic
              </label>
              <input
                ref={inputRef}
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. Photosynthesis, Machine Learning, Quantum Computing..."
                className="w-full bg-background/60 border border-border/30 rounded-xl px-4 py-3.5 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-[hsl(73,31%,45%)]/30 focus:border-[hsl(73,31%,45%)]/40 transition-all duration-300"
              />
            </div>

            {/* Options row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold text-muted-foreground/80 mb-2 uppercase tracking-[0.15em]">
                  Slides
                </label>
                <select
                  value={numSlides}
                  onChange={(e) => setNumSlides(parseInt(e.target.value))}
                  className="w-full bg-background/60 border border-border/30 rounded-xl px-4 py-3.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-[hsl(73,31%,45%)]/30 transition-all duration-300 appearance-none cursor-pointer"
                >
                  {[6, 8, 10, 12, 15].map((n) => (
                    <option key={n} value={n}>{n} slides (~{n * 2} min)</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-muted-foreground/80 mb-2 uppercase tracking-[0.15em]">
                  Difficulty
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full bg-background/60 border border-border/30 rounded-xl px-4 py-3.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-[hsl(73,31%,45%)]/30 transition-all duration-300 appearance-none cursor-pointer"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
            </div>

            {/* Generate button */}
            <button
              onClick={handleGenerate}
              disabled={!topic.trim()}
              className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,35%,50%)] text-white font-semibold text-sm shadow-lg shadow-[hsl(73,31%,45%)]/20 hover:shadow-xl hover:shadow-[hsl(73,31%,45%)]/30 hover:brightness-110 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2.5 active:scale-[0.98]"
            >
              <Sparkles className="w-4 h-4" />
              Generate Video Lecture
            </button>
          </div>

          {/* Minimal info row */}
          <div className="flex items-center justify-center gap-6 mt-6 text-[11px] text-muted-foreground/50">
            <span className="flex items-center gap-1.5"><Layers className="w-3 h-3" /> Animated slides</span>
            <span className="w-1 h-1 rounded-full bg-muted-foreground/20" />
            <span className="flex items-center gap-1.5"><Mic className="w-3 h-3" /> AI narration</span>
            <span className="w-1 h-1 rounded-full bg-muted-foreground/20" />
            <span className="flex items-center gap-1.5"><ImageIcon className="w-3 h-3" /> Auto images</span>
          </div>
        </div>
      </div>
    )
  }

  // ── Generating State ──
  if (status === 'generating' && !presentation) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center animate-fadeInUp max-w-sm">
          <Loader2 className="w-10 h-10 text-[hsl(73,31%,50%)] animate-spin mx-auto mb-5" />
          <h3 className="text-xl font-bold text-foreground mb-2 tracking-tight">Creating Your Lecture</h3>
          <p className="text-sm text-muted-foreground mb-6">{statusMessage || 'Preparing slides...'}</p>

          {/* Animated progress bar */}
          <div className="w-full h-1.5 bg-muted/50 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: statusMessage.includes('images') ? '70%' : statusMessage.includes('narration') ? '85%' : '40%',
                background: 'linear-gradient(90deg, hsl(73,31%,45%), hsl(73,40%,55%))',
              }}
            />
          </div>
          <div className="flex justify-between mt-2 text-[10px] text-muted-foreground/50">
            <span>Generating</span>
            <span>Complete</span>
          </div>
        </div>
      </div>
    )
  }

  // ── Presentation View ──
  if (presentation && presentation.slides.length > 0) {
    const guideContext = `Lecture topic: ${presentation.title}. ${presentation.subtitle || ''}. Currently on slide ${currentSlide + 1} of ${presentation.total_slides}: "${presentation.slides[currentSlide]?.title}". Slide content: ${presentation.slides[currentSlide]?.bullet_points?.join('; ')}`

    return (
      <>
      <div className="flex-1 flex flex-col min-h-0 p-4 gap-4 animate-fadeIn">
        {/* Header bar */}
        <div className="flex items-center justify-between px-1">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-foreground truncate tracking-tight">{presentation.title}</h2>
            {presentation.subtitle && (
              <p className="text-xs text-muted-foreground/70 truncate">{presentation.subtitle}</p>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground/60 shrink-0 ml-4">
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-muted/30">
              <Layers className="w-3 h-3" />
              {presentation.total_slides} slides
            </span>
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-muted/30">
              <Clock className="w-3 h-3" />
              ~{presentation.estimated_duration_minutes} min
            </span>
            {status === 'generating' && (
              <span className="flex items-center gap-1.5 text-[hsl(73,31%,55%)] px-2.5 py-1 rounded-lg bg-[hsl(73,31%,45%)]/10">
                <Loader2 className="w-3 h-3 animate-spin" />
                {generatedSlideCount}/{numSlides}
              </span>
            )}
            <button
              onClick={() => {
                setStatus('idle')
                setPresentation(null)
                setIsPlaying(false)
              }}
              className="px-3 py-1.5 rounded-lg border border-border/20 hover:bg-muted/40 text-muted-foreground hover:text-foreground transition-all duration-200 text-xs font-medium"
            >
              New Lecture
            </button>
          </div>
        </div>

        {/* Main area: Slides + Narration */}
        <div className="flex-1 flex gap-4 min-h-0">
          {/* Slide viewer */}
          <div className="flex-1 min-w-0">
            <SlideViewer
              slides={presentation.slides}
              title={presentation.title}
              subtitle={presentation.subtitle}
              currentSlide={currentSlide}
              onSlideChange={setCurrentSlide}
              isPlaying={isPlaying}
              onPlayToggle={togglePlay}
            />
          </div>

          {/* Right sidebar */}
          <div className="w-72 flex flex-col gap-3 shrink-0">
            {/* Narration panel */}
            {currentSlideData && (
              <VoiceNarration
                narrationText={currentSlideData.narration_text || currentSlideData.speaker_notes}
                audioBase64={currentSlideData.audio_base64}
                useBrowserTTS={currentSlideData.use_browser_tts ?? true}
                isActive={true}
                onNarrationEnd={handleNarrationEnd}
                autoPlay={isPlaying}
              />
            )}

            {/* Slide list */}
            <div className="flex-1 min-h-0 overflow-y-auto rounded-xl border border-white/[0.04] bg-slate-900/50 backdrop-blur-xl">
              <div className="px-3 py-2.5 border-b border-white/[0.04]">
                <span className="text-[10px] text-white/30 font-bold uppercase tracking-[0.15em]">
                  Slides
                </span>
              </div>
              <div className="p-1.5 space-y-0.5">
                {presentation.slides.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setCurrentSlide(i)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-xs transition-all duration-200 ${
                      i === currentSlide
                        ? 'bg-[hsl(73,31%,45%)]/15 text-[hsl(73,31%,70%)] border border-[hsl(73,31%,45%)]/20'
                        : 'text-white/40 hover:text-white/60 hover:bg-white/[0.03] border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`w-5 h-5 rounded-md shrink-0 flex items-center justify-center text-[10px] font-bold tabular-nums ${
                          i === currentSlide
                            ? 'bg-[hsl(73,31%,45%)] text-white shadow-sm'
                            : i < currentSlide
                            ? 'bg-[hsl(73,31%,45%)]/30 text-[hsl(73,31%,60%)]'
                            : 'bg-white/[0.06] text-white/30'
                        }`}
                      >
                        {i + 1}
                      </span>
                      <span className="truncate font-medium">{s.title}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Auto-advance toggle */}
            <label className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-slate-900/50 border border-white/[0.04] cursor-pointer transition-all hover:bg-slate-900/70">
              <input
                type="checkbox"
                checked={autoAdvance}
                onChange={(e) => setAutoAdvance(e.target.checked)}
                className="rounded border-white/20 bg-white/5 text-[hsl(73,31%,45%)] focus:ring-[hsl(73,31%,45%)]/30 w-3.5 h-3.5"
              />
              <span className="text-[11px] text-white/40 font-medium">Auto-advance after narration</span>
            </label>
          </div>
        </div>
      </div>
      <GuideChatbot mode="video-lecture" context={guideContext} title="Lecture Assistant" />
      </>
    )
  }

  return null
}
