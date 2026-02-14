'use client'

import { useState, useRef, useEffect } from 'react'
import {
  X,
  Send,
  Loader2,
  Sparkles,
  Minimize2,
  Maximize2,
  Trash2,
  Bot,
  User as UserIcon,
  HelpCircle,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { guideChat } from '@/lib/api'
import { GuideMessage } from '@/lib/types'

interface GuideChatbotProps {
  mode: 'exam-prep' | 'personalized' | 'video-lecture'
  context: string
  title?: string
}

const modeConfig: Record<string, { label: string; greeting: string }> = {
  'exam-prep': {
    label: 'Study Guide',
    greeting:
      "Hi! I'm your study guide. Ask me anything about your exam topics — I can explain concepts, create practice questions, or help you study more effectively.",
  },
  personalized: {
    label: 'Learning Guide',
    greeting:
      "Hello! I'm your learning guide. I can help you dive deeper into any topic, provide extra examples, or help you overcome any learning challenges.",
  },
  'video-lecture': {
    label: 'Lecture Assistant',
    greeting:
      "Hey there! I'm your lecture assistant. Feel free to ask about anything from the slides — I can clarify concepts, give more examples, or answer any questions.",
  },
}

export default function GuideChatbot({ mode, context, title }: GuideChatbotProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [messages, setMessages] = useState<GuideMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const config = modeConfig[mode] || modeConfig['exam-prep']

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  // Add greeting when first opened
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([
        {
          id: 'greeting',
          role: 'assistant',
          content: config.greeting,
          timestamp: new Date(),
        },
      ])
    }
  }, [isOpen, messages.length, config.greeting])

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: GuideMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    const assistantId = (Date.now() + 1).toString()
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isLoading: true,
      },
    ])

    try {
      const history = messages
        .filter((m) => m.id !== 'greeting' || m.role === 'assistant')
        .map((m) => ({ role: m.role, content: m.content }))

      const result = await guideChat(userMessage.content, mode, context, history)

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: result.response, isLoading: false } : m
        )
      )
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: 'Sorry, I encountered an error. Please try again.', isLoading: false }
            : m
        )
      )
    } finally {
      setIsLoading(false)
    }
  }

  const handleClear = () => {
    setMessages([
      {
        id: 'greeting-' + Date.now(),
        role: 'assistant',
        content: config.greeting,
        timestamp: new Date(),
      },
    ])
  }

  const renderMarkdown = (text: string) => (
    <div
      className="prose prose-invert prose-sm max-w-none
        prose-headings:text-foreground prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1.5
        prose-p:text-muted-foreground prose-p:leading-relaxed prose-p:my-1 prose-p:text-[13px]
        prose-strong:text-foreground
        prose-code:text-[hsl(73,31%,60%)] prose-code:bg-muted/50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
        prose-pre:bg-muted/30 prose-pre:border prose-pre:border-border/20 prose-pre:rounded-lg prose-pre:text-xs
        prose-li:text-muted-foreground prose-li:my-0.5 prose-li:text-[13px]
        prose-ul:space-y-0.5 prose-ol:space-y-0.5"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  )

  // ── Floating trigger button ──
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 group"
        title={`Open ${title || config.label}`}
      >
        <div className="relative">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,35%)] text-white flex items-center justify-center shadow-xl shadow-[hsl(73,31%,45%)]/25 group-hover:shadow-2xl group-hover:shadow-[hsl(73,31%,45%)]/40 group-hover:scale-105 transition-all duration-300">
            <HelpCircle className="w-6 h-6 group-hover:scale-110 transition-transform" />
          </div>
          <div className="absolute -inset-1 rounded-[20px] bg-[hsl(73,31%,45%)]/10 animate-pulse-glow pointer-events-none" />
        </div>
      </button>
    )
  }

  // ── Chat panel ──
  return (
    <div
      className={`fixed z-50 transition-all duration-300 ease-out flex flex-col overflow-hidden
        border border-border/30 shadow-2xl shadow-black/20 bg-background
        ${
          isExpanded
            ? 'bottom-0 right-0 w-full h-full sm:bottom-5 sm:right-5 sm:w-[520px] sm:h-[680px] sm:rounded-2xl'
            : 'bottom-5 right-5 w-[400px] h-[540px] rounded-2xl'
        }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/20 bg-gradient-to-r from-[hsl(73,31%,42%)] to-[hsl(73,35%,38%)] shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/15 flex items-center justify-center backdrop-blur-sm">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              {title || config.label}
            </h3>
            <p className="text-[10px] text-white/60 font-medium">AI-powered assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-0.5">
          {messages.length > 1 && (
            <button
              onClick={handleClear}
              className="w-8 h-8 rounded-lg hover:bg-white/10 text-white/60 hover:text-white flex items-center justify-center transition-colors"
              title="Clear chat"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-8 h-8 rounded-lg hover:bg-white/10 text-white/60 hover:text-white hidden sm:flex items-center justify-center transition-colors"
            title={isExpanded ? 'Minimize' : 'Expand'}
          >
            {isExpanded ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="w-8 h-8 rounded-lg hover:bg-white/10 text-white/60 hover:text-white flex items-center justify-center transition-colors"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-2.5 animate-fadeIn ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,35%)] flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                <Bot className="w-3.5 h-3.5 text-white" />
              </div>
            )}

            <div className="max-w-[85%]">
              {msg.role === 'user' ? (
                <div className="bg-gradient-to-r from-[hsl(73,31%,42%)] to-[hsl(73,35%,47%)] text-white px-3.5 py-2.5 rounded-2xl rounded-tr-sm shadow-sm">
                  <p className="text-[13px] leading-relaxed">{msg.content}</p>
                </div>
              ) : (
                <div className="bg-card/80 border border-border/30 px-3.5 py-2.5 rounded-2xl rounded-tl-sm">
                  {msg.isLoading ? (
                    <div className="flex items-center gap-2 py-1">
                      <div className="flex gap-1">
                        <span
                          className="w-1.5 h-1.5 rounded-full bg-[hsl(73,31%,50%)] animate-bounce"
                          style={{ animationDelay: '0ms' }}
                        />
                        <span
                          className="w-1.5 h-1.5 rounded-full bg-[hsl(73,31%,50%)] animate-bounce"
                          style={{ animationDelay: '150ms' }}
                        />
                        <span
                          className="w-1.5 h-1.5 rounded-full bg-[hsl(73,31%,50%)] animate-bounce"
                          style={{ animationDelay: '300ms' }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground">Thinking...</span>
                    </div>
                  ) : (
                    renderMarkdown(msg.content)
                  )}
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center flex-shrink-0 mt-0.5">
                <UserIcon className="w-3.5 h-3.5 text-white" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-3 py-3 border-t border-border/20 bg-background shrink-0">
        <form onSubmit={handleSubmit} className="relative">
          <div className="relative bg-card/60 border border-border/40 rounded-xl transition-all duration-300 focus-within:border-[hsl(73,31%,45%)]/40 focus-within:bg-card/80 focus-within:ring-1 focus-within:ring-[hsl(73,31%,45%)]/20">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                // Stop propagation so parent handlers (e.g. SlideViewer space-key) don't interfere
                e.stopPropagation()
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit()
                }
              }}
              placeholder="Ask your guide..."
              disabled={isLoading}
              rows={1}
              className="w-full px-4 py-3 pr-12 bg-transparent border-none focus:outline-none focus:ring-0 resize-none text-foreground placeholder:text-muted-foreground/50 text-[13px]"
              style={{ minHeight: '44px', maxHeight: '100px' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2 bottom-2 h-8 w-8 rounded-lg bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,35%,50%)] text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center shadow-sm disabled:shadow-none hover:brightness-110"
            >
              {isLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
