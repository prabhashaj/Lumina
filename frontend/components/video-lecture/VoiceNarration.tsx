'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Volume2, VolumeX, ChevronDown, ChevronUp } from 'lucide-react'

interface VoiceNarrationProps {
  narrationText: string
  audioBase64?: string
  useBrowserTTS: boolean
  isActive: boolean
  onNarrationEnd: () => void
  autoPlay: boolean
}

export default function VoiceNarration({
  narrationText,
  audioBase64,
  useBrowserTTS,
  isActive,
  onNarrationEnd,
  autoPlay,
}: VoiceNarrationProps) {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [showTranscript, setShowTranscript] = useState(true)
  const [highlightWord, setHighlightWord] = useState(-1)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  const wordsRef = useRef<string[]>([])

  // Split narration into words for highlighting
  useEffect(() => {
    wordsRef.current = narrationText.split(/\s+/).filter(Boolean)
    setHighlightWord(-1)
  }, [narrationText])

  // Stop any current playback when slide changes
  useEffect(() => {
    return () => {
      stopAll()
    }
  }, [narrationText])

  const stopAll = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    setIsSpeaking(false)
    setHighlightWord(-1)
  }, [])

  const playAudio = useCallback(() => {
    if (isMuted) return

    stopAll()

    if (!useBrowserTTS && audioBase64) {
      // Use ElevenLabs audio
      const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`)
      audioRef.current = audio

      // Estimate word timing from audio duration
      audio.onloadedmetadata = () => {
        const duration = audio.duration
        const words = wordsRef.current
        if (words.length === 0) return
        const interval = (duration * 1000) / words.length
        let idx = 0
        const timer = setInterval(() => {
          if (idx < words.length) {
            setHighlightWord(idx)
            idx++
          } else {
            clearInterval(timer)
          }
        }, interval)

        audio.onended = () => {
          clearInterval(timer)
          setIsSpeaking(false)
          setHighlightWord(-1)
          onNarrationEnd()
        }
      }

      audio.play()
      setIsSpeaking(true)
    } else {
      // Browser TTS fallback
      if (!window.speechSynthesis) return

      const utterance = new SpeechSynthesisUtterance(narrationText)
      utteranceRef.current = utterance

      // Pick a soft, natural-sounding female English voice
      const voices = window.speechSynthesis.getVoices()
      const softFemaleNames = ['Samantha', 'Zira', 'Jenny', 'Aria', 'Sara', 'Google UK English Female', 'Google US English']
      const preferred = voices.find(
        (v) => v.lang.startsWith('en') && softFemaleNames.some((name) => v.name.includes(name))
      ) || voices.find(
        (v) => v.lang.startsWith('en') && v.name.toLowerCase().includes('female')
      ) || voices.find(
        (v) => v.lang.startsWith('en')
      )
      if (preferred) utterance.voice = preferred

      utterance.rate = 0.82
      utterance.pitch = 1.02

      // Word boundary events for highlighting
      let wordIdx = 0
      utterance.onboundary = (e) => {
        if (e.name === 'word') {
          setHighlightWord(wordIdx)
          wordIdx++
        }
      }

      utterance.onend = () => {
        setIsSpeaking(false)
        setHighlightWord(-1)
        onNarrationEnd()
      }

      utterance.onerror = () => {
        setIsSpeaking(false)
        setHighlightWord(-1)
      }

      window.speechSynthesis.speak(utterance)
      setIsSpeaking(true)
    }
  }, [audioBase64, isMuted, narrationText, onNarrationEnd, stopAll, useBrowserTTS])

  // Auto-play when slide becomes active OR when narration text changes (slide advance)
  useEffect(() => {
    if (isActive && autoPlay && !isMuted && narrationText) {
      // Small delay for slide transition to complete
      const t = setTimeout(() => playAudio(), 450)
      return () => clearTimeout(t)
    }
  }, [isActive, autoPlay, narrationText])

  const toggleMute = () => {
    if (!isMuted) {
      stopAll()
    }
    setIsMuted((prev) => !prev)
  }

  const words = wordsRef.current

  return (
    <div className="bg-slate-900/60 backdrop-blur rounded-xl border border-white/5 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/5">
        <div className="flex items-center gap-2">
          <button
            onClick={toggleMute}
            className={`p-1.5 rounded-lg transition-all ${
              isMuted
                ? 'text-red-400 hover:bg-red-400/10'
                : 'text-[hsl(73,31%,55%)] hover:bg-[hsl(73,31%,55%)]/10'
            }`}
          >
            {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>
          <span className="text-xs text-white/50 font-medium">
            {isSpeaking ? 'Speaking...' : 'Narration'}
          </span>
          {isSpeaking && (
            <div className="flex items-center gap-0.5">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="w-0.5 bg-[hsl(73,31%,55%)] rounded-full animate-pulse"
                  style={{
                    height: `${8 + Math.random() * 8}px`,
                    animationDelay: `${i * 150}ms`,
                    animationDuration: '0.6s',
                  }}
                />
              ))}
            </div>
          )}
        </div>
        <button
          onClick={() => setShowTranscript((prev) => !prev)}
          className="flex items-center gap-1 text-xs text-white/40 hover:text-white/60 transition-all"
        >
          Transcript
          {showTranscript ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>

      {/* Transcript with word highlighting */}
      {showTranscript && (
        <div className="px-4 py-3 max-h-32 overflow-y-auto text-sm leading-relaxed">
          {words.map((word, i) => (
            <span
              key={i}
              className={`transition-colors duration-200 ${
                i === highlightWord
                  ? 'text-[hsl(73,31%,55%)] font-semibold'
                  : i < highlightWord
                  ? 'text-white/60'
                  : 'text-white/40'
              }`}
            >
              {word}{' '}
            </span>
          ))}
        </div>
      )}

      {/* Play button if not auto-playing */}
      {!isSpeaking && !isMuted && isActive && (
        <div className="px-4 pb-3">
          <button
            onClick={playAudio}
            className="w-full py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/60 hover:text-white/80 text-xs font-medium transition-all flex items-center justify-center gap-1.5"
          >
            <Volume2 className="w-3 h-3" />
            Play Narration
          </button>
        </div>
      )}
    </div>
  )
}
