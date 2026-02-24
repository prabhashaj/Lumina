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

// ── Personalized Learning Types ──────────────────────────────

export type KnowledgeLevel = 'beginner' | 'intermediate' | 'advanced'
export type LearningStyle = 'visual' | 'textual' | 'example-driven' | 'practice-heavy'
export type PersonalizedTopicStatus = 'not-started' | 'in-progress' | 'completed'

export interface AssessmentQuestion {
  id: string
  question: string
  options: string[]
  correctIndex: number
  difficulty: 'foundational' | 'intermediate' | 'advanced'
  cognitiveLevel: string
  subTopic: string
}

export interface PlanTopic {
  title: string
  reason: string
  approach: string
  estimatedMinutes: number
  status?: PersonalizedTopicStatus
  content?: TopicContent
}

export interface LearningPhase {
  phase: number
  title: string
  description: string
  topics: PlanTopic[]
  technique: string
}

export interface LearnerProfile {
  knowledgeLevel: KnowledgeLevel
  overallScore: number
  strengthAreas: string[]
  weaknessAreas: string[]
  learningPlan: LearningPhase[]
  personalizedTips: string[]
  recommendedStyle: LearningStyle
  motivationalNote: string
}

export interface PersonalizedSession {
  id: string
  subject: string
  profile: LearnerProfile
  assessmentQuestions: AssessmentQuestion[]
  assessmentAnswers: number[]
  createdAt: string
  updatedAt: string
  overallProgress: number // 0-100
}

// ── Video Lecture / Slide Types ──────────────────────────────

export type SlideLayout = 'title' | 'default' | 'image-focus' | 'comparison' | 'summary'

export interface Slide {
  slide_number: number
  title: string
  bullet_points: string[]
  speaker_notes: string
  image_query: string
  layout: SlideLayout
  background_style: string
  // Injected after narration generation
  audio_base64?: string
  use_browser_tts?: boolean
  narration_text?: string
  duration_estimate?: number
  // Resolved image from Unsplash
  image_url?: string
}

export interface Presentation {
  title: string
  subtitle: string
  total_slides: number
  estimated_duration_minutes: number
  slides: Slide[]
}

export interface VideoLectureSession {
  id: string
  topic: string
  presentation: Presentation | null
  createdAt: string
  status: 'idle' | 'generating' | 'ready' | 'error'
  error?: string
}

// ── Doubt Solver Types ──────────────────────────────

export interface DoubtSolverResult {
  filename: string
  preview_url: string
  ocr_text: string
  solution: string
}

export interface DoubtMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  imagePreview?: string       // local data URL for display
  imageContext?: string       // VLM extracted text
  isLoading?: boolean
}

export interface GuideMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isLoading?: boolean
}
