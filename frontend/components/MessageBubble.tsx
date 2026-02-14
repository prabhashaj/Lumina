'use client'

import { useState, useRef } from 'react'
import { Message } from '@/lib/types'
import { User, Sparkles, Loader2, ExternalLink, Image as ImageIcon, ZoomIn, ZoomOut, X, Maximize2, Volume2, VolumeX, FileText, ArrowRight } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { textToSpeech } from '@/lib/api'

interface MessageBubbleProps {
  message: Message
  onFollowUpClick?: (text: string) => void
  isLast?: boolean
}

export default function MessageBubble({ message, onFollowUpClick, isLast }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const [lightbox, setLightbox] = useState<{ url: string; caption: string } | null>(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isLoadingTTS, setIsLoadingTTS] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

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

  // TTS: read aloud the explanation/tldr
  const handleSpeak = async () => {
    if (isSpeaking) {
      // Stop playback
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
      window.speechSynthesis?.cancel()
      setIsSpeaking(false)
      return
    }

    const textContent = message.explanation?.content || message.tldr || message.content || ''
    if (!textContent) return

    // Strip markdown for clean TTS
    const cleanText = textContent
      .replace(/#{1,6}\s/g, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/`(.*?)`/g, '$1')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .replace(/\n{2,}/g, '. ')
      .replace(/\n/g, ' ')
      .trim()

    setIsLoadingTTS(true)
    setIsSpeaking(true)

    try {
      const result = await textToSpeech(cleanText)

      if (result.audio) {
        // Use ElevenLabs audio
        const url = URL.createObjectURL(result.audio)
        const audio = new Audio(url)
        audioRef.current = audio

        audio.onended = () => {
          setIsSpeaking(false)
          URL.revokeObjectURL(url)
          audioRef.current = null
        }
        audio.onerror = () => {
          setIsSpeaking(false)
          URL.revokeObjectURL(url)
          audioRef.current = null
        }

        await audio.play()
      } else {
        // Fallback to browser TTS with soft female voice
        const utterance = new SpeechSynthesisUtterance(cleanText.slice(0, 3000))
        utterance.rate = 0.9
        utterance.pitch = 1.1
        // Try to select a female voice
        const voices = window.speechSynthesis.getVoices()
        const femaleVoice = voices.find(v => /female|zira|samantha|karen|fiona|victoria|susan/i.test(v.name)) || voices.find(v => /google.*us.*english/i.test(v.name))
        if (femaleVoice) utterance.voice = femaleVoice
        utterance.onend = () => setIsSpeaking(false)
        utterance.onerror = () => setIsSpeaking(false)
        window.speechSynthesis.speak(utterance)
      }
    } catch (err) {
      console.error('TTS error:', err)
      // Fallback to browser TTS with soft female voice
      const utterance = new SpeechSynthesisUtterance(cleanText.slice(0, 3000))
      utterance.rate = 0.9
      utterance.pitch = 1.1
      const voices = window.speechSynthesis.getVoices()
      const femaleVoice = voices.find(v => /female|zira|samantha|karen|fiona|victoria|susan/i.test(v.name)) || voices.find(v => /google.*us.*english/i.test(v.name))
      if (femaleVoice) utterance.voice = femaleVoice
      utterance.onend = () => setIsSpeaking(false)
      utterance.onerror = () => setIsSpeaking(false)
      window.speechSynthesis.speak(utterance)
    } finally {
      setIsLoadingTTS(false)
    }
  }

  if (isUser) {
    return (
      <div className="flex items-start gap-4 px-6 py-7 animate-fadeIn">
        <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-lg shadow-[hsl(73,31%,45%)]/15">
          <User className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1 space-y-2">
          <p className="text-foreground text-[15px] leading-relaxed whitespace-pre-wrap font-medium">{message.content}</p>
          {/* Show user attachments */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="flex gap-2 flex-wrap mt-2">
              {message.attachments.map((att, idx) => (
                <div key={idx} className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(73,31%,45%)]/8 border border-[hsl(73,31%,45%)]/15 rounded-xl text-xs">
                  {att.type === 'image' ? (
                    <>
                      {att.previewUrl && <img src={att.previewUrl} alt="" className="w-6 h-6 rounded object-cover" />}
                      <span className="text-[hsl(73,31%,45%)] font-medium">{att.name}</span>
                    </>
                  ) : (
                    <>
                      <FileText className="w-3.5 h-3.5 text-[hsl(73,31%,45%)]" />
                      <span className="text-[hsl(73,31%,45%)] font-medium">{att.name}</span>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="flex items-start gap-4 px-6 py-7 animate-fadeIn">
        <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-[hsl(73,31%,50%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-lg shadow-[hsl(73,31%,45%)]/15">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        
        <div className="flex-1 space-y-5">
          {/* Loading State */}
          {message.isLoading && !message.tldr && (
            <div className="bg-card/50 rounded-2xl px-6 py-5 border border-border/30 shadow-lg shadow-black/5">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Loader2 className="w-5 h-5 animate-spin text-[hsl(73,31%,45%)]" />
                  <div className="absolute inset-0 w-5 h-5 rounded-full bg-[hsl(73,31%,45%)]/15 animate-ping" />
                </div>
                <span className="text-muted-foreground/80 text-sm">
                  {message.status || 'Researching your question...'}
                </span>
              </div>
            </div>
          )}

          {/* Error State */}
          {message.error && (
            <div className="bg-red-500/8 border border-red-500/20 rounded-2xl px-6 py-4">
              <p className="text-red-400 text-sm">{message.error}</p>
            </div>
          )}

          {/* TL;DR (standalone when no explanation yet) */}
          {message.tldr && !message.explanation && (
            <div className="bg-gradient-to-r from-[hsl(73,31%,45%)]/8 to-transparent rounded-2xl px-6 py-4 border border-[hsl(73,31%,45%)]/20">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.tldr}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Explanation (with TL;DR summary at top) */}
          {message.explanation && (
            <div className="bg-card/50 rounded-2xl px-6 py-5 border border-border/30 shadow-lg shadow-black/5">
              {/* Topic Heading */}
              {message.topic && (
                <h2 className="text-lg font-semibold text-foreground mb-4">
                  {message.topic}
                </h2>
              )}
              {message.tldr && (
                <div className="mb-5 pb-4 border-b border-border/20">
                  <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:text-[19px] [&>p]:leading-relaxed [&>p]:text-foreground/85">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.tldr}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
              <div className="prose dark:prose-invert max-w-none explanation-content [&>p]:text-base [&>p]:font-normal [&>p]:leading-relaxed [&>p]:text-foreground/85">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    ol: ({ node, start, ...props }: any) => (
                      <ol {...props} start={1} />
                    )
                  }}
                >
                  {message.explanation.content || JSON.stringify(message.explanation)}
                </ReactMarkdown>
              </div>

              {/* TTS Button */}
              <div className="mt-4 pt-3 border-t border-border/20 flex items-center gap-2">
                <button
                  onClick={handleSpeak}
                  disabled={isLoadingTTS}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 ${
                    isSpeaking
                      ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20'
                      : 'bg-[hsl(73,31%,45%)]/8 text-[hsl(73,31%,45%)] hover:bg-[hsl(73,31%,45%)]/15 border border-[hsl(73,31%,45%)]/15'
                  }`}
                  title={isSpeaking ? 'Stop reading' : 'Read aloud'}
                >
                  {isLoadingTTS ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : isSpeaking ? (
                    <VolumeX className="w-3.5 h-3.5" />
                  ) : (
                    <Volume2 className="w-3.5 h-3.5" />
                  )}
                  <span>{isLoadingTTS ? 'Loading...' : isSpeaking ? 'Stop' : 'Read Aloud'}</span>
                </button>
              </div>
            </div>
          )}

          {/* Images - deduplicated, clickable with lightbox */}
          {message.images && message.images.length > 0 && (() => {
            const seen = new Set<string>();
            const uniqueImages = message.images.filter(img => {
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
                  {uniqueImages.map((img) => (
                    <div
                      key={img.url}
                      className="group relative rounded-2xl overflow-hidden bg-muted/50 border border-border/30 hover:border-[hsl(73,31%,45%)]/30 shadow-lg shadow-black/5 hover:shadow-xl transition-all duration-300 cursor-pointer"
                      onClick={() => openLightbox(img.url, (img.caption || img.alt_text || '').slice(0, 120))}
                    >
                      <div className="aspect-[16/10] overflow-hidden">
                        <img
                          src={img.url}
                          alt={img.alt_text || img.caption || 'Visual explanation'}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
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

          {/* Analogy */}
          {message.analogy && (
            <div className="bg-gradient-to-br from-amber-500/8 to-orange-500/5 rounded-2xl px-6 py-5 border border-amber-500/15">
              <h4 className="text-sm font-semibold text-amber-300 mb-3 flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center">
                  <span className="text-sm">💡</span>
                </div>
                Real-World Analogy
              </h4>
              <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:text-foreground/75">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.analogy}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Practice Questions - deduplicated */}
          {message.practiceQuestions && message.practiceQuestions.length > 0 && (() => {
            const seen = new Set<string>();
            const uniqueQuestions = message.practiceQuestions.filter(q => {
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
                  {uniqueQuestions.map((q, idx) => (
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

          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className="space-y-3 mt-5 pt-5 border-t border-border/20">
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-[hsl(73,31%,45%)]/12 flex items-center justify-center">
                  <ExternalLink className="w-3.5 h-3.5 text-[hsl(73,31%,45%)]" />
                </div>
                Sources
                <span className="text-xs text-muted-foreground font-normal">({message.sources.length})</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {message.sources.map((source, idx) => (
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

          {/* Follow-up Suggestions */}
          {isLast && message.complete && message.followUpSuggestions && message.followUpSuggestions.length > 0 && onFollowUpClick && (
            <div className="space-y-2 mt-2 animate-fadeIn">
              <p className="text-xs text-muted-foreground/60 font-medium uppercase tracking-wider">Continue exploring</p>
              <div className="flex flex-wrap gap-2">
                {message.followUpSuggestions.slice(0, 4).map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => onFollowUpClick(suggestion)}
                    className="group flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-card/50 border border-border/30 hover:border-[hsl(73,31%,45%)]/40 hover:bg-[hsl(73,31%,45%)]/5 text-xs text-muted-foreground hover:text-foreground transition-all duration-200 hover:-translate-y-0.5"
                  >
                    <span className="line-clamp-1">{suggestion}</span>
                    <ArrowRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-[hsl(73,31%,45%)]" />
                  </button>
                ))}
              </div>
            </div>
          )}

        
      </div>
    </div>

    {/* Lightbox Modal */}
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
            <ZoomOut className="w-4.5 h-4.5" />
          </button>
          <span className="text-white/70 text-xs font-medium min-w-[3rem] text-center bg-white/10 rounded-xl px-3 py-2 backdrop-blur-md">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className="p-2.5 bg-white/10 hover:bg-white/20 rounded-xl text-white transition-all duration-200 backdrop-blur-md"
            title="Zoom in"
          >
            <ZoomIn className="w-4.5 h-4.5" />
          </button>
          <button
            onClick={resetZoom}
            className="p-2.5 bg-white/10 hover:bg-white/20 rounded-xl text-white transition-all duration-200 backdrop-blur-md ml-1"
            title="Reset zoom"
          >
            <Maximize2 className="w-4.5 h-4.5" />
          </button>
          <button
            onClick={closeLightbox}
            className="p-2.5 bg-white/10 hover:bg-red-500/70 rounded-xl text-white transition-all duration-200 backdrop-blur-md ml-2"
            title="Close"
          >
            <X className="w-4.5 h-4.5" />
          </button>
        </div>

        {/* Image container */}
        <div className="relative z-[5] max-w-[90vw] max-h-[85vh] overflow-hidden rounded-2xl select-none shadow-2xl"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          style={{ cursor: zoom > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
        >
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
          <p className="text-white/40 text-xs">Scroll to zoom • Drag to pan • Click outside to close</p>
        </div>
      </div>
    )}
    </>
  )
}
