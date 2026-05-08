# LUMINA
AI Learning Platform
COMPLETE QA & TESTING DOCUMENT

Document Version: v1.0  
Project: Lumina - AI Research Teaching Agent  
Test Cases Covered: TC01 to TC60 (Core API, Research, Uploads, Exam Prep, Personalized Learning, Video Lecture, Doubt Solver, Guide/Code Tutor)  
Sections: Testing Guide | Test Case Template | Test Case Catalog | Report Structure  
Stack: Next.js + FastAPI + Python + LangGraph + LocalStorage  
Test Tools: pytest, curl, Postman/Thunder Client, Browser DevTools

---

## SECTION 1 - HOW TO TEST THIS PROJECT

This section explains how to test Lumina across backend APIs, streaming behavior, and frontend user flows.

### 1.1 Testing Architecture Overview

| Layer | Technology | Test Tool | Test Type |
|---|---|---|---|
| Backend Core | FastAPI + Python | pytest + curl/Postman | Unit + Integration + API |
| AI Orchestration | LangGraph + LLM providers | pytest + manual validation | Integration + Quality |
| Streaming APIs | SSE over HTTP | curl `-N`, Postman, browser Network tab | Streaming + Contract |
| Frontend | Next.js + React + TypeScript | Manual + DevTools | UI + E2E |
| Persistence | Browser localStorage | DevTools Application tab | State validation |

### 1.2 Setup Before Testing

Run backend and frontend before executing most test cases.

```powershell
# Terminal 1 - Backend
cd C:\Users\Vivek\Desktop\newpro\Lumina\backend
python main.py

# Terminal 2 - Frontend
cd C:\Users\Vivek\Desktop\newpro\Lumina\frontend
npm install
npm run dev
```

Verify services:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### 1.3 Automated Backend Testing (Existing Project Tests)

```powershell
cd C:\Users\Vivek\Desktop\newpro\Lumina\backend

# Run all tests
pytest -v

# Run fast structural tests only
pytest -m structural -v

# Run pedagogical heuristics
pytest -m pedagogical -v

# Run all except slow LLM-backed tests
pytest -m "not slow" -v
```

Current tests already present in project:
- `test_agents.py`
- `test_llm_evaluation.py`

### 1.4 API Testing with curl/Postman

Use these as baseline checks before deep QA runs.

```powershell
# Health checks
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/api/config

# Basic research request
curl -X POST http://localhost:8000/api/research ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What is photosynthesis?\"}"

# Streaming research request
curl -N -X POST http://localhost:8000/api/research/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Explain neural networks\"}"
```

### 1.5 Frontend Manual Testing

1. Open `http://localhost:3000`.
2. Sign up or login (email flow or provider mock flow).
3. Verify each mode from app shell:
   - Chat (Research)
   - Exam Prep
   - Personalized
   - Video Lecture
   - Doubt Solver
4. Check browser console for runtime errors.
5. Check localStorage keys update when sessions are created/deleted.

### 1.6 Data and Environment Notes

- Some endpoints depend on external providers (Mistral, Tavily, optional ElevenLabs).
- LLM variability is expected; validate response schema and behavior, not exact wording.
- For negative/error-path testing (for example credits exhausted), use controlled mocks or intentionally invalid API keys in a non-production environment.

---

## SECTION 2 - STANDARD TEST CASE TEMPLATE

Use this template to execute and record every test case from Section 3.

```text
Test Case ID:
Test Case Title:
Module:
Priority: [Critical/High/Medium/Low]
Test Type: [Functional/Validation/Security/Streaming/UI/Performance]
Preconditions:
Test Steps:
Test Data:
Expected Result:

Actual Result: [Fill after execution]
Status: [PASS/FAIL/SKIP/BLOCKED]
Tester Name:
Date Executed:
Remarks/Defects:
```

---

## SECTION 3 - TEST CASE CATALOG (TC01 TO TC60)

### Module 1: Platform Health and Configuration (TC01-TC06)

| ID | Test Case Title | Priority | Test Type | Preconditions | Test Steps | Expected Result |
|---|---|---|---|---|---|---|
| TC01 | Root health endpoint is available | Critical | Functional | Backend running | `GET /` | `200` with `status`, `service`, `version`, and `cost` fields |
| TC02 | Detailed health endpoint returns orchestrator status | Critical | Functional | Backend running | `GET /health` | `200` with `orchestrator` boolean and settings block |
| TC03 | Config endpoint returns non-sensitive configuration | High | Functional | Backend running | `GET /api/config` | `200` with limits, supported models, and features |
| TC04 | CORS preflight is accepted | High | Security/Integration | Backend running | `OPTIONS /api/research` with origin headers | `200` and CORS headers allow methods/headers |
| TC05 | Invalid method returns method not allowed | Medium | Validation | Backend running | `PUT /health` | `405 Method Not Allowed` |
| TC06 | Service-unavailable path on orchestrator-dependent endpoint | Medium | Resilience | Orchestrator intentionally unavailable | `POST /api/research` | `503` with service initialization detail |

### Module 2: Research Mode APIs and Streaming (TC07-TC18)

| ID | Test Case Title | Priority | Test Type | Preconditions | Test Steps | Expected Result |
|---|---|---|---|---|---|---|
| TC07 | Research endpoint with valid question | Critical | Functional | Backend + keys configured | `POST /api/research` with normal question | `200` and full `TeachingResponse` schema |
| TC08 | Research validation on too-short question | High | Validation | Backend running | `POST /api/research` with `"ab"` | `422` validation error |
| TC09 | Research validation on overly long question | Medium | Validation | Backend running | `POST /api/research` with >2000 chars | `422` validation error |
| TC10 | Research request accepts attachment context fields | High | Functional | Backend running | `POST /api/research` with `image_context` and `file_context` | `200`; contexts are accepted without schema failure |
| TC11 | Research stream event sequence and completion | Critical | Streaming | Backend + keys configured | `POST /api/research/stream` and consume SSE | Receives status/content events and final `complete` event |
| TC12 | Research stream emits source citations | High | Streaming | Backend + keys configured | Stream a research request | At least one `source` event with citation fields |
| TC13 | Research stream emits error event on failure | High | Resilience | Induce provider/network failure | Call stream endpoint | `error` SSE event with readable message |
| TC14 | Research endpoint handles conversation history | Medium | Functional | Backend running | Include `conversation_history` in request body | `200` without parsing/processing errors |
| TC15 | Research response includes difficulty level enum | High | Contract | Backend + keys configured | `POST /api/research` | `difficulty_level` in `beginner/intermediate/advanced` |
| TC16 | Research response includes practice questions list | High | Contract | Backend + keys configured | `POST /api/research` | `practice_questions` array exists (may be empty for edge cases) |
| TC17 | Research response processing time is positive | Medium | Contract | Backend + keys configured | `POST /api/research` | `processing_time > 0` |
| TC18 | Research stream completes without duplicate terminal events | Medium | Streaming | Backend + keys configured | Consume full SSE stream | Exactly one terminal `complete` event per request |

### Module 3: Uploads and Text-to-Speech (TC19-TC26)

| ID | Test Case Title | Priority | Test Type | Preconditions | Test Steps | Expected Result |
|---|---|---|---|---|---|---|
| TC19 | Image upload accepts supported image types | Critical | Functional | Backend running | `POST /api/upload/image` with PNG/JPEG/WebP/GIF | `200` with `preview_url` data URL |
| TC20 | Image upload rejects unsupported type | High | Validation | Backend running | Upload unsupported MIME (for example PDF) to image endpoint | `400` unsupported image type |
| TC21 | File upload extracts text from TXT/MD/CSV | High | Functional | Backend running | `POST /api/upload/file` with `.txt` | `200` with non-empty `extracted_text` |
| TC22 | File upload extracts text from DOCX | High | Functional | Backend running | `POST /api/upload/file` with `.docx` | `200` with extracted document text |
| TC23 | File upload rejects unsupported file type | High | Validation | Backend running | Upload unsupported extension (for example `.exe`) | `400` unsupported file type |
| TC24 | File upload truncates very large extracted text | Medium | Boundary | Backend running | Upload large text/PDF content | Response `char_count` capped and shows truncation marker |
| TC25 | TTS endpoint fallback behavior with empty text | Medium | Resilience | Backend running | `POST /api/tts` with empty text | Returns fallback audio response with `X-Use-Browser-TTS: true` |
| TC26 | TTS endpoint returns provider audio or browser fallback | High | Functional | Backend running | `POST /api/tts` with normal text | Returns audio bytes OR fallback header without crashing |

### Module 4: Exam Prep Mode (TC27-TC35)

| ID | Test Case Title | Priority | Test Type | Preconditions | Test Steps | Expected Result |
|---|---|---|---|---|---|---|
| TC27 | Generate roadmap for valid subject | Critical | Functional | Backend + keys configured | `POST /api/exam-prep/roadmap` with subject | `200` with `subject` and `chapters[]` |
| TC28 | Roadmap request without subject | High | Validation | Backend running | `POST /api/exam-prep/roadmap` with empty body | `400` no subject provided |
| TC29 | Roadmap service unavailable path | Medium | Resilience | Orchestrator unavailable | Call roadmap endpoint | `503` service not initialized |
| TC30 | Stream topic content for selected topic | Critical | Streaming | Backend + keys configured | `POST /api/exam-prep/topic-content/stream` | SSE includes topic, explanation data, and complete event |
| TC31 | Topic content stream without topic | High | Validation | Backend running | Call stream endpoint with no topic | `400` no topic provided |
| TC32 | Quiz generation for valid topic | Critical | Functional | Backend + keys configured | `POST /api/exam-prep/quiz` | `200` with `questions[]`, each question has options and answer |
| TC33 | Quiz request without topic | High | Validation | Backend running | `POST /api/exam-prep/quiz` with missing topic | `400` no topic provided |
| TC34 | Quiz response enforces per-question IDs | Medium | Contract | Backend + keys configured | Generate quiz and inspect payload | Questions include generated IDs (`q_0`, `q_1`, ...) |
| TC35 | Quiz malformed LLM output handling | Medium | Resilience | Force malformed provider output | Generate quiz | Returns controlled error (`500`) instead of crash loop |

### Module 5: Personalized Learning Mode (TC36-TC44)

| ID | Test Case Title | Priority | Test Type | Preconditions | Test Steps | Expected Result |
|---|---|---|---|---|---|---|
| TC36 | Generate diagnostic assessment | Critical | Functional | Backend + keys configured | `POST /api/personalized/assess` with topic | `200` with `topic` and assessment questions |
| TC37 | Assessment request without topic | High | Validation | Backend running | `POST /api/personalized/assess` empty topic | `400` no topic provided |
| TC38 | Analyze learner profile with valid answers | Critical | Functional | Assessment data available | `POST /api/personalized/analyze-profile` | `200` with level, score, strengths, weaknesses, learning plan |
| TC39 | Analyze profile missing required fields | High | Validation | Backend running | Omit topic/questions/answers | `400` missing required data |
| TC40 | Knowledge level classification logic | High | Logic | Backend running | Send crafted answers for low/medium/high scores | Returns beginner/intermediate/advanced as expected |
| TC41 | Personalized learning stream for a topic | Critical | Streaming | Profile data available | `POST /api/personalized/learn/stream` | SSE includes personalized status, explanation, and complete |
| TC42 | Personalized stream without topic | High | Validation | Backend running | Call personalized stream with empty topic | `400` no topic provided |
| TC43 | Personalized stream includes cost event | Medium | Contract | Backend + keys configured | Consume full personalized SSE | Receives `cost` event before complete |
| TC44 | Profile analysis handles short answer arrays safely | Medium | Boundary | Backend running | Send fewer answers than questions | No index crash; response still returned |

### Module 6: Video Lecture Mode (TC45-TC52)

| ID | Test Case Title | Priority | Test Type | Preconditions | Test Steps | Expected Result |
|---|---|---|---|---|---|---|
| TC45 | Generate full video lecture package | Critical | Functional | Backend + keys configured | `POST /api/video-lecture/generate` with topic | `200` with slides, narration fields, and cost |
| TC46 | Video lecture generation without topic | High | Validation | Backend running | Call generate endpoint with empty topic | `400` no topic provided |
| TC47 | Stream video lecture generation | Critical | Streaming | Backend + keys configured | `POST /api/video-lecture/generate/stream` | SSE emits metadata, slide events, and complete |
| TC48 | Video lecture stream without topic | High | Validation | Backend running | Call stream endpoint with empty topic | `400` no topic provided |
| TC49 | Narrate single slide with valid text | High | Functional | Backend running | `POST /api/video-lecture/narrate-slide` | `200` with audio payload/fallback fields |
| TC50 | Narrate single slide with missing text | High | Validation | Backend running | Call narrate endpoint with empty text | `400` no text provided |
| TC51 | Slide count parameter behavior | Medium | Boundary | Backend + keys configured | Generate with custom `num_slides` | Output slide count aligns with request intent |
| TC52 | Image resolution fallback robustness | Medium | Resilience | Backend + keys configured | Simulate partial image search failures | Endpoint still returns slides without hard failure |

### Module 7: Doubt Solver Mode (TC53-TC58)

| ID | Test Case Title | Priority | Test Type | Preconditions | Test Steps | Expected Result |
|---|---|---|---|---|---|---|
| TC53 | Solve doubt from uploaded image | Critical | Functional | Backend + keys configured | `POST /api/doubt-solver/solve` with image + question | `200` with `solution` text |
| TC54 | Doubt solver rejects unsupported file type | High | Validation | Backend running | Upload non-image file to solve endpoint | `400` unsupported image type |
| TC55 | Doubt solver chat with text message only | High | Functional | Backend + keys configured | `POST /api/doubt-solver/chat` with message | `200` with assistant response |
| TC56 | Doubt solver chat with image context | Medium | Functional | Backend + keys configured | Send `image_base64` with/without message | `200`; response includes optional `image_context` note |
| TC57 | Doubt solver chat with no message and no image | High | Validation | Backend running | Send empty body | `400` no message or image provided |
| TC58 | Doubt solver quota/payment error mapping | Medium | Resilience | Simulated credit exhaustion | Trigger provider credit error | `402` with quota guidance message |

### Module 8: Guide Chatbot and Code Tutor (TC59-TC60)

| ID | Test Case Title | Priority | Test Type | Preconditions | Test Steps | Expected Result |
|---|---|---|---|---|---|---|
| TC59 | Guide chatbot response in mode context | High | Functional | Backend + keys configured | `POST /api/guide/chat` with `mode`, `context`, `message` | `200` with structured tutor response |
| TC60 | Code tutor chat response with coding context | High | Functional | Backend + keys configured | `POST /api/code-ai/chat` with message + code snippet | `200` with actionable coding guidance |

---

## SECTION 4 - FRONTEND REGRESSION CHECKLIST (MANUAL)

Use this list after backend API tests to validate the full user experience.

1. Auth flow:
   - Signup creates pending account in localStorage.
   - Verification code flow marks user verified.
   - Login fails for unverified users and succeeds after verification.
2. Chat mode:
   - Send text-only query and confirm streamed answer rendering.
   - Upload image and document and confirm attachment context is used.
   - Confirm chat history persists and reloads.
3. Exam Prep mode:
   - Generate roadmap, open chapter/topic, stream topic content, run quiz.
4. Personalized mode:
   - Complete assessment, generate profile, stream a learning topic.
5. Video Lecture mode:
   - Generate slide deck, play narration, verify fallback if needed.
6. Doubt Solver mode:
   - Upload an image and get a solution.
   - Continue conversation in chat follow-up.
7. Unified history sidebar:
   - Open prior sessions by mode.
   - Delete entries and verify state consistency.

---

## SECTION 5 - TEST EXECUTION REPORT STRUCTURE

Use this format for daily or release-level QA reporting.

### 5.1 Test Summary

| Metric | Value |
|---|---|
| Total Test Cases Planned | 60 |
| Total Executed | |
| Passed | |
| Failed | |
| Skipped | |
| Blocked | |
| Pass Percentage | |

Pass Percentage formula:

`(Passed / Executed) * 100`

### 5.2 Defect Log Template

| Defect ID | Linked TC | Severity | Environment | Steps to Reproduce | Expected | Actual | Status |
|---|---|---|---|---|---|---|---|
| BUG-001 | TCxx | Critical/High/Medium/Low | Local/Staging/Prod | | | | Open/In Progress/Fixed/Closed |

### 5.3 Release Sign-Off Checklist

- All Critical test cases passed.
- No open Critical defects.
- High-severity defects accepted or fixed.
- Streaming endpoints validated end-to-end.
- Frontend regression checklist completed.

---

## SECTION 6 - RECOMMENDED NEXT AUTOMATION ADDITIONS

To increase long-term reliability, add these in future test sprints:

1. API contract tests for all 21 endpoints (status + schema checks).
2. SSE contract tests validating event order and terminal events.
3. Frontend E2E suite (Playwright) for mode switching and history persistence.
4. Provider-fallback tests (LLM/TTS) using mocked failure modes.
5. CI pipeline stages for `pytest -m "not slow"` on every PR.
