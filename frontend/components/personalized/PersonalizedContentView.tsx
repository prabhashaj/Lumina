'use client'

import { useState, useEffect, useRef } from 'react'
import { TopicContent, PlanTopic, LearningPhase, LearnerProfile, ImageData, Source } from '@/lib/types'
import { streamPersonalizedContent } from '@/lib/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ArrowLeft,
  Loader2,
  CheckCircle2,
  BookOpen,
  Image as ImageIcon,
  Link2,
  Lightbulb,
  Brain,
  RefreshCw,
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  ExternalLink,
  Maximize2,
  ZoomIn,
  ZoomOut,
  X,
  Volume2,
  VolumeX,
  FileText,
} from 'lucide-react'

interface PersonalizedContentViewProps {
  subject: string
  topic: PlanTopic
  phase: LearningPhase
  profile: LearnerProfile
  onBack: () => void
  onMarkComplete: () => void
}

export default function PersonalizedContentView({
  subject,
  topic,
  phase,
  profile,
  onBack,
  onMarkComplete,
}: PersonalizedContentViewProps) {
  const [content, setContent] = useState<TopicContent | null>(topic.content || null)
  const [isGenerating, setIsGenerating] = useState(!topic.content)
  const [error, setError] = useState<string | null>(null)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    explanation: true,
    images: true,
    analogy: true,
    practice: true,
    sources: false,
  })
  const scrollRef = useRef<HTMLDivElement>(null)

  // Lightbox state (same as research mode)
  const [lightbox, setLightbox] = useState<{ url: string; caption: string } | null>(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  const openLightbox = (url: string, caption: string) => {
    setLightbox({ url, caption })
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }
  const closeLightbox = () => {
    setLightbox(null)
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }
  const zoomIn = () => setZoom(prev => Math.min(prev + 0.5, 5))
  const zoomOut = () => {
    setZoom(prev => {
      const newZoom = Math.max(prev - 0.5, 0.5)
      if (newZoom <= 1) setPan({ x: 0, y: 0 })
      return newZoom
    })
  }
  const resetZoom = () => { setZoom(1); setPan({ x: 0, y: 0 }) }
  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoom > 1) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
    }
  }
  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoom > 1) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
    }
  }
  const handleMouseUp = () => setIsDragging(false)
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    if (e.deltaY < 0) zoomIn()
    else zoomOut()
  }

  useEffect(() => {
    if (topic.content) {
      setContent(topic.content)
      setIsGenerating(false)
      return
    }
    generateContent()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topic.title])

  const generateContent = async () => {
    setIsGenerating(true)
    setError(null)

    const newContent: TopicContent = {}

    try {
      await streamPersonalizedContent(
        topic.title,
        profile.knowledgeLevel,
        profile.weaknessAreas,
        profile.strengthAreas,
        profile.recommendedStyle,
        topic.approach,
        phase.title,
        subject,
        (chunk) => {
          switch (chunk.type) {
            case 'tldr':
              newContent.tldr = chunk.data
              setContent({ ...newContent })
              break
            case 'explanation':
              newContent.explanation = chunk.data
              setContent({ ...newContent })
              break
            case 'image':
              newContent.images = [...(newContent.images || []), chunk.data]
              setContent({ ...newContent })
              break
            case 'source':
              newContent.sources = [...(newContent.sources || []), chunk.data]
              setContent({ ...newContent })
              break
            case 'analogy':
              newContent.analogy = chunk.data
              setContent({ ...newContent })
              break
            case 'practice_question':
              newContent.practiceQuestions = [...(newContent.practiceQuestions || []), chunk.data]
              setContent({ ...newContent })
              break
            case 'error':
              setError(chunk.data)
              break
            case 'complete':
              setIsGenerating(false)
              break
          }
        }
      )
    } catch (err: any) {
      setError(err.message || 'Failed to generate content')
      setIsGenerating(false)
    }
  }

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-border/20 bg-card/30 backdrop-blur-sm">
        <button
          onClick={onBack}
          className="p-2 rounded-xl hover:bg-muted/40 text-muted-foreground hover:text-foreground transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-foreground truncate">{topic.title}</div>
          <div className="text-xs text-muted-foreground">
            {phase.title} • {profile.knowledgeLevel} level •{' '}
            <span className="text-[hsl(73,31%,50%)]">{profile.recommendedStyle}</span> style
          </div>
        </div>
        {!isGenerating && content && (
          <div className="flex items-center gap-2">
            <button
              onClick={generateContent}
              className="p-2 rounded-xl hover:bg-muted/40 text-muted-foreground hover:text-foreground transition-all"
              title="Regenerate"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onMarkComplete}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-600 to-emerald-700 text-white shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 transition-all"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Mark Complete
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
          {/* Personalization banner */}
          <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-gradient-to-r from-[hsl(73,31%,45%)]/10 to-[hsl(73,40%,38%)]/10 border border-[hsl(73,31%,45%)]/20">
            <Brain className="w-5 h-5 text-[hsl(73,31%,50%)] flex-shrink-0 mt-0.5" />
            <div className="text-xs text-foreground/70">
              <span className="font-semibold text-[hsl(73,31%,55%)]">Personalized for you</span> — This content is tailored to your{' '}
              <span className="text-[hsl(73,31%,55%)]">{profile.knowledgeLevel}</span> level using a{' '}
              <span className="text-[hsl(73,31%,55%)]">{profile.recommendedStyle}</span> approach.
              {topic.approach && <> Focus: {topic.approach}</>}
            </div>
          </div>

          {/* Loading state */}
          {isGenerating && !content?.tldr && (
            <div className="flex flex-col items-center gap-4 py-16">
              <div className="relative animate-fadeIn">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-xl shadow-[hsl(73,31%,45%)]/20">
                  <Loader2 className="w-7 h-7 text-white animate-spin" />
                </div>
                <div className="absolute -inset-3 rounded-[24px] bg-[hsl(73,31%,45%)]/8 animate-pulse-glow" />
              </div>
              <p className="text-sm text-muted-foreground animate-pulse">
                Personalizing content for your learning level...
              </p>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-400">Error generating content</p>
                <p className="text-xs text-muted-foreground mt-1">{error}</p>
                <button
                  onClick={generateContent}
                  className="mt-2 text-xs text-[hsl(73,31%,50%)] hover:underline flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" /> Try again
                </button>
              </div>
            </div>
          )}

          {/* TL;DR — same style as research mode */}
          {content?.tldr && !content?.explanation && (
            <div className="bg-gradient-to-r from-[hsl(73,31%,45%)]/8 to-transparent rounded-2xl px-6 py-4 border border-[hsl(73,31%,45%)]/20">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {content.tldr}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Explanation — same card as research mode */}
          {content?.explanation && (
            <div className="bg-card/50 rounded-2xl px-6 py-5 border border-border/30 shadow-lg shadow-black/5">
              {/* Topic Heading */}
              <h2 className="text-lg font-semibold text-foreground mb-4">
                {topic.title}
              </h2>
              {/* TL;DR at top of explanation card */}
              {content.tldr && (
                <div className="mb-5 pb-4 border-b border-border/20">
                  <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:text-[19px] [&>p]:leading-relaxed [&>p]:text-foreground/85">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {content.tldr}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
              {/* Main explanation content */}
              <div className="prose dark:prose-invert max-w-none explanation-content [&>p]:text-base [&>p]:font-normal [&>p]:leading-relaxed [&>p]:text-foreground/85">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    ol: ({ node, start, ...props }: any) => (
                      <ol {...props} start={1} />
                    )
                  }}
                >
                  {typeof content.explanation === 'string'
                    ? content.explanation
                    : content.explanation?.content
                      ? (content.explanation.subsections?.length
                          ? content.explanation.content + '\n\n' + content.explanation.subsections.map((sub: any) => `### ${sub.title}\n${sub.content}`).join('\n\n')
                          : content.explanation.content)
                      : JSON.stringify(content.explanation)}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Images — same style as research mode with lightbox */}
          {content?.images && content.images.length > 0 && (() => {
            const seen = new Set<string>();
            const uniqueImages = content.images.filter((img: ImageData) => {
              if (seen.has(img.url)) return false;
              seen.add(img.url);
              return true;
            }).slice(0, 2);
            return (
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <ImageIcon className="w-4 h-4 text-[hsl(73,31%,45%)]" />
                  Visual Explanations
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {uniqueImages.map((img: ImageData) => (
                    <div
                      key={img.url}
                      className="group relative rounded-2xl overflow-hidden bg-muted/50 border border-border/30 hover:border-[hsl(73,31%,45%)]/30 shadow-lg shadow-black/5 hover:shadow-xl transition-all duration-300 cursor-pointer"
                      onClick={() => openLightbox(img.url, img.caption || img.alt_text || '')}
                    >
                      <div className="aspect-[16/10] overflow-hidden">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={img.url}
                          alt={img.alt_text || img.caption || 'Visual explanation'}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none'
                          }}
                        />
                      </div>
                      {/* Hover overlay */}
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors duration-300 flex items-center justify-center">
                        <div className="opacity-0 group-hover:opacity-100 transition-all duration-300 scale-75 group-hover:scale-100 bg-black/60 backdrop-blur-md rounded-xl p-3 shadow-lg">
                          <Maximize2 className="w-5 h-5 text-foreground" />
                        </div>
                      </div>
                      {img.caption && (
                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-3 pt-8">
                          <p className="text-xs text-white/90 line-clamp-2 leading-relaxed">{img.caption}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Analogy — same style as research mode */}
          {content?.analogy && (
            <div className="bg-gradient-to-br from-amber-500/8 to-orange-500/5 rounded-2xl px-6 py-5 border border-amber-500/15">
              <h4 className="text-sm font-semibold text-amber-300 mb-3 flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center">
                  <span className="text-sm">💡</span>
                </div>
                Real-World Analogy
              </h4>
              <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:text-foreground/75">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {content.analogy}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Practice Questions — same style as research mode */}
          {content?.practiceQuestions && content.practiceQuestions.length > 0 && (() => {
            const seen = new Set<string>();
            const uniqueQuestions = content.practiceQuestions.filter((q: string) => {
              const normalized = q.toLowerCase().replace(/[?.!,]/g, '').trim();
              if (seen.has(normalized)) return false;
              seen.add(normalized);
              return true;
            }).slice(0, 5);
            return (
              <div className="bg-card/50 rounded-2xl px-6 py-5 border border-border/30 shadow-lg shadow-black/5">
                <h4 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-[hsl(73,31%,45%)]/12 flex items-center justify-center">
                    <span className="text-sm">📝</span>
                  </div>
                  Practice Questions
                </h4>
                <ol className="space-y-3">
                  {uniqueQuestions.map((q: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-3 group">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[hsl(73,31%,45%)]/15 group-hover:bg-[hsl(73,31%,45%)]/25 flex items-center justify-center text-xs font-bold text-[hsl(73,31%,45%)] transition-colors mt-0.5">
                        {idx + 1}
                      </span>
                      <span className="text-foreground/85 text-sm leading-relaxed">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          className="inline"
                          components={{
                            p: ({ children }) => <span>{children}</span>
                          }}
                        >
                          {q.replace(/^\*+|\*+$/g, '').trim()}
                        </ReactMarkdown>
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            );
          })()}

          {/* Sources — same style as research mode */}
          {content?.sources && content.sources.length > 0 && (
            <div className="space-y-3 mt-5 pt-5 border-t border-border/20">
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-[hsl(73,31%,45%)]/12 flex items-center justify-center">
                  <ExternalLink className="w-3.5 h-3.5 text-[hsl(73,31%,45%)]" />
                </div>
                Sources
                <span className="text-xs text-muted-foreground font-normal">({content.sources.length})</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {content.sources.map((source: Source, idx: number) => (
                  <a
                    key={idx}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group p-3.5 bg-card/40 rounded-xl border border-border/25 hover:bg-[hsl(73,31%,45%)]/5 hover:border-[hsl(73,31%,45%)]/25 transition-all duration-200 hover:-translate-y-0.5"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-md bg-[hsl(73,31%,45%)]/10 group-hover:bg-[hsl(73,31%,45%)]/20 flex items-center justify-center text-[10px] font-bold text-[hsl(73,31%,45%)] transition-colors">
                        {idx + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground/90 line-clamp-2 group-hover:text-[hsl(73,31%,45%)] mb-0.5 transition-colors leading-snug">
                          {source.title}
                        </p>
                        <p className="text-[11px] text-muted-foreground/60">
                          {source.domain}
                        </p>
                      </div>
                      <ExternalLink className="w-3 h-3 text-muted-foreground/40 group-hover:text-[hsl(73,31%,45%)] flex-shrink-0 transition-colors mt-0.5" />
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Loading indicator for streaming */}
          {isGenerating && content?.tldr && (
            <div className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-[hsl(73,31%,50%)]" />
              <span className="animate-pulse">Generating more personalized content...</span>
            </div>
          )}

          {/* Bottom padding */}
          <div className="h-8" />
        </div>
      </div>

      {/* Lightbox Modal — same as research mode */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center lightbox-overlay"
          onClick={(e) => { if (e.target === e.currentTarget) closeLightbox() }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/85 backdrop-blur-md" />

          {/* Controls */}
          <div className="absolute top-4 right-4 z-10 flex items-center gap-1.5">
            <button
              onClick={zoomOut}
              className="p-2.5 bg-white/10 hover:bg-white/20 rounded-xl text-white transition-all duration-200 backdrop-blur-md"
              title="Zoom out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-white/70 text-xs font-medium min-w-[3rem] text-center bg-white/10 rounded-xl px-3 py-2 backdrop-blur-md">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={zoomIn}
              className="p-2.5 bg-white/10 hover:bg-white/20 rounded-xl text-white transition-all duration-200 backdrop-blur-md"
              title="Zoom in"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={resetZoom}
              className="p-2.5 bg-white/10 hover:bg-white/20 rounded-xl text-white transition-all duration-200 backdrop-blur-md ml-1"
              title="Reset zoom"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            <button
              onClick={closeLightbox}
              className="p-2.5 bg-white/10 hover:bg-red-500/70 rounded-xl text-white transition-all duration-200 backdrop-blur-md ml-2"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Image container */}
          <div
            className="relative z-[5] max-w-[90vw] max-h-[85vh] overflow-hidden rounded-2xl select-none shadow-2xl"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            style={{ cursor: zoom > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={lightbox.url}
              alt={lightbox.caption}
              className="max-w-[90vw] max-h-[85vh] object-contain transition-transform duration-200 ease-out"
              style={{
                transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
              }}
              draggable={false}
            />
          </div>

          {/* Caption */}
          {lightbox.caption && (
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 max-w-2xl">
              <div className="bg-black/60 backdrop-blur-md rounded-xl px-5 py-3 border border-white/10">
                <p className="text-white/90 text-sm text-center leading-relaxed">{lightbox.caption}</p>
              </div>
            </div>
          )}

          {/* Keyboard hint */}
          <div className="absolute bottom-6 right-6 z-10">
            <p className="text-white/40 text-xs">Scroll to zoom · Drag to pan · Click outside to close</p>
          </div>
        </div>
      )}
    </div>
  )
}
