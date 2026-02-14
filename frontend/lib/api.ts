const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function streamResearch(
  question: string,
  onChunk: (chunk: any) => void,
  imageContext?: string,
  fileContext?: string,
  conversationHistory?: { role: string; content: string }[]
): Promise<void> {
  const body: any = { question }
  if (imageContext) body.image_context = imageContext
  if (fileContext) body.file_context = fileContext
  if (conversationHistory && conversationHistory.length > 0) {
    body.conversation_history = conversationHistory
  }

  const response = await fetch(`${API_URL}/api/research/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) {
    throw new Error('No reader available')
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          try {
            const parsed = JSON.parse(data)
            onChunk(parsed)
          } catch (e) {
            console.error('Failed to parse chunk:', e)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function askQuestion(question: string): Promise<any> {
  const response = await fetch(`${API_URL}/api/research`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export async function uploadImage(file: File, question: string = ''): Promise<{
  filename: string
  analysis: string
  preview_url: string
}> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('question', question)

  const response = await fetch(`${API_URL}/api/upload/image`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`)
  }

  return response.json()
}

export async function uploadFile(file: File): Promise<{
  filename: string
  extracted_text: string
  char_count: number
}> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_URL}/api/upload/file`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`)
  }

  return response.json()
}

export async function textToSpeech(text: string): Promise<{ audio: Blob | null, useBrowserTTS: boolean }> {
  try {
    const response = await fetch(`${API_URL}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })

    if (response.headers.get('X-Use-Browser-TTS') === 'true' || !response.ok) {
      return { audio: null, useBrowserTTS: true }
    }

    const blob = await response.blob()
    if (blob.size === 0) {
      return { audio: null, useBrowserTTS: true }
    }

    return { audio: blob, useBrowserTTS: false }
  } catch {
    return { audio: null, useBrowserTTS: true }
  }
}

// ── Exam Prep API ──────────────────────────────

export async function generateRoadmap(subject: string): Promise<{
  subject: string
  chapters: { title: string; description: string; topics: string[] }[]
}> {
  const response = await fetch(`${API_URL}/api/exam-prep/roadmap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject }),
  })

  if (!response.ok) {
    throw new Error(`Roadmap generation failed: ${response.status}`)
  }

  return response.json()
}

export async function streamTopicContent(
  subject: string,
  chapter: string,
  topic: string,
  onChunk: (chunk: any) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/exam-prep/topic-content/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, chapter, topic }),
  })

  if (!response.ok) {
    throw new Error(`Topic content generation failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) throw new Error('No reader available')

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(line.slice(6))
            onChunk(parsed)
          } catch (e) {
            console.error('Failed to parse chunk:', e)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function generateQuiz(
  subject: string,
  chapter: string,
  topic: string
): Promise<{ questions: { id: string; question: string; options: string[]; correctIndex: number; explanation: string }[] }> {
  const response = await fetch(`${API_URL}/api/exam-prep/quiz`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, chapter, topic }),
  })

  if (!response.ok) {
    throw new Error(`Quiz generation failed: ${response.status}`)
  }

  return response.json()
}

// ── Personalized Learning API ──────────────────────────────

export async function generateAssessment(topic: string): Promise<{
  topic: string
  questions: { id: string; question: string; options: string[]; correctIndex: number; difficulty: string; cognitiveLevel: string; subTopic: string }[]
}> {
  const response = await fetch(`${API_URL}/api/personalized/assess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  })

  if (!response.ok) {
    throw new Error(`Assessment generation failed: ${response.status}`)
  }

  return response.json()
}

export async function analyzeLearnerProfile(
  topic: string,
  questions: any[],
  answers: number[]
): Promise<any> {
  const response = await fetch(`${API_URL}/api/personalized/analyze-profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, questions, answers }),
  })

  if (!response.ok) {
    throw new Error(`Profile analysis failed: ${response.status}`)
  }

  return response.json()
}

export async function streamPersonalizedContent(
  topic: string,
  knowledgeLevel: string,
  weakAreas: string[],
  strongAreas: string[],
  learningStyle: string,
  approach: string,
  phaseTitle: string,
  subject: string,
  onChunk: (chunk: any) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/personalized/learn/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic,
      knowledgeLevel,
      weakAreas,
      strongAreas,
      learningStyle,
      approach,
      phaseTitle,
      subject,
    }),
  })

  if (!response.ok) {
    throw new Error(`Personalized content generation failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) throw new Error('No reader available')

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(line.slice(6))
            onChunk(parsed)
          } catch (e) {
            console.error('Failed to parse chunk:', e)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

// ── Video Lecture / Slide Generation API ──────────────────────────────

export async function generateVideoLecture(
  topic: string,
  numSlides: number = 10,
  difficulty: string = 'intermediate'
): Promise<any> {
  const response = await fetch(`${API_URL}/api/video-lecture/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, num_slides: numSlides, difficulty }),
  })

  if (!response.ok) {
    throw new Error(`Video lecture generation failed: ${response.status}`)
  }

  return response.json()
}

export async function streamVideoLecture(
  topic: string,
  numSlides: number,
  difficulty: string,
  onChunk: (chunk: any) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/video-lecture/generate/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, num_slides: numSlides, difficulty }),
  })

  if (!response.ok) {
    throw new Error(`Video lecture stream failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) throw new Error('No reader available')

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(line.slice(6))
            onChunk(parsed)
          } catch (e) {
            console.error('Failed to parse chunk:', e)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function narrateSingleSlide(text: string): Promise<{
  audio_base64: string
  use_browser_tts: boolean
  text: string
  duration_estimate: number
}> {
  const response = await fetch(`${API_URL}/api/video-lecture/narrate-slide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })

  if (!response.ok) {
    throw new Error(`Narration failed: ${response.status}`)
  }

  return response.json()
}

// ── Doubt Solver API ──────────────────────────────

export async function solveDoubt(file: File, question: string = ''): Promise<{
  filename: string
  preview_url: string
  ocr_text: string
  solution: string
}> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('question', question)

  const response = await fetch(`${API_URL}/api/doubt-solver/solve`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Doubt solver failed: ${response.status}`)
  }

  return response.json()
}

// ── Doubt Solver Chat API ──────────────────────────────

export async function doubtSolverChat(
  message: string,
  conversationHistory: { role: string; content: string }[],
  imageBase64?: string,
  imageType?: string
): Promise<{ response: string; image_context?: string | null }> {
  const body: any = {
    message,
    conversation_history: conversationHistory,
  }
  if (imageBase64) {
    body.image_base64 = imageBase64
    body.image_type = imageType || 'image/png'
  }

  const response = await fetch(`${API_URL}/api/doubt-solver/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Doubt solver chat failed: ${response.status}`)
  }

  return response.json()
}

// ── Guide Chatbot API ──────────────────────────────

export async function guideChat(
  message: string,
  mode: string,
  context: string,
  conversationHistory: { role: string; content: string }[]
): Promise<{ response: string }> {
  const response = await fetch(`${API_URL}/api/guide/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      mode,
      context,
      conversation_history: conversationHistory,
    }),
  })

  if (!response.ok) {
    throw new Error(`Guide chat failed: ${response.status}`)
  }

  return response.json()
}

// ── Flashcard API ──────────────────────────────

export async function generateFlashcards(
  topic: string,
  content?: string,
  count?: number
): Promise<{ cards: { front: string; back: string; difficulty: number }[]; topic: string }> {
  const response = await fetch(`${API_URL}/api/flashcards/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, content, count }),
  })

  if (!response.ok) {
    throw new Error(`Flashcard generation failed: ${response.status}`)
  }

  return response.json()
}

// ── Code Playground API ──────────────────────────────

export async function runCode(
  code: string,
  language: string,
  stdin?: string
): Promise<{ stdout: string; stderr: string; exitCode: number; executionTime: number }> {
  const response = await fetch(`${API_URL}/api/code-playground/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, language, stdin }),
  })

  if (!response.ok) {
    throw new Error(`Code execution failed: ${response.status}`)
  }

  return response.json()
}

export async function explainCode(
  code: string,
  language: string,
  action: 'explain' | 'debug' | 'exercise' | 'optimize',
  error?: string
): Promise<{ result: string; action: string }> {
  const response = await fetch(`${API_URL}/api/code-playground/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, language, action, error }),
  })

  if (!response.ok) {
    throw new Error(`Code explain failed: ${response.status}`)
  }

  return response.json()
}