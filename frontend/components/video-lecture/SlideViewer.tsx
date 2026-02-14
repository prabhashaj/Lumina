'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Play,
  Pause,
  Maximize2,
  Minimize2,
  RotateCcw,
  Clock,
  ImageIcon,
} from 'lucide-react'
import { Slide } from '@/lib/types'

interface SlideViewerProps {
  slides: Slide[]
  title: string
  subtitle: string
  currentSlide: number
  onSlideChange: (index: number) => void
  isPlaying: boolean
  onPlayToggle: () => void
}

// Resolve image URL: prefer backend-resolved URL
function getImageUrl(slide: Slide): string {
  if (slide.image_url) return slide.image_url
  return ''
}

// Normalize bullet_points: LLM sometimes returns objects instead of plain strings.
// Handles: {column, points}, {left_column, right_column}, {text}, etc.
function normalizeBullets(bullets: any[]): string[] {
  if (!bullets || !Array.isArray(bullets)) return []
  const result: string[] = []

  function addItem(item: any) {
    if (typeof item === 'string') {
      // Strip markdown bold markers: **text** → text
      const cleaned = item.replace(/\*\*/g, '').replace(/^[•·\-]\s*/, '').trim()
      if (cleaned) result.push(cleaned)
    } else if (Array.isArray(item)) {
      item.forEach(addItem)
    } else if (item && typeof item === 'object') {
      // {left_column: [...], right_column: [...]}
      if (item.left_column || item.right_column) {
        const leftTitle = Array.isArray(item.left_column) ? item.left_column[0] : item.left_column
        const rightTitle = Array.isArray(item.right_column) ? item.right_column[0] : item.right_column
        const leftPoints = Array.isArray(item.left_column) ? item.left_column.slice(1) : []
        const rightPoints = Array.isArray(item.right_column) ? item.right_column.slice(1) : []
        if (leftTitle) addItem(String(leftTitle))
        leftPoints.forEach((p: any) => addItem(p))
        if (rightTitle) addItem(String(rightTitle))
        rightPoints.forEach((p: any) => addItem(p))
        return
      }
      // {column: "...", points: [...]}
      if (item.column) addItem(item.column)
      if (Array.isArray(item.points)) item.points.forEach((p: any) => addItem(p))
      if (item.column || item.points) return
      // Generic object — try common text keys
      const text = item.text || item.content || item.label || item.title || item.value || item.name || item.description
      if (text) addItem(String(text))
      // Skip entirely if no recognizable text (don't render JSON)
    } else if (item != null) {
      result.push(String(item))
    }
  }

  for (const b of bullets) addItem(b)
  return result
}

// Render bullet text: parse **bold** markers and numbered prefixes into styled spans
function renderBulletText(text: string, accentColor: string): React.ReactNode {
  // Split on **...**  patterns
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  if (parts.length === 1) {
    // Check for "N. Title: rest" pattern (e.g. "1. Goal Definition: Aligns with...")
    const numberedMatch = text.match(/^(\d+\.\s*)([^:]+)(:.*)/)
    if (numberedMatch) {
      return (
        <>
          <span style={{ color: accentColor, fontWeight: 700 }}>{numberedMatch[1]}{numberedMatch[2]}</span>
          <span>{numberedMatch[3]}</span>
        </>
      )
    }
    return text
  }
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const inner = part.slice(2, -2)
      return <strong key={i} style={{ color: accentColor, fontWeight: 700 }}>{inner}</strong>
    }
    return <span key={i}>{part}</span>
  })
}

// Marker colors for the whiteboard theme
const MARKER_COLORS = [
  { primary: '#1a3a5c', accent: '#2563eb' },   // Dark blue
  { primary: '#1e4d3a', accent: '#16a34a' },   // Dark green
  { primary: '#5c1a2a', accent: '#dc2626' },   // Dark red
  { primary: '#4a2d1a', accent: '#d97706' },   // Brown/amber
  { primary: '#2d1a5c', accent: '#7c3aed' },   // Purple
  { primary: '#1a4a5c', accent: '#0891b2' },   // Teal
  { primary: '#5c3a1a', accent: '#ea580c' },   // Orange
  { primary: '#1a5c4a', accent: '#059669' },   // Emerald
]

function getMarkerColor(index: number) {
  return MARKER_COLORS[index % MARKER_COLORS.length]
}

// Sketch-style irregular border radius
function getSketchBorderRadius(seed: number): string {
  const variations = [
    '255px 15px 225px 15px / 15px 225px 15px 255px',
    '15px 225px 15px 255px / 255px 15px 225px 15px',
    '225px 15px 255px 15px / 15px 255px 15px 225px',
    '15px 255px 15px 225px / 225px 15px 255px 15px',
  ]
  return variations[seed % variations.length]
}

export default function SlideViewer({
  slides,
  title,
  subtitle,
  currentSlide,
  onSlideChange,
  isPlaying,
  onPlayToggle,
}: SlideViewerProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [slideDirection, setSlideDirection] = useState<'left' | 'right'>('right')
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [isVisible, setIsVisible] = useState(true)
  const containerRef = useRef<HTMLDivElement>(null)
  const [loadedImages, setLoadedImages] = useState<Record<number, string>>({})
  const [failedImages, setFailedImages] = useState<Set<number>>(new Set())
  const [hoveredNav, setHoveredNav] = useState<'left' | 'right' | null>(null)

  const slide = slides[currentSlide]
  const markerColor = getMarkerColor(currentSlide)

  // Normalize bullet_points for current slide to ensure they are plain strings
  const safeBullets = slide ? normalizeBullets(slide.bullet_points) : []

  // Preload images for nearby slides
  useEffect(() => {
    const toLoad = [currentSlide - 1, currentSlide, currentSlide + 1].filter(
      (i) => i >= 0 && i < slides.length && !loadedImages[i] && !failedImages.has(i)
    )
    toLoad.forEach((i) => {
      const url = getImageUrl(slides[i])
      if (!url) return
      const img = new Image()
      img.src = url
      img.onload = () => setLoadedImages((prev) => ({ ...prev, [i]: url }))
      img.onerror = () => setFailedImages((prev) => new Set(prev).add(i))
      setLoadedImages((prev) => ({ ...prev, [i]: url }))
    })
  }, [currentSlide, slides])

  const goToSlide = useCallback(
    (index: number) => {
      if (index === currentSlide || isTransitioning) return
      const direction = index > currentSlide ? 'right' : 'left'
      setSlideDirection(direction)
      setIsVisible(false)
      setIsTransitioning(true)
      setTimeout(() => {
        onSlideChange(index)
        setSlideDirection(direction)
        setTimeout(() => {
          setIsVisible(true)
          setIsTransitioning(false)
        }, 60)
      }, 280)
    },
    [currentSlide, isTransitioning, onSlideChange]
  )

  const nextSlide = useCallback(() => {
    if (currentSlide < slides.length - 1) goToSlide(currentSlide + 1)
  }, [currentSlide, slides.length, goToSlide])

  const prevSlide = useCallback(() => {
    if (currentSlide > 0) goToSlide(currentSlide - 1)
  }, [currentSlide, goToSlide])

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      // Don't intercept keys when user is typing in an input or textarea
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return

      if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); nextSlide() }
      if (e.key === 'ArrowLeft') { e.preventDefault(); prevSlide() }
      if (e.key === 'f' || e.key === 'F') toggleFullscreen()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [nextSlide, prevSlide])

  const toggleFullscreen = () => {
    if (!document.fullscreenElement && containerRef.current) {
      containerRef.current.requestFullscreen()
      setIsFullscreen(true)
    } else if (document.fullscreenElement) {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handler)
    return () => document.removeEventListener('fullscreenchange', handler)
  }, [])

  if (!slide) return null

  const imageUrl = loadedImages[currentSlide] || getImageUrl(slide)
  const hasImage = !!imageUrl && !failedImages.has(currentSlide)
  const progress = ((currentSlide + 1) / slides.length) * 100

  return (
    <div
      ref={containerRef}
      className={`relative flex flex-col overflow-hidden shadow-2xl ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : 'rounded-2xl'
      }`}
      style={{
        '--marker-primary': markerColor.primary,
        '--marker-accent': markerColor.accent,
      } as React.CSSProperties}
    >
      {/* ── SVG Filter for sketch effect ── */}
      <svg width="0" height="0" className="absolute">
        <defs>
          <filter id="sketchy">
            <feTurbulence type="turbulence" baseFrequency="0.03" numOctaves="4" result="noise" seed="1" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.5" xChannelSelector="R" yChannelSelector="G" />
          </filter>
          <filter id="sketchy-strong">
            <feTurbulence type="turbulence" baseFrequency="0.04" numOctaves="3" result="noise" seed="2" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.5" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
      </svg>

      {/* ── Main Slide Area (Whiteboard) ── */}
      <div className="relative flex-1 min-h-[420px] overflow-hidden whiteboard-bg">
        {/* Whiteboard texture - dot grid */}
        <div className="absolute inset-0 whiteboard-grid opacity-40" />
        
        {/* Subtle whiteboard edge shadow */}
        <div className="absolute inset-0 pointer-events-none"
          style={{
            boxShadow: 'inset 0 0 60px rgba(0,0,0,0.06), inset 0 0 20px rgba(0,0,0,0.03)',
          }}
        />

        {/* Marker tray decoration — top left */}
        <div className="absolute top-4 left-4 flex items-center gap-1.5 z-20 opacity-60">
          {MARKER_COLORS.slice(0, 5).map((c, i) => (
            <div
              key={i}
              className={`w-2.5 h-2.5 rounded-full transition-all duration-300 ${
                i === currentSlide % 5 ? 'scale-125 ring-2 ring-offset-1' : ''
              }`}
              style={{
                background: c.accent,
                '--tw-ring-color': c.accent,
              } as React.CSSProperties}
            />
          ))}
        </div>

        {/* Slide content — animated */}
        <div
          className={`relative z-10 h-full flex slide-content-wrapper ${
            isVisible ? 'slide-enter-active' : 'slide-exit-active'
          } ${slideDirection === 'right' ? 'slide-from-right' : 'slide-from-left'}`}
        >
          {/* ─── Title Layout ─── */}
          {slide.layout === 'title' && (
            <div className="flex flex-col items-center justify-center w-full px-12 py-16 text-center">
              {/* Hand-drawn underline that animates in */}
              <svg className="w-32 h-3 mb-6 sketch-draw-line" viewBox="0 0 120 10" fill="none">
                <path
                  d="M2 7 C20 3, 40 8, 60 5 C80 2, 100 7, 118 4"
                  stroke={markerColor.accent}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  className="sketch-path"
                />
              </svg>
              <h1
                className="text-4xl md:text-5xl lg:text-6xl font-bold mb-5 leading-[1.1] tracking-tight sketch-title font-caveat"
                style={{ color: markerColor.primary }}
              >
                {slide.title}
              </h1>
              {safeBullets.length > 0 && (
                <p
                  className="text-lg md:text-xl max-w-2xl font-patrick sketch-subtitle"
                  style={{ color: `${markerColor.primary}99` }}
                >
                  {safeBullets[0]}
                </p>
              )}
              {/* Hand-drawn decorative squiggle */}
              <svg className="w-48 h-4 mt-8 sketch-draw-line" viewBox="0 0 200 16" fill="none" style={{ animationDelay: '0.6s' }}>
                <path
                  d="M4 8 C20 2, 30 14, 50 8 C70 2, 80 14, 100 8 C120 2, 130 14, 150 8 C170 2, 180 14, 196 8"
                  stroke={markerColor.accent}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeOpacity="0.4"
                  className="sketch-path-long"
                />
              </svg>
            </div>
          )}

          {/* ─── Default Layout (bullets + side image) ─── */}
          {slide.layout === 'default' && (
            <div className="flex w-full">
              <div className="flex-1 flex flex-col justify-center px-10 md:px-12 py-10">
                {/* Slide number — hand-drawn circle */}
                <div className="flex items-center gap-3 mb-5">
                  <div className="relative sketch-number-badge">
                    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" className="absolute inset-0">
                      <ellipse
                        cx="18" cy="18" rx="15" ry="14"
                        stroke={markerColor.accent}
                        strokeWidth="2"
                        fill="none"
                        className="sketch-circle"
                        style={{ filter: 'url(#sketchy)' }}
                      />
                    </svg>
                    <span
                      className="relative z-10 w-9 h-9 flex items-center justify-center text-sm font-bold font-caveat"
                      style={{ color: markerColor.accent }}
                    >
                      {slide.slide_number}
                    </span>
                  </div>
                </div>
                <h2
                  className="text-2xl md:text-3xl lg:text-4xl font-bold mb-2 leading-tight tracking-tight sketch-title font-caveat"
                  style={{ color: markerColor.primary }}
                >
                  {slide.title}
                </h2>
                {/* Hand-drawn underline under title */}
                <svg className="w-full max-w-[200px] h-3 mb-6 sketch-draw-line" viewBox="0 0 200 10" fill="none">
                  <path
                    d="M2 6 C40 2, 80 9, 120 5 C140 3, 170 7, 198 4"
                    stroke={markerColor.accent}
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeOpacity="0.5"
                    className="sketch-path"
                  />
                </svg>
                <ul className="space-y-4">
                  {safeBullets.map((point, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-4 text-base md:text-lg sketch-bullet font-patrick"
                      style={{ animationDelay: `${200 + i * 150}ms`, color: '#2d3748' }}
                    >
                      {/* Hand-drawn bullet marker */}
                      <span className="mt-1.5 shrink-0">
                        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                          <path
                            d={`M${3 + (i % 2)}  ${9 + (i % 3)} L${8 - (i % 2)} ${13 + (i % 2)} L${15 - (i % 2)} ${4 + (i % 2)}`}
                            stroke={markerColor.accent}
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            style={{ filter: 'url(#sketchy)' }}
                          />
                        </svg>
                      </span>
                      <span className="leading-relaxed">{renderBulletText(point, markerColor.accent)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="hidden md:flex w-[38%] items-center justify-center p-6 pr-8">
                {hasImage ? (
                  <div
                    className="relative w-full aspect-[4/3] overflow-hidden shadow-lg sketch-image-box group"
                    style={{
                      borderRadius: getSketchBorderRadius(currentSlide),
                      border: `3px solid ${markerColor.accent}44`,
                    }}
                  >
                    <img
                      src={imageUrl}
                      alt={slide.image_query}
                      className="w-full h-full object-contain bg-white/50 transition-transform duration-700 group-hover:scale-105"
                      loading="lazy"
                      onError={() => setFailedImages((prev) => new Set(prev).add(currentSlide))}
                    />
                    {/* Sketch corner decorations */}
                    <svg className="absolute top-0 left-0 w-8 h-8" viewBox="0 0 30 30" fill="none">
                      <path d="M2 28 L2 4 L26 4" stroke={markerColor.accent} strokeWidth="2.5" strokeLinecap="round" opacity="0.6" style={{ filter: 'url(#sketchy)' }} />
                    </svg>
                    <svg className="absolute bottom-0 right-0 w-8 h-8" viewBox="0 0 30 30" fill="none">
                      <path d="M28 2 L28 26 L4 26" stroke={markerColor.accent} strokeWidth="2.5" strokeLinecap="round" opacity="0.6" style={{ filter: 'url(#sketchy)' }} />
                    </svg>
                  </div>
                ) : (
                  <div
                    className="relative w-full aspect-[4/3] overflow-hidden flex flex-col items-center justify-center gap-3 sketch-image-box"
                    style={{
                      borderRadius: getSketchBorderRadius(currentSlide),
                      border: `2px dashed ${markerColor.accent}33`,
                      background: `${markerColor.accent}08`,
                    }}
                  >
                    <ImageIcon className="w-10 h-10" style={{ color: `${markerColor.accent}33` }} />
                    <span className="text-xs font-patrick" style={{ color: `${markerColor.accent}44` }}>sketch area</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ─── Image Focus Layout ─── */}
          {slide.layout === 'image-focus' && (
            <div className="flex flex-col items-center justify-center w-full px-10 py-8">
              <div className="flex items-center gap-3 mb-5">
                <div className="relative sketch-number-badge">
                  <svg width="36" height="36" viewBox="0 0 36 36" fill="none" className="absolute inset-0">
                    <ellipse cx="18" cy="18" rx="15" ry="14" stroke={markerColor.accent} strokeWidth="2" fill="none" className="sketch-circle" style={{ filter: 'url(#sketchy)' }} />
                  </svg>
                  <span className="relative z-10 w-9 h-9 flex items-center justify-center text-sm font-bold font-caveat" style={{ color: markerColor.accent }}>
                    {slide.slide_number}
                  </span>
                </div>
              </div>
              <h2
                className="text-2xl md:text-3xl font-bold mb-6 tracking-tight sketch-title font-caveat"
                style={{ color: markerColor.primary }}
              >
                {slide.title}
              </h2>
              {hasImage ? (
                <div
                  className="relative w-full max-w-3xl aspect-video overflow-hidden shadow-lg mb-6 sketch-image-box group"
                  style={{
                    borderRadius: getSketchBorderRadius(currentSlide + 1),
                    border: `3px solid ${markerColor.accent}44`,
                  }}
                >
                  <img
                    src={imageUrl}
                    alt={slide.image_query}
                    className="w-full h-full object-contain bg-white/50 transition-transform duration-700 group-hover:scale-105"
                    loading="lazy"
                    onError={() => setFailedImages((prev) => new Set(prev).add(currentSlide))}
                  />
                  {/* Sketch corners */}
                  <svg className="absolute top-0 left-0 w-8 h-8" viewBox="0 0 30 30" fill="none">
                    <path d="M2 28 L2 4 L26 4" stroke={markerColor.accent} strokeWidth="2.5" strokeLinecap="round" opacity="0.5" style={{ filter: 'url(#sketchy)' }} />
                  </svg>
                  <svg className="absolute bottom-0 right-0 w-8 h-8" viewBox="0 0 30 30" fill="none">
                    <path d="M28 2 L28 26 L4 26" stroke={markerColor.accent} strokeWidth="2.5" strokeLinecap="round" opacity="0.5" style={{ filter: 'url(#sketchy)' }} />
                  </svg>
                </div>
              ) : (
                <div
                  className="relative w-full max-w-3xl aspect-video overflow-hidden mb-6 flex items-center justify-center sketch-image-box"
                  style={{
                    borderRadius: getSketchBorderRadius(currentSlide + 1),
                    border: `2px dashed ${markerColor.accent}33`,
                    background: `${markerColor.accent}08`,
                  }}
                >
                  <ImageIcon className="w-14 h-14" style={{ color: `${markerColor.accent}22` }} />
                </div>
              )}
              {safeBullets.length > 0 && (
                <p className="text-center max-w-2xl font-patrick sketch-subtitle" style={{ color: `${markerColor.primary}88` }}>
                  {safeBullets.join(' · ')}
                </p>
              )}
            </div>
          )}

          {/* ─── Comparison Layout ─── */}
          {slide.layout === 'comparison' && (
            <div className="flex flex-col w-full px-10 md:px-12 py-10">
              <div className="flex items-center gap-3 mb-4 justify-center">
                <div className="relative sketch-number-badge">
                  <svg width="36" height="36" viewBox="0 0 36 36" fill="none" className="absolute inset-0">
                    <ellipse cx="18" cy="18" rx="15" ry="14" stroke={markerColor.accent} strokeWidth="2" fill="none" className="sketch-circle" style={{ filter: 'url(#sketchy)' }} />
                  </svg>
                  <span className="relative z-10 w-9 h-9 flex items-center justify-center text-sm font-bold font-caveat" style={{ color: markerColor.accent }}>
                    {slide.slide_number}
                  </span>
                </div>
              </div>
              <h2
                className="text-2xl md:text-3xl font-bold mb-8 text-center tracking-tight sketch-title font-caveat"
                style={{ color: markerColor.primary }}
              >
                {slide.title}
              </h2>
              <div className="grid grid-cols-2 gap-4 flex-1">
                {safeBullets.map((point, i) => (
                  <div
                    key={i}
                    className="relative p-5 flex items-start gap-3 sketch-bullet sketch-card"
                    style={{
                      animationDelay: `${200 + i * 150}ms`,
                      borderRadius: getSketchBorderRadius(i),
                      border: `2px solid ${markerColor.accent}22`,
                      background: `${markerColor.accent}06`,
                    }}
                  >
                    <span
                      className="w-7 h-7 flex items-center justify-center text-sm font-bold shrink-0 font-caveat"
                      style={{
                        color: markerColor.accent,
                        border: `2px solid ${markerColor.accent}44`,
                        borderRadius: getSketchBorderRadius(i + 2),
                      }}
                    >
                      {i + 1}
                    </span>
                    <span className="leading-relaxed font-patrick" style={{ color: '#2d3748' }}>{renderBulletText(point, markerColor.accent)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ─── Summary Layout ─── */}
          {slide.layout === 'summary' && (
            <div className="flex flex-col items-center justify-center w-full px-12 py-12 text-center">
              {/* Decorative sketch underline */}
              <svg className="w-24 h-3 mb-8 sketch-draw-line" viewBox="0 0 100 10" fill="none">
                <path
                  d="M2 6 C25 2, 50 9, 75 5 C85 3, 92 7, 98 4"
                  stroke={markerColor.accent}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  className="sketch-path"
                />
              </svg>
              <h2
                className="text-3xl md:text-4xl font-bold mb-10 tracking-tight sketch-title font-caveat"
                style={{ color: markerColor.primary }}
              >
                {slide.title}
              </h2>
              <div className="space-y-3 max-w-2xl w-full">
                {safeBullets.map((point, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-4 px-6 py-4 sketch-bullet sketch-card"
                    style={{
                      animationDelay: `${200 + i * 150}ms`,
                      borderRadius: getSketchBorderRadius(i),
                      border: `2px solid ${markerColor.accent}22`,
                      background: `${markerColor.accent}06`,
                    }}
                  >
                    {/* Hand-drawn checkmark */}
                    <span className="shrink-0">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path
                          d="M4 12 L10 18 L20 6"
                          stroke={markerColor.accent}
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="sketch-check"
                          style={{ filter: 'url(#sketchy)' }}
                        />
                      </svg>
                    </span>
                    <span className="text-left leading-relaxed font-patrick" style={{ color: '#2d3748' }}>{renderBulletText(point, markerColor.accent)}</span>
                  </div>
                ))}
              </div>
              {/* Bottom squiggle */}
              <svg className="w-40 h-4 mt-10 sketch-draw-line" viewBox="0 0 160 16" fill="none" style={{ animationDelay: '0.8s' }}>
                <path
                  d="M4 8 C20 2, 30 14, 50 8 C70 2, 80 14, 100 8 C120 2, 130 14, 156 8"
                  stroke={markerColor.accent}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeOpacity="0.35"
                  className="sketch-path-long"
                />
              </svg>
            </div>
          )}
        </div>

        {/* Navigation arrows — sketch style */}
        {currentSlide > 0 && (
          <button
            onClick={prevSlide}
            onMouseEnter={() => setHoveredNav('left')}
            onMouseLeave={() => setHoveredNav(null)}
            className="absolute left-4 top-1/2 -translate-y-1/2 w-11 h-11 flex items-center justify-center transition-all duration-300 z-20 hover:scale-110 active:scale-95 sketch-nav-btn"
            style={{
              borderRadius: getSketchBorderRadius(0),
              border: `2px solid ${markerColor.accent}44`,
              background: hoveredNav === 'left' ? `${markerColor.accent}15` : 'rgba(255,255,255,0.8)',
              color: markerColor.primary,
            }}
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        )}
        {currentSlide < slides.length - 1 && (
          <button
            onClick={nextSlide}
            onMouseEnter={() => setHoveredNav('right')}
            onMouseLeave={() => setHoveredNav(null)}
            className="absolute right-4 top-1/2 -translate-y-1/2 w-11 h-11 flex items-center justify-center transition-all duration-300 z-20 hover:scale-110 active:scale-95 sketch-nav-btn"
            style={{
              borderRadius: getSketchBorderRadius(1),
              border: `2px solid ${markerColor.accent}44`,
              background: hoveredNav === 'right' ? `${markerColor.accent}15` : 'rgba(255,255,255,0.8)',
              color: markerColor.primary,
            }}
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        )}

        {/* Slide number badge — handwritten */}
        <div
          className="absolute top-4 right-4 text-[13px] font-bold px-3 py-1.5 z-20 tabular-nums font-caveat"
          style={{
            color: markerColor.primary,
            background: 'rgba(255,255,255,0.7)',
            borderRadius: getSketchBorderRadius(2),
            border: `1.5px solid ${markerColor.accent}33`,
          }}
        >
          {currentSlide + 1} / {slides.length}
        </div>
      </div>

      {/* ── Bottom Controls Bar — Whiteboard shelf ── */}
      <div className="bg-[#e8e0d4] border-t-2 border-[#c4b89a]" style={{ boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.06)' }}>
        {/* Progress bar — pen stroke style */}
        <div className="h-[4px] bg-[#d4cbb8] relative overflow-hidden">
          <div
            className="h-full transition-all duration-500 ease-out"
            style={{
              width: `${progress}%`,
              background: `linear-gradient(90deg, ${markerColor.accent}88, ${markerColor.accent})`,
              borderRadius: '0 4px 4px 0',
            }}
          />
        </div>

        <div className="px-4 py-3">
          {/* Slide Dots — marker dots */}
          <div className="flex items-center justify-center gap-2 mb-3">
            {slides.map((s, i) => (
              <button
                key={i}
                onClick={() => goToSlide(i)}
                className="group relative transition-all duration-300"
                title={`Slide ${i + 1}: ${s.title}`}
              >
                <div
                  className={`transition-all duration-300 ${
                    i === currentSlide
                      ? 'w-6 h-3 rounded-full'
                      : 'w-2.5 h-2.5 rounded-full'
                  }`}
                  style={{
                    background: i === currentSlide
                      ? markerColor.accent
                      : i < currentSlide
                      ? `${markerColor.accent}66`
                      : '#bbb',
                    borderRadius: i === currentSlide ? getSketchBorderRadius(i) : '50%',
                    opacity: i === currentSlide ? 1 : i < currentSlide ? 0.8 : 0.4,
                  }}
                />
                <span className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-[#2d3748] text-white text-[10px] px-2 py-1 rounded-md whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-30 font-patrick">
                  {s.title}
                </span>
              </button>
            ))}
          </div>

          {/* Control buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={onPlayToggle}
                className="flex items-center gap-2 px-4 py-2 text-white text-xs font-bold transition-all duration-300 hover:brightness-110 active:scale-95 font-patrick"
                style={{
                  background: markerColor.accent,
                  borderRadius: getSketchBorderRadius(3),
                  boxShadow: `0 2px 8px ${markerColor.accent}33`,
                }}
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                {isPlaying ? 'Pause' : 'Play'}
              </button>
              <button
                onClick={() => goToSlide(0)}
                className="p-2 rounded-lg transition-all duration-200 hover:bg-[#d4cbb8]"
                style={{ color: markerColor.primary }}
                title="Restart"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="flex items-center gap-3 text-[11px] font-medium tabular-nums font-patrick" style={{ color: '#8b7e6a' }}>
              <span className="flex items-center gap-1.5">
                <Clock className="w-3 h-3" />
                Slide {currentSlide + 1} of {slides.length}
              </span>
            </div>

            <button
              onClick={toggleFullscreen}
              className="p-2 rounded-lg transition-all duration-200 hover:bg-[#d4cbb8]"
              style={{ color: markerColor.primary }}
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
