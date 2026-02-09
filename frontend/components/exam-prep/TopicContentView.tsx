'use client'

import { useState, useRef } from 'react'
import { TopicContent as TopicContentType, ImageData, Source } from '@/lib/types'
import {
  Sparkles,
  Loader2,
  ExternalLink,
  Image as ImageIcon,
  ZoomIn,
  ZoomOut,
  X,
  Maximize2,
  Volume2,
  VolumeX,
  ClipboardCheck,
  Lightbulb,
  HelpCircle,
  BookOpen,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { textToSpeech } from '@/lib/api'

interface TopicContentViewProps {
  topicTitle: string
  content: TopicContentType
  chapterTitle: string
  onTakeQuiz: () => void
}

export default function TopicContentView({
  topicTitle,
  content,
  chapterTitle,
  onTakeQuiz,
}: TopicContentViewProps) {
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
  const closeLightbox = () => { setLightbox(null); setZoom(1); setPan({ x: 0, y: 0 }) }
  const zoomIn = () => setZoom((p) => Math.min(p + 0.5, 5))
  const zoomOut = () => { setZoom((p) => { const n = Math.max(p - 0.5, 0.5); if (n <= 1) setPan({ x: 0, y: 0 }); return n }) }

  const handleMouseDown = (e: React.MouseEvent) => { if (zoom > 1) { setIsDragging(true); setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y }) } }
  const handleMouseMove = (e: React.MouseEvent) => { if (isDragging && zoom > 1) setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y }) }
  const handleMouseUp = () => setIsDragging(false)
  const handleWheel = (e: React.WheelEvent) => { e.preventDefault(); e.deltaY < 0 ? zoomIn() : zoomOut() }

  const handleSpeak = async () => {
    if (isSpeaking) {
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
      window.speechSynthesis?.cancel()
      setIsSpeaking(false)
      return
    }
    const text = content.explanation?.content || content.tldr || ''
    if (!text) return
    const cleanText = text.replace(/#{1,6}\s/g, '').replace(/\*\*(.*?)\*\*/g, '$1').replace(/\*(.*?)\*/g, '$1').replace(/`(.*?)`/g, '$1').replace(/\[(.*?)\]\(.*?\)/g, '$1').replace(/\n{2,}/g, '. ').replace(/\n/g, ' ').trim()
    setIsLoadingTTS(true); setIsSpeaking(true)
    try {
      const result = await textToSpeech(cleanText)
      if (result.audio) {
        const url = URL.createObjectURL(result.audio)
        const audio = new Audio(url)
        audioRef.current = audio
        audio.onended = () => { setIsSpeaking(false); URL.revokeObjectURL(url); audioRef.current = null }
        audio.onerror = () => { setIsSpeaking(false); URL.revokeObjectURL(url); audioRef.current = null }
        await audio.play()
      } else {
        const utterance = new SpeechSynthesisUtterance(cleanText.slice(0, 3000))
        utterance.rate = 0.9; utterance.pitch = 1.1
        const voices = window.speechSynthesis.getVoices()
        const femaleVoice = voices.find(v => /female|zira|samantha|karen|fiona/i.test(v.name))
        if (femaleVoice) utterance.voice = femaleVoice
        utterance.onend = () => setIsSpeaking(false)
        utterance.onerror = () => setIsSpeaking(false)
        window.speechSynthesis.speak(utterance)
      }
    } catch { setIsSpeaking(false) } finally { setIsLoadingTTS(false) }
  }

  // Deduplicate images
  const uniqueImages = (() => {
    if (!content.images) return []
    const seen = new Set<string>()
    return content.images.filter((img) => {
      if (seen.has(img.url)) return false
      seen.add(img.url)
      return true
    }).slice(0, 2)
  })()

  // Deduplicate practice questions
  const uniqueQuestions = (() => {
    if (!content.practiceQuestions) return []
    const seen = new Set<string>()
    return content.practiceQuestions.filter((q) => {
      const norm = q.toLowerCase().replace(/[^a-z0-9]/g, '')
      if (seen.has(norm)) return false
      seen.add(norm)
      return true
    }).slice(0, 5)
  })()

  return (
    <>
      <div className="space-y-5 animate-fadeIn">
        {/* TL;DR */}
        {content.tldr && (
          <div className="bg-gradient-to-r from-[hsl(73,31%,45%)]/8 to-transparent rounded-2xl px-6 py-4 border border-[hsl(73,31%,45%)]/20">
            <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:text-[20px] [&>p]:leading-relaxed [&>p]:text-foreground/85">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.tldr}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Explanation */}
        {content.explanation && (
          <div className="bg-card/50 rounded-2xl px-6 py-5 border border-border/30 shadow-lg shadow-black/5">
            <div className="prose dark:prose-invert max-w-none explanation-content [&>p]:text-base [&>p]:font-normal [&>p]:leading-relaxed [&>p]:text-foreground/85">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{ ol: ({ node, start, ...props }: any) => <ol {...props} start={1} /> }}
              >
                {content.explanation.content || JSON.stringify(content.explanation)}
              </ReactMarkdown>
            </div>

            {/* TTS */}
            <div className="mt-4 pt-3 border-t border-border/20 flex items-center gap-2">
              <button
                onClick={handleSpeak}
                disabled={isLoadingTTS}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 ${
                  isSpeaking
                    ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20'
                    : 'bg-[hsl(73,31%,45%)]/8 text-[hsl(73,31%,45%)] hover:bg-[hsl(73,31%,45%)]/15 border border-[hsl(73,31%,45%)]/15'
                }`}
              >
                {isLoadingTTS ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : isSpeaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                <span>{isLoadingTTS ? 'Loading...' : isSpeaking ? 'Stop' : 'Read Aloud'}</span>
              </button>
            </div>
          </div>
        )}

        {/* Images */}
        {uniqueImages.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-[hsl(73,31%,45%)]/10 flex items-center justify-center">
                <ImageIcon className="w-3.5 h-3.5 text-[hsl(73,31%,45%)]" />
              </div>
              Visual Explanations
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {uniqueImages.map((img) => (
                <div
                  key={img.url}
                  className="group relative rounded-2xl overflow-hidden bg-muted/30 border border-border/30 hover:border-[hsl(73,31%,45%)]/30 shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer"
                  onClick={() => openLightbox(img.url, img.caption || img.alt_text || '')}
                >
                  <div className="aspect-[16/10] overflow-hidden">
                    <img src={img.url} alt={img.alt_text || img.caption || ''} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                  </div>
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300 flex items-center justify-center">
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-white/90 dark:bg-black/70 rounded-full p-3 shadow-lg backdrop-blur-sm">
                      <Maximize2 className="w-5 h-5 text-foreground" />
                    </div>
                  </div>
                  {(img.caption || img.alt_text) && (
                    <div className="px-4 py-2.5 bg-card/80 border-t border-border/20">
                      <p className="text-xs text-muted-foreground line-clamp-2">{img.caption || img.alt_text}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analogy */}
        {content.analogy && (
          <div className="bg-gradient-to-r from-amber-500/8 to-transparent rounded-2xl px-6 py-4 border border-amber-500/15">
            <h4 className="text-sm font-semibold text-amber-500 mb-2 flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
              </div>
              Think of it this way...
            </h4>
            <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:text-sm [&>p]:text-foreground/75 [&>p]:leading-relaxed [&>ul]:text-sm [&>ul]:text-foreground/75 [&>ol]:text-sm [&>ol]:text-foreground/75 [&>h2]:text-base [&>h2]:text-foreground/85 [&>h2]:mt-4 [&>h2]:mb-2">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.analogy}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Practice Questions */}
        {uniqueQuestions.length > 0 && (
          <div className="bg-card/50 rounded-2xl px-6 py-5 border border-border/30">
            <h4 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-[hsl(73,31%,45%)]/10 flex items-center justify-center">
                <HelpCircle className="w-3.5 h-3.5 text-[hsl(73,31%,45%)]" />
              </div>
              Practice Questions
            </h4>
            <ul className="space-y-3">
              {uniqueQuestions.map((q, i) => (
                <li key={i} className="flex items-start gap-3 group">
                  <span className="flex-shrink-0 w-6 h-6 rounded-lg bg-[hsl(73,31%,45%)]/8 group-hover:bg-[hsl(73,31%,45%)]/15 flex items-center justify-center text-xs font-bold text-[hsl(73,31%,45%)] transition-colors mt-0.5">
                    {i + 1}
                  </span>
                  <span className="text-sm text-foreground/75 leading-relaxed">{q.replace(/^\*+|\*+$/g, '').trim()}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Sources */}
        {content.sources && content.sources.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-[hsl(73,31%,45%)]/10 flex items-center justify-center">
                <BookOpen className="w-3.5 h-3.5 text-[hsl(73,31%,45%)]" />
              </div>
              Sources
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {content.sources.slice(0, 4).map((src, i) => (
                <a key={i} href={src.url} target="_blank" rel="noopener noreferrer" className="flex items-start gap-2.5 p-3.5 bg-card/50 rounded-xl border border-border/30 hover:border-[hsl(73,31%,45%)]/25 hover:bg-card/80 transition-all duration-200 group">
                  <ExternalLink className="w-3.5 h-3.5 text-[hsl(73,31%,45%)] mt-0.5 flex-shrink-0 group-hover:scale-110 transition-transform" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-foreground truncate group-hover:text-[hsl(73,31%,45%)] transition-colors">{src.title}</p>
                    <p className="text-[11px] text-muted-foreground/60 truncate">{src.domain}</p>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Take Quiz Button */}
        <div className="pt-4 pb-2">
          <button
            onClick={onTakeQuiz}
            className="w-full flex items-center justify-center gap-2.5 px-6 py-4 rounded-2xl bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white font-semibold text-sm hover:shadow-xl hover:shadow-[hsl(73,31%,45%)]/25 hover:-translate-y-0.5 transition-all duration-300"
          >
            <ClipboardCheck className="w-5 h-5" />
            Take Quiz on "{topicTitle}"
          </button>
        </div>
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center lightbox-overlay" onClick={closeLightbox}>
          <div className="absolute top-4 right-4 flex items-center gap-2 z-10">
            <button onClick={(e) => { e.stopPropagation(); zoomOut() }} className="p-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors backdrop-blur-sm"><ZoomOut className="w-5 h-5" /></button>
            <span className="text-white text-sm font-medium min-w-[3rem] text-center bg-white/10 rounded-xl px-3 py-1.5 backdrop-blur-sm">{Math.round(zoom * 100)}%</span>
            <button onClick={(e) => { e.stopPropagation(); zoomIn() }} className="p-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors backdrop-blur-sm"><ZoomIn className="w-5 h-5" /></button>
            <button onClick={closeLightbox} className="p-2.5 rounded-xl bg-white/10 hover:bg-red-500/80 text-white ml-2 transition-colors backdrop-blur-sm"><X className="w-5 h-5" /></button>
          </div>
          <div className="max-w-[90vw] max-h-[85vh] overflow-hidden rounded-xl" onClick={(e) => e.stopPropagation()} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp} onWheel={handleWheel}>
            <img src={lightbox.url} alt={lightbox.caption} className="max-w-full max-h-[85vh] object-contain transition-transform duration-200" style={{ transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`, cursor: zoom > 1 ? 'grab' : 'zoom-in' }} />
          </div>
          {lightbox.caption && <p className="absolute bottom-6 left-1/2 -translate-x-1/2 text-white/80 text-sm bg-black/60 px-5 py-2.5 rounded-xl backdrop-blur-sm max-w-lg text-center border border-white/10">{lightbox.caption}</p>}
        </div>
      )}
    </>
  )
}
