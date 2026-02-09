'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, Mic, MicOff, Paperclip, X, FileText } from 'lucide-react'
import MessageList from './MessageList'
import { Message, FileAttachment } from '@/lib/types'
import { streamResearch, uploadImage, uploadFile } from '@/lib/api'

interface ChatInterfaceProps {
  messages: Message[]
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  onMessagesChange?: () => void
}

export default function ChatInterface({ messages, setMessages, onMessagesChange }: ChatInterfaceProps) {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [attachments, setAttachments] = useState<FileAttachment[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const recognitionRef = useRef<any>(null)

  // Check for speech recognition support
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (SpeechRecognition) {
      setSpeechSupported(true)
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'

      recognition.onresult = (event: any) => {
        let finalTranscript = ''
        let interimTranscript = ''

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscript += transcript
          } else {
            interimTranscript += transcript
          }
        }

        if (finalTranscript) {
          setInput(prev => prev + finalTranscript)
        }
      }

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error)
        setIsRecording(false)
      }

      recognition.onend = () => {
        setIsRecording(false)
      }

      recognitionRef.current = recognition
    }
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Toggle voice recording
  const toggleRecording = useCallback(() => {
    if (!recognitionRef.current) return

    if (isRecording) {
      recognitionRef.current.stop()
      setIsRecording(false)
    } else {
      recognitionRef.current.start()
      setIsRecording(true)
    }
  }, [isRecording])

  // Handle file selection
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setIsUploading(true)

    for (const file of Array.from(files)) {
      try {
        const isImage = file.type.startsWith('image/')
        
        if (isImage) {
          // Upload image and get VLM analysis
          const result = await uploadImage(file, input)
          const attachment: FileAttachment = {
            name: file.name,
            type: 'image',
            previewUrl: result.preview_url,
            analysis: result.analysis,
            contentType: file.type
          }
          setAttachments(prev => [...prev, attachment])
        } else {
          // Upload document and extract text
          const result = await uploadFile(file)
          const attachment: FileAttachment = {
            name: file.name,
            type: 'document',
            analysis: result.extracted_text,
            contentType: file.type
          }
          setAttachments(prev => [...prev, attachment])
        }
      } catch (error) {
        console.error('File upload error:', error)
      }
    }

    setIsUploading(false)
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // Remove attachment
  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if ((!input.trim() && attachments.length === 0) || isLoading) return

    // Stop recording if active
    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop()
      setIsRecording(false)
    }

    // Build context from attachments
    let imageContext = ''
    let fileContext = ''
    const messageAttachments = [...attachments]

    for (const att of attachments) {
      if (att.type === 'image' && att.analysis) {
        imageContext += att.analysis + '\n'
      } else if (att.type === 'document' && att.analysis) {
        fileContext += `[${att.name}]:\n${att.analysis}\n\n`
      }
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim() || 'Analyze the attached content',
      timestamp: new Date(),
      attachments: messageAttachments.length > 0 ? messageAttachments : undefined
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setAttachments([])
    setIsLoading(true)

    // Create placeholder for assistant response
    const assistantId = (Date.now() + 1).toString()
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true
    }

    setMessages(prev => [...prev, assistantMessage])

    try {
      await streamResearch(
        userMessage.content,
        (chunk) => {
          setMessages(prev => {
            const newMessages = [...prev]
            const lastMessage = newMessages[newMessages.length - 1]
            
            if (lastMessage.id === assistantId) {
              if (chunk.type === 'status') {
                lastMessage.status = chunk.data
              } else if (chunk.type === 'topic') {
                lastMessage.topic = chunk.data
              } else if (chunk.type === 'intent') {
                lastMessage.intent = chunk.intent
              } else if (chunk.type === 'tldr') {
                lastMessage.tldr = chunk.data
                lastMessage.isLoading = false
              } else if (chunk.type === 'explanation') {
                lastMessage.explanation = chunk.data
              } else if (chunk.type === 'image') {
                if (!lastMessage.images) lastMessage.images = []
                const imgUrl = chunk.data.url
                if (!lastMessage.images.some((img: any) => img.url === imgUrl)) {
                  lastMessage.images.push(chunk.data)
                }
              } else if (chunk.type === 'source') {
                if (!lastMessage.sources) lastMessage.sources = []
                lastMessage.sources.push(chunk.data)
              } else if (chunk.type === 'analogy') {
                lastMessage.analogy = chunk.data
              } else if (chunk.type === 'practice_question') {
                if (!lastMessage.practiceQuestions) lastMessage.practiceQuestions = []
                const normalized = chunk.data.toLowerCase().replace(/[?.!,]/g, '').trim()
                const isDuplicate = lastMessage.practiceQuestions.some(
                  (q: string) => q.toLowerCase().replace(/[?.!,]/g, '').trim() === normalized
                )
                if (!isDuplicate) {
                  lastMessage.practiceQuestions.push(chunk.data)
                }
              } else if (chunk.type === 'complete') {
                lastMessage.isLoading = false
                lastMessage.complete = true
                const fullData = chunk.data
                lastMessage.content = fullData.tldr || lastMessage.tldr || ''
                lastMessage.followUpSuggestions = fullData.follow_up_suggestions || []
                // Save to history on completion
                setTimeout(() => onMessagesChange?.(), 0)
              }
            }
            
            return newMessages
          })
        },
        imageContext || undefined,
        fileContext || undefined
      )
    } catch (error) {
      console.error('Research error:', error)
      setMessages(prev => {
        const newMessages = [...prev]
        const lastMessage = newMessages[newMessages.length - 1]
        if (lastMessage.id === assistantId) {
          lastMessage.isLoading = false
          lastMessage.error = 'Sorry, I encountered an error processing your question. Please try again.'
        }
        return newMessages
      })
      onMessagesChange?.()
    } finally {
      setIsLoading(false)
    }
  }

  const suggestions = [
    { text: "Explain quantum entanglement?", icon: "🔬" },
    { text: "How do neural networks learn?", icon: "🧠" },
    { text: "What is the theory of relativity?", icon: "⚡" },
    { text: "Explain photosynthesis step by step?", icon: "🌿" },
  ]

  return (
    <div className="flex flex-col h-full max-w-5xl mx-auto px-4 sm:px-6">
      {messages.length === 0 ? (
        <div className="flex-1 flex items-center justify-center relative">
          {/* Ambient background orbs */}
          <div className="orb orb-primary w-[300px] h-[300px] top-[10%] left-[15%] animate-float" />
          <div className="orb orb-secondary w-[200px] h-[200px] bottom-[20%] right-[10%] animate-float" style={{ animationDelay: '1.5s' }} />

          <div className="text-center space-y-10 max-w-3xl w-full relative z-10 animate-fadeIn">
            {/* Hero section */}
            <div className="space-y-4">
              <div className="flex items-center justify-center mb-2">
                <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight animate-lumina-glow">
                  <span className="bg-gradient-to-r from-[hsl(73,31%,55%)] via-[hsl(73,45%,65%)] to-[hsl(73,31%,45%)] bg-[length:200%_auto] animate-gradient bg-clip-text text-transparent drop-shadow-[0_0_25px_hsl(73,31%,45%,0.35)]">Lumina</span>
                </h1>
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
                What do you want to <span className="text-gradient">explore</span>?
              </h2>
              <p className="text-muted-foreground text-base max-w-md mx-auto">
                Ask anything — I'll research, explain, and find visuals to help you understand.
              </p>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto stagger-children">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => setInput(suggestion.text)}
                  className="group relative p-4 text-left bg-card/50 border border-border/40 rounded-2xl hover:bg-card hover:border-[hsl(73,31%,45%)]/30 hover:shadow-lg hover:shadow-[hsl(73,31%,45%)]/5 transition-all duration-300"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg">{suggestion.icon}</span>
                    <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors leading-relaxed">
                      {suggestion.text}
                    </span>
                  </div>
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-[hsl(73,31%,45%)]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto pb-4">
          <MessageList messages={messages} />
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Attachment previews */}
      {attachments.length > 0 && (
        <div className="flex gap-2 flex-wrap px-2 pt-2">
          {attachments.map((att, idx) => (
            <div
              key={idx}
              className="relative group flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-xl text-sm animate-fadeIn"
            >
              {att.type === 'image' ? (
                <>
                  {att.previewUrl && (
                    <img src={att.previewUrl} alt={att.name} className="w-10 h-10 rounded-lg object-cover" />
                  )}
                  <div className="flex flex-col">
                    <span className="text-xs font-medium text-foreground truncate max-w-[120px]">{att.name}</span>
                    <span className="text-[10px] text-green-600 dark:text-green-400">Image analyzed</span>
                  </div>
                </>
              ) : (
                <>
                  <FileText className="w-5 h-5 text-[hsl(73,31%,45%)]" />
                  <div className="flex flex-col">
                    <span className="text-xs font-medium text-foreground truncate max-w-[120px]">{att.name}</span>
                    <span className="text-[10px] text-green-600 dark:text-green-400">Content extracted</span>
                  </div>
                </>
              )}
              <button
                onClick={() => removeAttachment(idx)}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
          {isUploading && (
            <div className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-xl text-sm">
              <Loader2 className="w-4 h-4 animate-spin text-[hsl(73,31%,45%)]" />
              <span className="text-xs text-muted-foreground">Analyzing...</span>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="pt-4 pb-4">
        <div className="relative bg-card/40 border border-border/40 rounded-2xl transition-all duration-300 focus-within:border-[hsl(73,31%,45%)]/40 focus-within:bg-card/80 focus-within:shadow-lg focus-within:shadow-[hsl(73,31%,45%)]/5">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
            placeholder={isRecording ? 'Listening...' : 'Ask anything...'}
            disabled={isLoading}
            rows={1}
            className={`w-full px-5 py-4 pr-36 bg-transparent border-none focus:outline-none focus:ring-0 resize-none text-foreground placeholder:text-muted-foreground/50 text-[15px] ${isRecording ? 'placeholder:text-red-400 placeholder:animate-pulse' : ''}`}
            style={{ minHeight: '54px', maxHeight: '200px' }}
          />
          
          {/* Input action buttons */}
          <div className="absolute right-2.5 bottom-2.5 flex items-center gap-1">
            {/* File attachment */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,.pdf,.docx,.txt,.md,.csv"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading || isUploading}
              className="h-9 w-9 rounded-xl hover:bg-[hsl(73,31%,45%)]/10 text-muted-foreground/60 hover:text-[hsl(73,31%,45%)] disabled:opacity-50 transition-all duration-200 flex items-center justify-center"
              title="Attach files (images, PDF, DOCX, TXT)"
            >
              <Paperclip className="w-[18px] h-[18px]" />
            </button>

            {/* Voice input */}
            {speechSupported && (
              <button
                type="button"
                onClick={toggleRecording}
                disabled={isLoading}
                className={`h-9 w-9 rounded-xl transition-all duration-200 flex items-center justify-center ${
                  isRecording
                    ? 'bg-red-500 hover:bg-red-600 text-white shadow-md shadow-red-500/25 animate-pulse'
                    : 'hover:bg-[hsl(73,31%,45%)]/10 text-muted-foreground/60 hover:text-[hsl(73,31%,45%)]'
                } disabled:opacity-50`}
                title={isRecording ? 'Stop recording' : 'Voice input'}
              >
                {isRecording ? <MicOff className="w-[18px] h-[18px]" /> : <Mic className="w-[18px] h-[18px]" />}
              </button>
            )}

            {/* Send button */}
            <button
              type="submit"
              disabled={(!input.trim() && attachments.length === 0) || isLoading}
              className="h-9 w-9 rounded-xl bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] hover:from-[hsl(73,31%,40%)] hover:to-[hsl(73,31%,45%)] text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center shadow-md shadow-[hsl(73,31%,45%)]/20 disabled:shadow-none"
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
  )
}
