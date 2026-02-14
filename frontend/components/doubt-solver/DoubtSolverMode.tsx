'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import {
  Camera,
  Upload,
  X,
  Loader2,
  Sparkles,
  Send,
  ImageIcon,
  RotateCcw,
  Lightbulb,
  Paperclip,
  Bot,
  User as UserIcon,
  Trash2,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { doubtSolverChat } from '@/lib/api'
import { DoubtMessage } from '@/lib/types'

export default function DoubtSolverMode() {
  const [messages, setMessages] = useState<DoubtMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [pendingImage, setPendingImage] = useState<File | null>(null)
  const [pendingImagePreview, setPendingImagePreview] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('Please upload an image file (JPG, PNG, WebP)')
      return
    }
    setError(null)
    setPendingImage(file)
    const reader = new FileReader()
    reader.onload = (e) => setPendingImagePreview(e.target?.result as string)
    reader.readAsDataURL(file)
  }, [])

  const removePendingImage = () => {
    setPendingImage(null)
    setPendingImagePreview(null)
  }

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => {
        const result = reader.result as string
        const base64 = result.split(',')[1]
        resolve(base64)
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if ((!input.trim() && !pendingImage) || isLoading) return

    const userMessage: DoubtMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim() || (pendingImage ? 'Please analyze this image and solve any problems shown.' : ''),
      timestamp: new Date(),
      imagePreview: pendingImagePreview || undefined,
    }

    setMessages(prev => [...prev, userMessage])

    let imageBase64: string | undefined
    let imageType: string | undefined
    const currentImage = pendingImage

    setInput('')
    setPendingImage(null)
    setPendingImagePreview(null)
    setIsLoading(true)
    setError(null)

    const assistantId = (Date.now() + 1).toString()
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    }])

    try {
      if (currentImage) {
        imageBase64 = await fileToBase64(currentImage)
        imageType = currentImage.type
      }

      const history = messages.map(m => ({
        role: m.role,
        content: m.imageContext
          ? `[Image context: ${m.imageContext}]\n${m.content}`
          : m.content,
      }))

      const result = await doubtSolverChat(
        userMessage.content,
        history,
        imageBase64,
        imageType
      )

      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: result.response, isLoading: false, imageContext: result.image_context || undefined }
          : m
      ))

      if (result.image_context) {
        setMessages(prev => prev.map(m =>
          m.id === userMessage.id
            ? { ...m, imageContext: result.image_context || undefined }
            : m
        ))
      }
    } catch (err: any) {
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: 'Sorry, I encountered an error. Please try again.', isLoading: false }
          : m
      ))
      setError(err.message || 'Failed to get response')
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setMessages([])
    setInput('')
    setPendingImage(null)
    setPendingImagePreview(null)
    setError(null)
  }

  const suggestions = [
    { text: "Solve this calculus problem step by step", icon: "📐" },
    { text: "Explain this physics concept with examples", icon: "⚛️" },
    { text: "Help me understand this chemistry equation", icon: "🧪" },
    { text: "Break down this programming algorithm", icon: "💻" },
  ]

  const renderMarkdown = (text: string) => (
    <div className="prose prose-invert prose-sm max-w-none
        prose-headings:text-foreground prose-headings:font-bold prose-headings:mt-4 prose-headings:mb-2
        prose-p:text-muted-foreground prose-p:leading-relaxed prose-p:my-1.5
        prose-strong:text-foreground
        prose-code:text-[hsl(73,31%,55%)] prose-code:bg-muted/50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
        prose-pre:bg-muted/30 prose-pre:border prose-pre:border-border/20 prose-pre:rounded-xl
        prose-li:text-muted-foreground prose-li:my-0.5
        prose-ul:space-y-0.5 prose-ol:space-y-0.5">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {text}
      </ReactMarkdown>
    </div>
  )

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center min-h-full px-4">
            <div className="text-center space-y-8 max-w-2xl w-full animate-fadeIn relative">
              <div className="orb orb-primary w-[250px] h-[250px] top-[15%] left-[10%] animate-float opacity-30" />
              <div className="orb orb-secondary w-[180px] h-[180px] bottom-[25%] right-[15%] animate-float opacity-30" style={{ animationDelay: '1.5s' }} />

              <div className="space-y-4 relative z-10">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-cyan-500/20 bg-cyan-500/5">
                  <Camera className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-xs font-medium text-cyan-400">AI Doubt Solver</span>
                </div>
                <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
                  Ask questions, upload <span className="text-gradient">images</span>
                </h1>
                <p className="text-muted-foreground max-w-lg mx-auto">
                  Chat with AI to solve doubts. Upload photos of textbooks, notes, or problems — or just type your question.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl mx-auto relative z-10">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(s.text)}
                    className="group relative p-4 text-left bg-card/50 border border-border/40 rounded-2xl hover:bg-card hover:border-cyan-500/30 hover:shadow-lg hover:shadow-cyan-500/5 transition-all duration-300"
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-lg">{s.icon}</span>
                      <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors leading-relaxed">
                        {s.text}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 animate-fadeIn ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-600 flex items-center justify-center flex-shrink-0 mt-1 shadow-lg shadow-cyan-500/20">
                    <Lightbulb className="w-4 h-4 text-white" />
                  </div>
                )}

                <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                  {msg.role === 'user' && (
                    <div className="space-y-2">
                      {msg.imagePreview && (
                        <div className="flex justify-end">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={msg.imagePreview}
                            alt="Uploaded"
                            className="max-h-48 rounded-xl border border-border/30 shadow-md"
                          />
                        </div>
                      )}
                      <div className="bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white px-4 py-3 rounded-2xl rounded-tr-md shadow-md">
                        <p className="text-sm leading-relaxed">{msg.content}</p>
                      </div>
                    </div>
                  )}

                  {msg.role === 'assistant' && (
                    <div className="bg-card/50 border border-border/20 px-5 py-4 rounded-2xl rounded-tl-md shadow-sm">
                      {msg.isLoading ? (
                        <div className="flex items-center gap-3 py-2">
                          <div className="flex gap-1">
                            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                          <span className="text-sm text-muted-foreground">Thinking...</span>
                        </div>
                      ) : (
                        renderMarkdown(msg.content)
                      )}
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
                    <UserIcon className="w-4 h-4 text-white" />
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 sm:px-6 max-w-4xl mx-auto w-full">
          <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-2 hover:text-foreground">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Pending image preview */}
      {pendingImagePreview && (
        <div className="px-4 sm:px-6 max-w-4xl mx-auto w-full pt-2">
          <div className="inline-flex items-center gap-2 p-2 bg-card/60 border border-border/30 rounded-xl animate-fadeIn">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={pendingImagePreview}
              alt="To upload"
              className="h-16 w-16 object-cover rounded-lg border border-border/20"
            />
            <div className="flex flex-col">
              <span className="text-xs font-medium text-foreground truncate max-w-[120px]">
                {pendingImage?.name}
              </span>
              <span className="text-[10px] text-cyan-400">Ready to analyze</span>
            </div>
            <button
              onClick={removePendingImage}
              className="ml-1 w-6 h-6 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 flex items-center justify-center transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="px-4 sm:px-6 max-w-4xl mx-auto w-full pt-3 pb-4">
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={handleReset}
              className="p-2.5 rounded-xl hover:bg-muted/60 text-muted-foreground hover:text-foreground transition-all disabled:opacity-50"
              title="Clear conversation"
              disabled={isLoading}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          <form onSubmit={handleSubmit} className="flex-1 relative">
            <div className="relative bg-card/40 border border-border/40 rounded-2xl transition-all duration-300 focus-within:border-cyan-500/40 focus-within:bg-card/80 focus-within:shadow-lg focus-within:shadow-cyan-500/5">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit()
                  }
                }}
                placeholder={
                  messages.length === 0
                    ? 'Type your doubt or upload an image...'
                    : 'Ask a follow-up question...'
                }
                disabled={isLoading}
                rows={1}
                className="w-full px-5 py-4 pr-24 bg-transparent border-none focus:outline-none focus:ring-0 resize-none text-foreground placeholder:text-muted-foreground/50 text-[15px]"
                style={{ minHeight: '54px', maxHeight: '150px' }}
              />

              <div className="absolute right-2.5 bottom-2.5 flex items-center gap-1">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleFile(file)
                    if (fileInputRef.current) fileInputRef.current.value = ''
                  }}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading}
                  className="h-9 w-9 rounded-xl hover:bg-cyan-500/10 text-muted-foreground/60 hover:text-cyan-400 disabled:opacity-50 transition-all duration-200 flex items-center justify-center"
                  title="Upload image"
                >
                  <ImageIcon className="w-[18px] h-[18px]" />
                </button>

                <button
                  type="submit"
                  disabled={(!input.trim() && !pendingImage) || isLoading}
                  className="h-9 w-9 rounded-xl bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center shadow-md shadow-cyan-500/20 disabled:shadow-none"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
