export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isLoading?: boolean
  error?: string
  status?: string
  topic?: string
  intent?: any
  tldr?: string
  explanation?: any
  images?: ImageData[]
  sources?: Source[]
  analogy?: string
  practiceQuestions?: string[]
  followUpSuggestions?: string[]
  complete?: boolean
  attachments?: FileAttachment[]  // User-attached files
}

export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: string   // ISO string for serialization
  updatedAt: string   // ISO string for serialization
}

export interface FileAttachment {
  name: string
  type: 'image' | 'document'
  previewUrl?: string        // Base64 data URL for images
  analysis?: string          // VLM analysis or extracted text
  contentType: string
}

export interface ImageData {
  url: string
  caption: string
  alt_text?: string
  relevance_score: number
  source_url?: string
}

export interface Source {
  title: string
  url: string
  snippet: string
  domain: string
  relevance_score: number
  source_type?: string
  published_date?: string
}

export interface StreamChunk {
  type: string
  data: any
  intent?: any
  timestamp?: string
}

// ── Exam Prep Types ──────────────────────────────

export type TopicStatus = 'locked' | 'available' | 'generating' | 'completed' | 'quiz-pending' | 'quiz-done'

export interface QuizQuestion {
  id: string
  question: string
  options: string[]
  correctIndex: number
  explanation: string
}

export interface TopicContent {
  tldr?: string
  explanation?: any
  images?: ImageData[]
  sources?: Source[]
  analogy?: string
  practiceQuestions?: string[]
}

export interface Topic {
  id: string
  title: string
  status: TopicStatus
  content?: TopicContent
  quiz?: QuizQuestion[]
  quizScore?: number       // percentage 0-100
  quizAnswers?: number[]   // user's selected answers
}

export interface Chapter {
  id: string
  title: string
  description: string
  topics: Topic[]
  order: number
}

export interface ExamPrepSession {
  id: string
  subject: string
  chapters: Chapter[]
  createdAt: string
  updatedAt: string
  overallProgress: number   // 0-100
}
