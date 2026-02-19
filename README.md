# Lumina AI Research Teaching Agent

Production-grade, multi-agent learning platform that researches the web, synthesizes teaching-quality explanations, and delivers multiple learning modes (research, exam prep, personalized learning, video lectures, and doubt solving).

## Highlights

- Multi-agent orchestration with LangGraph and a quality gate
- Real-time web research with Tavily and source citations
- Visual understanding pipeline with VLM fallbacks
- Streaming UI using Server-Sent Events (SSE)
- Exam prep roadmaps, topic content, quizzes, and progress tracking
- Personalized learning assessments and adaptive plans
- Video lecture slide generation with narration and images
- Doubt solver for image-based questions and follow-up chat
- Flashcard generation and spaced-repetition storage
- Code playground (run and explain) endpoints

## Modes and Features

### Research Mode
- Intent classification (difficulty, question type, learning needs)
- Live web search and content extraction
- Visual explanation with image ranking and captions
- Teaching synthesis: TL;DR, step-by-step explanation, analogy, practice questions
- Source citations and confidence metadata
- Streaming responses with progress updates

### Exam Prep Mode
- Curriculum roadmap generation (chapters and topics)
- Topic content streaming (reuses research pipeline)
- Quiz generation with explanations
- Topic unlocking and progress tracking (local storage)

### Personalized Learning Mode
- Diagnostic assessment (6 questions across difficulty levels)
- Learner profile analysis (strengths, weaknesses, learning style)
- Multi-phase learning plan with topic-level guidance
- Personalized content streaming with style-aware prompts

### Video Lecture Mode
- Slide deck generation with layouts and speaker notes
- Slide-specific image search and attachment
- Narration generation (ElevenLabs or browser TTS fallback)
- Streaming lecture generation and per-slide audio

### Doubt Solver Mode
- Image upload and VLM-based OCR/diagram understanding
- Step-by-step explanation and practice problems
- Chat-based follow-ups with optional image context

### Guide Chatbot
- Context-aware tutor for exam prep, personalized learning, and video lecture modes
- Short, structured responses with LaTeX support

### Flashcards
- Flashcard generation endpoint
- SM-2 spaced repetition scheduling and local storage

### Code Playground
- Run Python and JavaScript code in a sandboxed subprocess
- Explain, debug, optimize, or generate exercises with an LLM

## Architecture Overview

Research pipeline (LangGraph):

Student question
  -> Intent Classifier
  -> Search Router (plan + query strategy)
  -> Web Search (Tavily)
  -> Content Extraction
  -> Image Understanding (VLM)
  -> Teaching Synthesis
  -> Quality Assessment + Retry
  -> Streaming Response (SSE)

Key components:
- Backend: FastAPI, LangChain, LangGraph
- Frontend: Next.js (App Router) + TypeScript
- Shared schemas and prompt templates

## Repository Structure

- backend
  - main.py (FastAPI endpoints)
  - agents (intent, search, extraction, images, synthesis, slides, narration)
  - graph (LangGraph orchestrator)
  - config (settings and env loading)
  - tools (cost tracking)
- frontend
  - app (landing, auth, app shell)
  - components (research chat, exam prep, personalized, video lecture, doubt solver)
  - lib (API calls, storage, auth, types)
- shared
  - schemas (Pydantic models)
  - prompts (LLM prompt templates)

## Tech Stack

Backend
- FastAPI, Uvicorn
- LangChain, LangGraph
- Tavily (web search)
- Loguru (logging)
- Optional: Replicate, ElevenLabs, Redis

Frontend
- Next.js, React, TypeScript
- Tailwind CSS
- SSE streaming and Markdown rendering

AI Providers (priority varies per agent)
- OpenRouter (free router, optional)
- Mistral API (default in settings)
- Groq
- OpenAI

## Setup

### Quickstart

Windows:

```
cd ai-research-agent
.\quickstart.bat
```

Mac or Linux:

```
cd ai-research-agent
chmod +x quickstart.sh
./quickstart.sh
```

### Manual setup

Backend:

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

Frontend:

```
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## Configuration

Environment variables are read from backend/.env and frontend/.env.local.

Required (minimum):
- TAVILY_API_KEY
- OPENAI_API_KEY or MISTRAL_API_KEY or GROQ_API_KEY or OPENROUTER_API_KEY

Optional:
- REPLICATE_API_TOKEN (image understanding)
- ELEVENLABS_API_KEY (TTS)
- OPENROUTER_API_KEY (free router)
- CORS_ORIGINS, LOG_LEVEL, LOG_FILE, CACHE_TTL

Model selection order (most agents):
1) OpenRouter free router (if OPENROUTER_API_KEY)
2) Mistral API (if MISTRAL_API_KEY)
3) Groq (if GROQ_API_KEY)
4) OpenAI (if OPENAI_API_KEY)

## API Endpoints (Summary)

Core:
- POST /api/research
- POST /api/research/stream
- GET /api/config

Uploads and TTS:
- POST /api/upload/image
- POST /api/upload/file
- POST /api/tts

Exam prep:
- POST /api/exam-prep/roadmap
- POST /api/exam-prep/topic-content/stream
- POST /api/exam-prep/quiz

Personalized learning:
- POST /api/personalized/assess
- POST /api/personalized/analyze-profile
- POST /api/personalized/learn/stream

Video lecture:
- POST /api/video-lecture/generate
- POST /api/video-lecture/generate/stream
- POST /api/video-lecture/narrate-slide

Doubt solver:
- POST /api/doubt-solver/solve
- POST /api/doubt-solver/chat

Guide chatbot:
- POST /api/guide/chat

Flashcards:
- POST /api/flashcards/generate

Code playground:
- POST /api/code-playground/run
- POST /api/code-playground/explain

Code tutor:
- POST /api/code-ai/chat

## Local Storage

The frontend persists state in localStorage:
- Auth sessions and verification
- Research chat history
- Exam prep sessions and progress
- Personalized learning sessions and progress
- Flashcard decks and spaced repetition schedules

## Logging and Cost Tracking

- Application logs: backend/logs/app.log (configurable)
- Tavily cost summary logged to logs.txt in the repo root

## Development

Backend:
- Start: python main.py
- Tests: pytest

Frontend:
- Start: npm run dev
- Build: npm run build

See SETUP.md and DEVELOPMENT.md for details.

## Deployment

- Backend: render.yaml included for Render deployment
- Frontend: Next.js app suitable for Vercel or any Node host

## Known Limitations

- Redis and vector DBs are configured but not wired into the current flow
- Auth is localStorage-based and is not a production auth system
- Code playground uses subprocess and should be sandboxed further for production
