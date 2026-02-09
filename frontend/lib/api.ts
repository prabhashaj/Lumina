const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function streamResearch(
  question: string,
  onChunk: (chunk: any) => void,
  imageContext?: string,
  fileContext?: string
): Promise<void> {
  const body: any = { question }
  if (imageContext) body.image_context = imageContext
  if (fileContext) body.file_context = fileContext

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
