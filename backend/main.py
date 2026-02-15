"""
FastAPI main application
"""
import sys
import re
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from contextlib import asynccontextmanager
import json
import io
import base64
from loguru import logger
from langchain_openai import ChatOpenAI

from config.settings import settings
from graph.orchestrator import ResearchOrchestrator
from shared.schemas.models import ResearchRequest, TeachingResponse, ErrorResponse


def _safe_json_loads(raw: str) -> dict:
    """Parse JSON from LLM output, handling various malformed JSON issues."""
    import re as _re

    # Step 1: Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Step 2: Clean common LLM JSON issues
    cleaned = raw
    # Remove trailing commas before } or ]
    cleaned = _re.sub(r',\s*([}\]])', r'\1', cleaned)
    # Fix invalid escape sequences
    cleaned = _re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 3: Try to extract just the outermost JSON object more carefully
    # Find the first { and match braces
    start = raw.find('{')
    if start == -1:
        raise ValueError("No JSON object found in LLM response")

    depth = 0
    in_string = False
    escape_next = False
    end = start
    for i in range(start, len(raw)):
        c = raw[i]
        if escape_next:
            escape_next = False
            continue
        if c == '\\':
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    extracted = raw[start:end]
    # Clean the extracted JSON
    extracted = _re.sub(r',\s*([}\]])', r'\1', extracted)
    extracted = _re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', extracted)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        pass

    # Step 4: Last resort — use ast.literal_eval-style cleanup
    # Remove control characters except \n \r \t
    extracted = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', extracted)
    # Replace single quotes with double quotes (in case LLM used Python-style)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed after all fixes. Error: {e}")
        logger.error(f"First 500 chars of raw: {raw[:500]}")
        raise ValueError(f"Could not parse JSON from LLM response: {e}")


# Initialize logger
import os as _os
_log_dir = _os.path.dirname(settings.log_file)
if _log_dir:
    _os.makedirs(_log_dir, exist_ok=True)
try:
    logger.add(
        settings.log_file,
        rotation="500 MB",
        retention="10 days",
        level=settings.log_level
    )
except Exception:
    # On read-only filesystems (e.g. Render free tier), skip file logging
    logger.warning("Could not set up file logging, using stdout only")

# Global orchestrator instance
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator
    
    logger.info("Starting AI Research Teaching Agent...")
    try:
        orchestrator = ResearchOrchestrator()
        logger.info("Orchestrator initialized")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        orchestrator = None
    
    yield
    
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI Research Teaching Agent",
    description="Multi-agent system for intelligent research and teaching",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
_cors_origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Research Teaching Agent",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "orchestrator": orchestrator is not None,
        "settings": {
            "llm_model": settings.primary_llm_model,
            "max_search_results": settings.max_search_results,
            "max_images": settings.max_images_per_response
        }
    }


# ─── Code AI Tutor ───────────────────────────────────────────────

_code_ai_llm = None

def _get_code_ai_llm():
    """Lazy-init an LLM for the code tutor using same priority as teaching agents."""
    global _code_ai_llm
    if _code_ai_llm is None:
        if settings.mistral_api_key:
            _code_ai_llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.7,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
            )
        elif settings.groq_api_key:
            _code_ai_llm = ChatOpenAI(
                model=settings.groq_model,
                temperature=0.7,
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        else:
            _code_ai_llm = ChatOpenAI(
                model=settings.primary_llm_model,
                temperature=0.7,
                api_key=settings.openai_api_key,
            )
    return _code_ai_llm


@app.post("/api/code-ai/chat")
async def code_ai_chat(request: dict):
    """
    AI coding tutor chat endpoint.
    Accepts: message, systemPrompt, code, language, questionTitle,
             questionDescription, output, error, history
    Returns: { response: str }
    """
    try:
        from langchain_core.messages import SystemMessage, HumanMessage as HMsg, AIMessage

        llm = _get_code_ai_llm()

        system_prompt = request.get("systemPrompt", "You are a helpful coding tutor.")
        user_message = request.get("message", "")
        code = request.get("code", "")
        language = request.get("language", "python")
        question_title = request.get("questionTitle", "")
        question_desc = request.get("questionDescription", "")
        output = request.get("output", "")
        error = request.get("error", "")
        history = request.get("history", [])

        # Build context block
        context_parts = []
        if question_title:
            context_parts.append(f"**Problem:** {question_title}")
        if question_desc:
            context_parts.append(f"**Description:** {question_desc}")
        if code:
            context_parts.append(f"**Student's {language} code:**\n```{language}\n{code}\n```")
        if output:
            context_parts.append(f"**Program output:**\n```\n{output}\n```")
        if error:
            context_parts.append(f"**Error:**\n```\n{error}\n```")

        context_block = "\n\n".join(context_parts)

        # Build messages list
        messages = [SystemMessage(content=system_prompt)]

        # Add history
        for h in history[-6:]:
            if h.get("role") == "user":
                messages.append(HMsg(content=h["content"]))
            elif h.get("role") == "assistant":
                messages.append(AIMessage(content=h["content"]))

        # Add current user message with context
        full_user_message = f"{context_block}\n\n---\n\n{user_message}" if context_block else user_message
        messages.append(HMsg(content=full_user_message))

        result = await llm.ainvoke(messages)
        return {"response": result.content}

    except Exception as e:
        logger.error(f"Code AI chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI chat error: {str(e)}")


@app.post("/api/research", response_model=TeachingResponse)
async def research_question(request: ResearchRequest):
    """
    Process a research question and return comprehensive teaching content
    
    This endpoint orchestrates multiple AI agents to:
    1. Understand the question
    2. Search the web for information
    3. Extract and analyze content
    4. Process relevant images
    5. Synthesize teaching-quality explanations
    """
    try:
        logger.info(f"Received research request: {request.question[:100]}...")
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Process through the orchestrator
        response = await orchestrator.process_question(request)
        
        return response
        
    except Exception as e:
        logger.error(f"Research error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing research request: {str(e)}"
        )


@app.post("/api/research/stream")
async def research_question_stream(request: ResearchRequest):
    """
    Stream research results as they become available
    
    Provides real-time updates as each agent completes its work.
    Returns Server-Sent Events (SSE) stream.
    """
    async def generate_stream():
        """Generate streaming response"""
        try:
            logger.info(f"Starting streaming research: {request.question[:100]}...")
            
            # Send status update: Starting
            yield f"data: {json.dumps({'type': 'status', 'data': 'Analyzing question...'})}\n\n"
            
            # Build enriched question with any attached context
            enriched_question = request.question
            if request.image_context:
                enriched_question += f"\n\n[User attached an image with the following content: {request.image_context}]"
            if request.file_context:
                enriched_question += f"\n\n[User attached a document with the following content:\n{request.file_context[:5000]}]"
            
            # Create enriched request
            enriched_request = ResearchRequest(
                question=enriched_question,
                conversation_history=request.conversation_history,
                user_id=request.user_id,
                session_id=request.session_id
            )
            
            # Classify intent
            intent = await orchestrator.intent_agent.analyze(enriched_question)
            yield f"data: {json.dumps({'type': 'status', 'data': f'Difficulty: {intent.difficulty_level.value}', 'intent': intent.dict()})}\n\n"
            
            # Search
            yield f"data: {json.dumps({'type': 'status', 'data': 'Searching the web...'})}\n\n"
            
            # Run full workflow
            response = await orchestrator.process_question(enriched_request)
            
            # Stream the complete response
            yield f"data: {json.dumps({'type': 'status', 'data': 'Synthesizing teaching content...'})}\n\n"
            
            # Send TL;DR first
            yield f"data: {json.dumps({'type': 'topic', 'data': response.question})}\n\n"
            yield f"data: {json.dumps({'type': 'tldr', 'data': response.tldr})}\n\n"
            
            # Send explanation
            yield f"data: {json.dumps({'type': 'explanation', 'data': response.explanation.dict()})}\n\n"
            
            # Send images
            for img in response.images:
                yield f"data: {json.dumps({'type': 'image', 'data': img.dict()})}\n\n"
            
            # Send sources
            for source in response.sources:
                yield f"data: {json.dumps({'type': 'source', 'data': source.dict()})}\n\n"
            
            # Send analogy
            yield f"data: {json.dumps({'type': 'analogy', 'data': response.analogy})}\n\n"
            
            # Send practice questions
            logger.info(f"Streaming {len(response.practice_questions)} practice questions")
            for idx, q in enumerate(response.practice_questions, 1):
                logger.info(f"  Streaming Q{idx}: {q[:80]}")
                yield f"data: {json.dumps({'type': 'practice_question', 'data': q})}\n\n"
            
            # Send complete signal
            yield f"data: {json.dumps({'type': 'complete', 'data': response.dict()})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.get("/api/config")
async def get_config():
    """Get current configuration (non-sensitive)"""
    return {
        "max_search_results": settings.max_search_results,
        "max_images_per_response": settings.max_images_per_response,
        "cache_ttl": settings.cache_ttl,
        "supported_models": {
            "llm": settings.primary_llm_model,
            "embedding": settings.embedding_model,
            "vlm": settings.vlm_model
        },
        "features": {
            "tts_enabled": bool(settings.elevenlabs_api_key),
            "vlm_enabled": bool(settings.replicate_api_token),
            "file_upload": True
        }
    }


@app.post("/api/upload/image")
async def upload_and_analyze_image(file: UploadFile = File(...), question: str = Form("")):
    """Upload an image and analyze it with VLM to extract context"""
    try:
        logger.info(f"Received image upload: {file.filename}, size: {file.size}")
        
        # Read file content
        content = await file.read()
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")
        
        # Convert to base64 data URL for VLM
        b64_data = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{file.content_type};base64,{b64_data}"
        
        # Analyze with VLM
        vlm_description = await _analyze_image_with_vlm(data_url, question)
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "analysis": vlm_description,
            "preview_url": data_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/file")
async def upload_and_extract_file(file: UploadFile = File(...)):
    """Upload a document (PDF, DOCX, TXT) and extract its text content"""
    try:
        logger.info(f"Received file upload: {file.filename}")
        
        content = await file.read()
        extracted_text = ""
        
        if file.content_type == "application/pdf" or (file.filename and file.filename.endswith(".pdf")):
            # Extract text from PDF
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(io.BytesIO(content))
                pages = []
                for page in reader.pages[:20]:  # Limit to 20 pages
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                extracted_text = "\n\n".join(pages)
            except Exception as pdf_err:
                logger.error(f"PDF extraction error: {pdf_err}")
                extracted_text = "[Could not extract PDF content]"
                
        elif file.content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"] or (file.filename and file.filename.endswith(".docx")):
            # Extract text from DOCX
            try:
                from docx import Document
                doc = Document(io.BytesIO(content))
                extracted_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            except Exception as docx_err:
                logger.error(f"DOCX extraction error: {docx_err}")
                extracted_text = "[Could not extract DOCX content]"
                
        elif file.content_type in ["text/plain", "text/markdown", "text/csv"] or (file.filename and file.filename.endswith((".txt", ".md", ".csv"))):
            extracted_text = content.decode("utf-8", errors="replace")
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type or file.filename}")
        
        # Truncate to reasonable length
        if len(extracted_text) > 15000:
            extracted_text = extracted_text[:15000] + "\n\n[Content truncated...]"
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "extracted_text": extracted_text,
            "char_count": len(extracted_text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts")
async def text_to_speech(request: dict):
    """Convert text to speech using ElevenLabs API"""
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        # Truncate very long text to avoid API limits
        if len(text) > 5000:
            text = text[:5000]
        
        if not settings.elevenlabs_api_key:
            # Fallback: Use browser TTS (return empty with flag)
            return Response(content=b"", media_type="audio/mpeg", headers={"X-Use-Browser-TTS": "true"})
        
        # Use ElevenLabs API
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{settings.tts_voice_id}",
                headers={
                    "xi-api-key": settings.elevenlabs_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": settings.tts_model,
                    "voice_settings": {
                        "stability": 0.82,
                        "similarity_boost": 0.88,
                        "style": 0.08,
                        "use_speaker_boost": True
                    }
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"ElevenLabs API error: {response.status_code} - falling back to browser TTS")
                return Response(content=b"", media_type="audio/mpeg", headers={"X-Use-Browser-TTS": "true"})
            
            return Response(
                content=response.content,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline",
                    "Cache-Control": "no-cache"
                }
            )
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        return Response(content=b"", media_type="audio/mpeg", headers={"X-Use-Browser-TTS": "true"})


# ── Exam Prep Endpoints ──────────────────────────────

@app.post("/api/exam-prep/roadmap")
async def generate_exam_roadmap(request: dict):
    """Generate a chapter-wise syllabus/roadmap for a subject"""
    try:
        subject = request.get("subject", "").strip()
        if not subject:
            raise HTTPException(status_code=400, detail="No subject provided")

        logger.info(f"Generating exam prep roadmap for: {subject}")

        if not orchestrator:
            raise HTTPException(status_code=503, detail="Service not initialized")

        # Use the teaching agent's LLM to generate a structured roadmap
        from agents.teaching_synthesis import TeachingSynthesisAgent
        agent: TeachingSynthesisAgent = orchestrator.teaching_agent

        roadmap_prompt = f"""You are an expert curriculum designer. Create a comprehensive study roadmap for the subject: "{subject}".

Generate a structured syllabus with 5-8 chapters. Each chapter should have 3-6 specific topics.

Rules:
- Chapters should progress from fundamentals to advanced concepts
- Topics should be specific and learnable in a single study session
- Each chapter needs a brief 1-sentence description
- Each topic title should be clear and concise (5-10 words max)
- Order chapters logically for progressive learning

Return ONLY valid JSON in this exact format:
{{
  "subject": "{subject}",
  "chapters": [
    {{
      "title": "Chapter Title",
      "description": "Brief chapter description",
      "topics": [
        "Topic 1 Title",
        "Topic 2 Title",
        "Topic 3 Title"
      ]
    }}
  ]
}}"""

        llm_response = await agent._call_llm(roadmap_prompt)

        # Parse the JSON from the LLM response
        import re
        json_match = re.search(r'\{[\s\S]*\}', llm_response)
        if not json_match:
            raise ValueError("Could not parse roadmap from LLM response")

        roadmap = json.loads(json_match.group())
        return roadmap

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Roadmap generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/exam-prep/topic-content/stream")
async def generate_topic_content_stream(request: dict):
    """Stream content generation for a specific exam prep topic (reuses research pipeline)"""
    subject = request.get("subject", "")
    chapter = request.get("chapter", "")
    topic = request.get("topic", "")

    if not topic:
        raise HTTPException(status_code=400, detail="No topic provided")

    # Build a targeted learning question
    question = f"Explain '{topic}' in the context of {chapter} ({subject}). Provide a thorough, educational explanation suitable for exam preparation."

    async def generate_stream():
        try:
            if not orchestrator:
                yield f"data: {json.dumps({'type': 'error', 'data': 'Service not initialized'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'data': f'Researching: {topic}...'})}\n\n"

            enriched_request = ResearchRequest(question=question)
            response = await orchestrator.process_question(enriched_request)

            yield f"data: {json.dumps({'type': 'status', 'data': 'Synthesizing content...'})}\n\n"
            yield f"data: {json.dumps({'type': 'topic', 'data': topic})}\n\n"
            yield f"data: {json.dumps({'type': 'tldr', 'data': response.tldr})}\n\n"
            yield f"data: {json.dumps({'type': 'explanation', 'data': response.explanation.dict()})}\n\n"

            for img in response.images:
                yield f"data: {json.dumps({'type': 'image', 'data': img.dict()})}\n\n"

            for source in response.sources:
                yield f"data: {json.dumps({'type': 'source', 'data': source.dict()})}\n\n"

            yield f"data: {json.dumps({'type': 'analogy', 'data': response.analogy})}\n\n"

            for q in response.practice_questions:
                yield f"data: {json.dumps({'type': 'practice_question', 'data': q})}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'data': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Topic content streaming error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/exam-prep/quiz")
async def generate_topic_quiz(request: dict):
    """Generate a quiz for a specific topic"""
    try:
        subject = request.get("subject", "")
        chapter = request.get("chapter", "")
        topic = request.get("topic", "")

        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided")

        logger.info(f"Generating quiz for topic: {topic}")

        if not orchestrator:
            raise HTTPException(status_code=503, detail="Service not initialized")

        quiz_prompt = f"""You are an expert exam question writer. Create a quiz for the topic: "{topic}" 
(Chapter: {chapter}, Subject: {subject}).

Generate exactly 5 multiple-choice questions that test understanding of this topic.

Rules:
- Each question should have exactly 4 options (A, B, C, D)
- Only one correct answer per question
- Include a brief explanation for the correct answer
- Questions should range from basic recall to application/analysis
- Make wrong options plausible but clearly incorrect

Return ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "question": "The question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correctIndex": 0,
      "explanation": "Brief explanation of why this is correct"
    }}
  ]
}}"""

        import re as re_mod
        llm_response = None
        last_error = None

        # Try multiple LLM providers for reliability
        llm_candidates = []

        # Priority 1: Teaching agent's LLM (Mistral/Groq/OpenAI)
        if orchestrator.teaching_agent:
            llm_candidates.append(("teaching_agent", orchestrator.teaching_agent.llm))

        # Priority 2: Groq directly
        if settings.groq_api_key:
            llm_candidates.append(("groq", ChatOpenAI(
                model=settings.groq_model,
                temperature=0.7,
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1"
            )))

        # Priority 3: Mistral directly
        if settings.mistral_api_key:
            llm_candidates.append(("mistral", ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.7,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1"
            )))

        # Priority 4: OpenAI directly
        if settings.openai_api_key:
            llm_candidates.append(("openai", ChatOpenAI(
                model=settings.primary_llm_model,
                temperature=0.7,
                api_key=settings.openai_api_key
            )))

        for provider_name, llm in llm_candidates:
            try:
                logger.info(f"Trying quiz generation with: {provider_name}")
                from langchain_core.messages import HumanMessage as HMsg
                response = await llm.ainvoke([HMsg(content=quiz_prompt)])
                llm_response = response.content
                logger.info(f"Quiz LLM response from {provider_name}: {len(llm_response)} chars")
                break
            except Exception as llm_err:
                last_error = llm_err
                logger.warning(f"Quiz generation failed with {provider_name}: {str(llm_err)}")
                continue

        if not llm_response:
            raise ValueError(f"All LLM providers failed for quiz generation. Last error: {last_error}")

        json_match = re_mod.search(r'\{[\s\S]*\}', llm_response)
        if not json_match:
            raise ValueError("Could not parse quiz from LLM response")

        quiz_data = json.loads(json_match.group())

        # Validate quiz structure
        questions = quiz_data.get("questions", [])
        if not questions:
            raise ValueError("No questions found in quiz response")

        # Add IDs to questions and validate structure
        for i, q in enumerate(questions):
            q["id"] = f"q_{i}"
            # Ensure required fields exist
            if "options" not in q or len(q.get("options", [])) < 2:
                q["options"] = ["Option A", "Option B", "Option C", "Option D"]
            if "correctIndex" not in q:
                q["correctIndex"] = 0
            if "explanation" not in q:
                q["explanation"] = "See the topic content for detailed explanation."

        return quiz_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _analyze_image_with_vlm(image_url: str, question: str = "") -> str:
    """Analyze an uploaded image with VLM (Groq, Mistral, OpenAI, or Replicate)"""

    prompt_text = f"""Describe this image in detail for educational purposes.
What do you see? Include:
- Main subject/content
- Key details, labels, or text visible
- Any diagrams, charts, or visual elements
- How this relates to: {question if question else 'the topic shown'}

Be specific and thorough."""

    errors = []

    # Priority 1: Groq vision (fast, reliable)
    if settings.groq_api_key:
        try:
            from langchain_core.messages import HumanMessage as HMsg

            llm = ChatOpenAI(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                temperature=0.3,
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                max_tokens=1024,
            )

            message = HMsg(
                content=[
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            )
            result = await llm.ainvoke([message])
            return result.content
        except Exception as e:
            errors.append(f"Groq VLM: {str(e)}")
            logger.warning(f"Groq VLM failed, falling back to next provider: {str(e)}")

    # Priority 2: Use Mistral's vision model (pixtral) via OpenAI-compatible API
    if settings.mistral_api_key:
        try:
            from langchain_core.messages import HumanMessage as HMsg

            llm = ChatOpenAI(
                model="pixtral-12b-2409",
                temperature=0.3,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
                max_tokens=1024,
            )

            message = HMsg(
                content=[
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            )
            result = await llm.ainvoke([message])
            return result.content
        except Exception as e:
            errors.append(f"Mistral VLM: {str(e)}")
            logger.warning(f"Mistral VLM failed, falling back to next provider: {str(e)}")

    # Priority 3: Use OpenAI GPT-4o-mini Vision
    if settings.openai_api_key:
        try:
            from langchain_core.messages import HumanMessage as HMsg

            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                api_key=settings.openai_api_key,
                max_tokens=1024,
            )

            message = HMsg(
                content=[
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            )
            result = await llm.ainvoke([message])
            return result.content
        except Exception as e:
            errors.append(f"OpenAI VLM: {str(e)}")
            logger.warning(f"OpenAI VLM failed: {str(e)}")

    # Priority 4: Replicate LLaVA
    if settings.replicate_api_token:
        try:
            import replicate
            output = replicate.run(
                "yorickvp/llava-13b:b5f6212d032508382d61ff00469ddda3e32fd8a0e75dc39d8a4191bb742157fb",
                input={
                    "image": image_url,
                    "prompt": prompt_text,
                    "max_tokens": 500
                }
            )
            return "".join(output)
        except Exception as e:
            errors.append(f"Replicate VLM: {str(e)}")
            logger.warning(f"Replicate VLM failed: {str(e)}")

    error_detail = "; ".join(errors) if errors else "No vision API keys configured"
    logger.error(f"All VLM providers failed: {error_detail}")
    return f"Image uploaded but vision analysis failed. Errors: {error_detail}"


# ── Personalized Learning Endpoints ──────────────────────────────

@app.post("/api/personalized/assess")
async def generate_assessment(request: dict):
    """Generate adaptive assessment questions to gauge the user's knowledge level on a topic"""
    try:
        topic = request.get("topic", "").strip()
        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided")

        logger.info(f"Generating assessment for topic: {topic}")

        if not orchestrator:
            raise HTTPException(status_code=503, detail="Service not initialized")

        agent = orchestrator.teaching_agent

        prompt = f"""You are an expert educational assessor. Create a diagnostic assessment to gauge a student's 
knowledge level on the topic: "{topic}".

Generate exactly 6 questions that progressively increase in difficulty:
- Questions 1-2: Foundational / Recall (tests basic awareness)
- Questions 3-4: Intermediate / Application (tests understanding & ability to apply)
- Questions 5-6: Advanced / Analysis (tests deep understanding & critical thinking)

Each question should have 4 options with exactly one correct answer.

Rules:
- Questions must cleanly test different depth levels of the topic
- Wrong options should be plausible but clearly distinguishable for someone who knows the material
- Include a brief tag for the cognitive level being tested
- Include which sub-area of the topic this question covers

Return ONLY valid JSON in this exact format:
{{
  "topic": "{topic}",
  "questions": [
    {{
      "id": "q_0",
      "question": "The question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correctIndex": 0,
      "difficulty": "foundational",
      "cognitiveLevel": "recall",
      "subTopic": "Brief sub-topic label"
    }}
  ]
}}"""

        llm_response = await agent._call_llm(prompt)

        import re
        json_match = re.search(r'\{[\s\S]*\}', llm_response)
        if not json_match:
            raise ValueError("Could not parse assessment from LLM response")

        raw_json = json_match.group()
        assessment = _safe_json_loads(raw_json)
        return assessment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assessment generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/personalized/analyze-profile")
async def analyze_learner_profile(request: dict):
    """Analyze assessment answers to build a detailed learner profile"""
    try:
        topic = request.get("topic", "").strip()
        questions = request.get("questions", [])
        answers = request.get("answers", [])

        if not topic or not questions or not answers:
            raise HTTPException(status_code=400, detail="Missing topic, questions, or answers")

        if not orchestrator:
            raise HTTPException(status_code=503, detail="Service not initialized")

        logger.info(f"Analyzing learner profile for: {topic}")

        # Calculate score and identify patterns
        total = len(questions)
        correct = 0
        foundational_correct = 0
        foundational_total = 0
        intermediate_correct = 0
        intermediate_total = 0
        advanced_correct = 0
        advanced_total = 0
        weak_areas = []
        strong_areas = []

        for i, q in enumerate(questions):
            user_answer = answers[i] if i < len(answers) else -1
            is_correct = user_answer == q.get("correctIndex", -1)
            difficulty = q.get("difficulty", "foundational")
            sub_topic = q.get("subTopic", "General")

            if is_correct:
                correct += 1
                strong_areas.append(sub_topic)
            else:
                weak_areas.append(sub_topic)

            if difficulty == "foundational":
                foundational_total += 1
                if is_correct:
                    foundational_correct += 1
            elif difficulty == "intermediate":
                intermediate_total += 1
                if is_correct:
                    intermediate_correct += 1
            else:
                advanced_total += 1
                if is_correct:
                    advanced_correct += 1

        score_pct = round((correct / total) * 100) if total > 0 else 0

        # Determine knowledge level
        if score_pct >= 80:
            knowledge_level = "advanced"
        elif score_pct >= 50:
            knowledge_level = "intermediate"
        else:
            knowledge_level = "beginner"

        # Determine learning style hints from patterns
        agent = orchestrator.teaching_agent

        profile_prompt = f"""Based on a student's diagnostic assessment on "{topic}":

Score: {correct}/{total} ({score_pct}%)
Foundational questions: {foundational_correct}/{foundational_total} correct
Intermediate questions: {intermediate_correct}/{intermediate_total} correct  
Advanced questions: {advanced_correct}/{advanced_total} correct

Strong areas: {', '.join(strong_areas) if strong_areas else 'None identified'}
Weak areas: {', '.join(weak_areas) if weak_areas else 'None identified'}

Create a personalized learning plan. Return ONLY valid JSON:
{{
  "knowledgeLevel": "{knowledge_level}",
  "overallScore": {score_pct},
  "strengthAreas": {json.dumps(list(set(strong_areas)))},
  "weaknessAreas": {json.dumps(list(set(weak_areas)))},
  "learningPlan": [
    {{
      "phase": 1,
      "title": "Phase title",
      "description": "What this phase covers and why",
      "topics": [
        {{
          "title": "Specific topic title",
          "reason": "Why the student needs this",
          "approach": "How we'll teach this (analogies, visuals, practice, etc.)",
          "estimatedMinutes": 10
        }}
      ],
      "technique": "The learning technique used (e.g., scaffolding, spaced repetition, elaborative interrogation)"
    }}
  ],
  "personalizedTips": [
    "Tip 1 based on their performance",
    "Tip 2 based on their weaknesses",
    "Tip 3 for effective studying"
  ],
  "recommendedStyle": "visual|textual|example-driven|practice-heavy",
  "motivationalNote": "An encouraging, personalized message about their starting point"
}}

Rules:
- Create 3-4 phases progressing from their weak areas to mastery
- Each phase should have 2-3 specific topics
- Keep topic titles SHORT (under 8 words)
- Keep all string values SHORT and simple — no special characters or backslashes
- Tailor the approach based on their knowledge level ({knowledge_level})
- For beginners: more analogies, visuals, foundational concepts
- For intermediate: bridge gaps, introduce applications, practice
- For advanced: deep dives, edge cases, synthesis exercises
- Do NOT include trailing commas in the JSON
- Do NOT use any markdown formatting inside the JSON strings
- Return ONLY the JSON object, nothing else"""

        llm_response = await agent._call_llm(profile_prompt)

        # Try up to 2 attempts
        last_error = None
        for attempt in range(2):
            try:
                llm_response = await agent._call_llm(profile_prompt)

                import re
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if not json_match:
                    raise ValueError("Could not parse profile from LLM response")

                raw_json = json_match.group()
                profile = _safe_json_loads(raw_json)
                return profile
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(f"Profile parse attempt {attempt + 1} failed: {str(e)}, retrying...")
                continue

        raise ValueError(f"Failed to parse profile after 2 attempts: {last_error}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/personalized/learn/stream")
async def personalized_learn_stream(request: dict):
    """Stream personalized learning content for a specific topic, tailored to the learner's profile"""
    topic = request.get("topic", "")
    knowledge_level = request.get("knowledgeLevel", "beginner")
    weak_areas = request.get("weakAreas", [])
    strong_areas = request.get("strongAreas", [])
    learning_style = request.get("learningStyle", "example-driven")
    approach = request.get("approach", "")
    phase_title = request.get("phaseTitle", "")
    subject = request.get("subject", "")

    if not topic:
        raise HTTPException(status_code=400, detail="No topic provided")

    # Build a highly personalized question
    style_instructions = {
        "visual": "Use lots of diagrams descriptions, charts, and visual metaphors. Structure content spatially.",
        "textual": "Use detailed written explanations with clear logical flow and precise definitions.",
        "example-driven": "Lead with concrete examples before theory. Use real-world scenarios extensively.",
        "practice-heavy": "Include many practice problems, exercises, and hands-on challenges throughout."
    }

    style_hint = style_instructions.get(learning_style, style_instructions["example-driven"])

    personalized_question = f"""Teach me about '{topic}' as part of learning {subject} (Phase: {phase_title}).

CRITICAL PERSONALIZATION CONTEXT:
- My knowledge level: {knowledge_level}
- My strong areas: {', '.join(strong_areas) if strong_areas else 'Starting fresh'}
- My weak areas that need attention: {', '.join(weak_areas) if weak_areas else 'General understanding'}
- Recommended teaching approach: {approach}
- My preferred learning style: {learning_style}

TEACHING INSTRUCTIONS:
- {style_hint}
- {"Start from absolute basics, assume no prior knowledge. Use everyday analogies." if knowledge_level == "beginner" else ""}
- {"Build on existing knowledge, focus on connections and applications." if knowledge_level == "intermediate" else ""}
- {"Go deep into nuances, edge cases, and advanced applications. Challenge my thinking." if knowledge_level == "advanced" else ""}
- Explicitly connect new concepts to my strong areas ({', '.join(strong_areas) if strong_areas else 'basics'}) to aid understanding
- Pay extra attention to my weak areas: {', '.join(weak_areas) if weak_areas else 'foundational concepts'}
- Include checkpoint questions throughout to verify understanding
- End with a "Am I ready to move on?" self-check section

Provide a comprehensive, personalized explanation."""

    async def generate_stream():
        try:
            if not orchestrator:
                yield f"data: {json.dumps({'type': 'error', 'data': 'Service not initialized'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'data': f'Personalizing content for your level: {knowledge_level}...'})}\n\n"

            enriched_request = ResearchRequest(question=personalized_question)
            response = await orchestrator.process_question(enriched_request)

            yield f"data: {json.dumps({'type': 'status', 'data': 'Tailoring explanation to your learning style...'})}\n\n"
            yield f"data: {json.dumps({'type': 'topic', 'data': topic})}\n\n"
            yield f"data: {json.dumps({'type': 'tldr', 'data': response.tldr})}\n\n"
            yield f"data: {json.dumps({'type': 'explanation', 'data': response.explanation.dict()})}\n\n"

            for img in response.images:
                yield f"data: {json.dumps({'type': 'image', 'data': img.dict()})}\n\n"

            for source in response.sources:
                yield f"data: {json.dumps({'type': 'source', 'data': source.dict()})}\n\n"

            yield f"data: {json.dumps({'type': 'analogy', 'data': response.analogy})}\n\n"

            for q in response.practice_questions:
                yield f"data: {json.dumps({'type': 'practice_question', 'data': q})}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'data': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Personalized content streaming error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ─── Video Lecture / Slide Generation ────────────────────────────

from agents.slide_generator import SlideGeneratorAgent
from agents.narration_agent import NarrationAgent

_slide_agent: SlideGeneratorAgent | None = None
_narration_agent: NarrationAgent | None = None


def _get_slide_agent() -> SlideGeneratorAgent:
    global _slide_agent
    if _slide_agent is None:
        _slide_agent = SlideGeneratorAgent()
    return _slide_agent


def _get_narration_agent() -> NarrationAgent:
    global _narration_agent
    if _narration_agent is None:
        _narration_agent = NarrationAgent()
    return _narration_agent


async def _resolve_slide_images(slides: list, topic: str):
    """Fetch a relevant image for EACH slide using its unique image_query via Tavily."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)

        # Collect per-slide queries, dedup to save API calls
        query_map: dict[str, list[int]] = {}  # query -> [slide indices]
        for i, s in enumerate(slides):
            q = (s.get("image_query") or "").strip()
            if not q:
                q = f"{topic} {s.get('title', '')}".strip()
            key = q.lower()
            if key not in query_map:
                query_map[key] = []
            query_map[key].append(i)

        # Cap at 8 unique queries to balance relevance vs API usage
        unique_queries = list(query_map.items())[:8]
        global_fallback: list[str] = []

        for query_key, slide_indices in unique_queries:
            try:
                # Use the original-case query from the first slide in the group
                first_idx = slide_indices[0]
                original_query = (slides[first_idx].get("image_query") or "").strip()
                if not original_query:
                    original_query = f"{topic} {slides[first_idx].get('title', '')}".strip()

                resp = client.search(
                    query=original_query,
                    include_images=True,
                    max_results=3,
                    search_depth="basic",
                )
                images = resp.get("images", [])
                if images:
                    # Assign each slide in this group its own image (round-robin if fewer images)
                    for j, idx in enumerate(slide_indices):
                        slides[idx]["image_url"] = images[j % len(images)]
                    global_fallback.extend(images)
                else:
                    # Mark for fallback
                    for idx in slide_indices:
                        slides[idx]["_needs_fallback"] = True
            except Exception:
                for idx in slide_indices:
                    slides[idx]["_needs_fallback"] = True
                continue

        # Fill any slides that didn't get an image with fallback images
        if global_fallback:
            for i, slide in enumerate(slides):
                if slide.pop("_needs_fallback", False) or not slide.get("image_url"):
                    slide["image_url"] = global_fallback[i % len(global_fallback)]

        resolved_count = sum(1 for s in slides if s.get("image_url"))
        logger.info(f"Resolved images for {resolved_count}/{len(slides)} slides ({len(unique_queries)} queries)")
    except Exception as e:
        logger.warning(f"Slide image resolution failed: {e}")


@app.post("/api/video-lecture/generate")
async def generate_video_lecture(request: dict):
    """
    Generate a full slide deck with narration audio for a topic.
    Body: { "topic": str, "num_slides": int (opt), "difficulty": str (opt) }
    Returns the full presentation JSON including per-slide audio.
    """
    try:
        topic = request.get("topic", "").strip()
        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided")

        num_slides = request.get("num_slides", 10)
        difficulty = request.get("difficulty", "intermediate")

        slide_agent = _get_slide_agent()
        narration_agent = _get_narration_agent()

        # 1. Generate slides
        presentation = await slide_agent.generate_slides(topic, num_slides, difficulty)

        # 1b. Resolve real image URLs for each slide
        await _resolve_slide_images(presentation["slides"], topic)

        # 2. Generate narration scripts
        narration_scripts = await slide_agent.generate_narration_script(presentation["slides"])

        # 3. Generate audio for each slide
        narrations = await narration_agent.generate_all_narrations(narration_scripts)

        # 4. Merge audio into slides
        narr_map = {n["slide_number"]: n for n in narrations}
        for slide in presentation["slides"]:
            n = narr_map.get(slide["slide_number"], {})
            slide["audio_base64"] = n.get("audio_base64", "")
            slide["use_browser_tts"] = n.get("use_browser_tts", True)
            slide["narration_text"] = n.get("text", slide.get("speaker_notes", ""))
            slide["duration_estimate"] = n.get("duration_estimate", 5)

        return presentation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video lecture generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/video-lecture/generate/stream")
async def generate_video_lecture_stream(request: dict):
    """
    Stream slide generation progress so the UI can show slides
    as they are being generated.
    """
    topic = request.get("topic", "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="No topic provided")

    num_slides = request.get("num_slides", 10)
    difficulty = request.get("difficulty", "intermediate")

    async def event_stream():
        try:
            slide_agent = _get_slide_agent()
            narration_agent = _get_narration_agent()

            yield f"data: {json.dumps({'type': 'status', 'data': 'Generating slides...'})}\n\n"

            presentation = await slide_agent.generate_slides(topic, num_slides, difficulty)

            # Resolve real image URLs
            yield f"data: {json.dumps({'type': 'status', 'data': 'Fetching images...'})}\n\n"
            await _resolve_slide_images(presentation["slides"], topic)

            yield f"data: {json.dumps({'type': 'metadata', 'data': {'title': presentation['title'], 'subtitle': presentation['subtitle'], 'total_slides': presentation['total_slides'], 'estimated_duration_minutes': presentation['estimated_duration_minutes']}})}\n\n"

            yield f"data: {json.dumps({'type': 'status', 'data': 'Generating narration...'})}\n\n"

            narration_scripts = await slide_agent.generate_narration_script(presentation["slides"])

            # Stream each slide with its audio
            for i, slide in enumerate(presentation["slides"]):
                script = narration_scripts[i] if i < len(narration_scripts) else {"narration": ""}
                audio_data = await narration_agent.generate_slide_audio(script.get("narration", ""))

                slide["audio_base64"] = audio_data.get("audio_base64", "")
                slide["use_browser_tts"] = audio_data.get("use_browser_tts", True)
                slide["narration_text"] = audio_data.get("text", slide.get("speaker_notes", ""))
                slide["duration_estimate"] = audio_data.get("duration_estimate", 5)

                yield f"data: {json.dumps({'type': 'slide', 'data': slide})}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'data': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Video lecture streaming error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/video-lecture/narrate-slide")
async def narrate_single_slide(request: dict):
    """
    Generate audio narration for a single slide on demand.
    Body: { "text": str }
    """
    try:
        text = request.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        narration_agent = _get_narration_agent()
        result = await narration_agent.generate_slide_audio(text)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single slide narration error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────── AI Doubt Solver ───────────────────────────

@app.post("/api/doubt-solver/solve")
async def doubt_solver(file: UploadFile = File(...), question: str = Form("")):
    """
    Upload an image of a textbook page, handwritten notes, or problem set.
    The AI OCRs it and explains / solves / generates practice from it.
    """
    try:
        logger.info(f"Doubt solver upload: {file.filename}")
        content = await file.read()

        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")

        b64_data = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{file.content_type};base64,{b64_data}"

        # Step 1 – VLM extracts text / diagram description
        ocr_description = await _analyze_image_with_vlm(
            data_url,
            question or "Extract all text, equations, diagrams, and problems visible in this image. Be very thorough."
        )

        # Step 2 – LLM explains / solves
        from langchain_core.messages import SystemMessage, HumanMessage as HMsg

        llm = _get_code_ai_llm()

        system = SystemMessage(content="""You are Lumina Doubt Solver — an expert tutor for students.
You receive OCR-extracted content from a student's uploaded image (textbook page, notes, problem set, etc.) plus an optional question.

Your job:
1. **Identify** what the student is looking at (subject, topic, type of content).
2. **Explain** the core concepts shown clearly and simply.
3. **Solve** any problems/equations step-by-step with clear reasoning.
4. **Practice** — generate 2-3 similar practice problems with answers.

Rules:
- Use LaTeX for math: inline $...$ and display $$...$$
- Use markdown formatting with headers, bullet points, bold, etc.
- Be encouraging and supportive like a great teacher.
- If the image contains multiple problems, address each one.
- If unsure about OCR accuracy, note assumptions.
""")

        user_msg = f"""## Extracted content from student's uploaded image:

{ocr_description}

## Student's question:
{question if question else "Please explain this and solve any problems shown."}"""

        result = await llm.ainvoke([system, HMsg(content=user_msg)])

        return {
            "filename": file.filename,
            "preview_url": "",
            "ocr_text": ocr_description,
            "solution": result.content,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Doubt solver error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/doubt-solver/chat")
async def doubt_solver_chat(request: dict):
    """
    Chat-based doubt solver with conversation memory.
    Supports follow-up questions and optional image uploads.
    Body: { "message": str, "conversation_history": [{"role":str,"content":str}], "image_base64"?: str, "image_type"?: str }
    """
    try:
        message = request.get("message", "").strip()
        history = request.get("conversation_history", [])
        image_b64 = request.get("image_base64", "")
        image_type = request.get("image_type", "image/png")

        if not message and not image_b64:
            raise HTTPException(status_code=400, detail="No message or image provided")

        from langchain_core.messages import SystemMessage, HumanMessage as HMsg

        llm = _get_code_ai_llm()

        # If image is provided, run VLM first
        image_context = ""
        if image_b64:
            data_url = f"data:{image_type};base64,{image_b64}"
            image_context = await _analyze_image_with_vlm(
                data_url,
                message or "Extract all text, equations, diagrams, and problems visible in this image. Be very thorough."
            )

        system = SystemMessage(content="""You are Lumina Doubt Solver — an expert tutor who helps students understand concepts and solve problems through conversation.

Your capabilities:
1. **Explain** concepts clearly with examples and analogies.
2. **Solve** problems step-by-step with clear reasoning.
3. **Follow up** on previous discussion with deeper insights.
4. **Practice** — suggest practice problems when appropriate.

Rules:
- Use LaTeX for math: inline $...$ and display $$...$$ 
- Use markdown formatting with headers, bullet points, bold, etc.
- Be encouraging and supportive like a great teacher.
- Reference previous conversation context when answering follow-ups.
- If an image was analyzed, incorporate that context into your response.
- Keep responses focused and well-structured.
""")

        # Build messages from history
        chat_messages = [system]
        for msg in history[-20:]:  # Keep last 20 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant":
                from langchain_core.messages import AIMessage
                chat_messages.append(AIMessage(content=content))
            else:
                chat_messages.append(HMsg(content=content))

        # Build current user message
        user_msg_parts = []
        if image_context:
            user_msg_parts.append(f"[Image content extracted via OCR/VLM]:\n{image_context}")
        if message:
            user_msg_parts.append(message)

        chat_messages.append(HMsg(content="\n\n".join(user_msg_parts) if user_msg_parts else "Please help me understand this."))

        result = await llm.ainvoke(chat_messages)

        return {
            "response": result.content,
            "image_context": image_context if image_context else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Doubt solver chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────── Guide Chatbot ─────────────────────────────

@app.post("/api/guide/chat")
async def guide_chat(request: dict):
    """
    Context-aware guide chatbot for Exam Prep, Personalized Learning, and Video Lectures.
    Body: { "message": str, "mode": str, "context": str, "conversation_history": [{"role":str,"content":str}] }
    """
    try:
        message = request.get("message", "").strip()
        mode = request.get("mode", "general")
        context = request.get("context", "")
        history = request.get("conversation_history", [])

        if not message:
            raise HTTPException(status_code=400, detail="No message provided")

        from langchain_core.messages import SystemMessage, HumanMessage as HMsg, AIMessage

        llm = _get_code_ai_llm()

        mode_prompts = {
            "exam-prep": """You are Lumina Study Guide — an AI tutor embedded in the Exam Prep section.
The student is studying for exams and has a roadmap of topics. Help them:
- Understand difficult concepts from their study topics
- Explain formulas, theorems, and definitions
- Create quick practice questions on the fly
- Suggest study strategies and memory techniques
- Answer any questions about the subjects they're studying""",

            "personalized": """You are Lumina Learning Guide — an AI tutor embedded in the Personalized Learning section.
The student has a personalized learning plan. Help them:
- Dive deeper into topics from their learning plan
- Explain concepts at their skill level
- Suggest additional resources and exercises
- Help them overcome specific learning challenges
- Track and discuss their learning progress""",

            "video-lecture": """You are Lumina Lecture Assistant — an AI tutor embedded in the Video Lecture section.
The student is watching AI-generated video lectures. Help them:
- Clarify concepts presented in the slides
- Answer questions about the lecture content
- Provide additional examples and explanations
- Help them take effective notes
- Connect lecture content to broader topics""",
        }

        system_prompt = mode_prompts.get(mode, """You are Lumina Guide — a helpful AI learning assistant.
Help the student with any questions about their studies.""")

        if context:
            system_prompt += f"\n\nCurrent context the student is working with:\n{context}"

        system_prompt += """

Rules:
- Use LaTeX for math: inline $...$ and display $$...$$
- Use markdown formatting for structure
- Be concise but thorough — respect the student's time
- Be encouraging and supportive
- Reference previous conversation when relevant
"""

        system = SystemMessage(content=system_prompt)

        chat_messages = [system]
        for msg in history[-15:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant":
                chat_messages.append(AIMessage(content=content))
            else:
                chat_messages.append(HMsg(content=content))

        chat_messages.append(HMsg(content=message))

        result = await llm.ainvoke(chat_messages)

        return {"response": result.content}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Guide chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────── Flashcard Generation ──────────────────────────

@app.post("/api/flashcards/generate")
async def generate_flashcards(request: dict):
    """
    Generate flashcards from a topic or pasted content.
    Body: { "topic": str, "content"?: str, "count"?: int }
    Returns: { cards: [{ front, back, difficulty }] }
    """
    try:
        topic = request.get("topic", "").strip()
        content = request.get("content", "").strip()
        count = min(request.get("count", 10), 20)

        if not topic and not content:
            raise HTTPException(status_code=400, detail="Provide a topic or content")

        from langchain_core.messages import SystemMessage, HumanMessage as HMsg
        llm = _get_code_ai_llm()

        system = SystemMessage(content=f"""You are a flashcard generator for spaced-repetition learning.
Generate exactly {count} flashcards as a JSON array.

Each flashcard must have:
- "front": The question/prompt (concise, clear)
- "back": The answer/explanation (thorough but focused)
- "difficulty": 1-5 (1=easy recall, 5=very hard)

Rules:
- Cover the most important concepts first.
- Mix question types: definitions, fill-in-blank, true/false, short-answer, application.
- Use LaTeX ($...$) for math/science formulas.
- Return ONLY a valid JSON array, no other text.
""")

        user_content = f"Topic: {topic}" if topic else ""
        if content:
            user_content += f"\n\nSource content to create flashcards from:\n{content[:5000]}"

        result = await llm.ainvoke([system, HMsg(content=user_content)])
        raw = result.content.strip()

        # Strip markdown code blocks if present (```json ... ``` or ``` ... ```)
        if raw.startswith("```"):
            # Remove opening ``` (optionally with language tag) and closing ```
            raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
            raw = re.sub(r'\n?```\s*$', '', raw)
            raw = raw.strip()

        # Parse JSON — the LLM might return a bare array [...] or an object {"cards": [...]}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: try the safe parser
            parsed = _safe_json_loads(raw)

        if isinstance(parsed, list):
            cards = parsed
        elif isinstance(parsed, dict):
            cards = parsed.get("cards", parsed.get("flashcards", []))
            if not isinstance(cards, list):
                cards = []
        else:
            cards = []

        return {"cards": cards, "topic": topic}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Flashcard generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────── Code Playground ───────────────────────────────

@app.post("/api/code-playground/run")
async def run_code_playground(request: dict):
    """
    Execute code in a sandboxed environment (Python only for safety).
    Body: { "code": str, "language": str, "stdin"?: str }
    Returns: { stdout, stderr, exitCode, executionTime }
    """
    import subprocess
    import tempfile
    import time

    try:
        code = request.get("code", "").strip()
        language = request.get("language", "python").lower()
        stdin_data = request.get("stdin", "")

        if not code:
            raise HTTPException(status_code=400, detail="No code provided")

        if language not in ("python", "javascript", "js"):
            raise HTTPException(status_code=400, detail=f"Language '{language}' execution not supported. Use 'python' or 'javascript'.")

        start_time = time.time()

        if language == "python":
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                f.flush()
                try:
                    proc = subprocess.run(
                        [sys.executable, f.name],
                        capture_output=True, text=True,
                        timeout=10, input=stdin_data,
                    )
                    elapsed = round((time.time() - start_time) * 1000)
                    return {
                        "stdout": proc.stdout[-5000:] if len(proc.stdout) > 5000 else proc.stdout,
                        "stderr": proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr,
                        "exitCode": proc.returncode,
                        "executionTime": elapsed,
                    }
                finally:
                    import os
                    os.unlink(f.name)

        elif language in ("javascript", "js"):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                f.flush()
                try:
                    proc = subprocess.run(
                        ["node", f.name],
                        capture_output=True, text=True,
                        timeout=10, input=stdin_data,
                    )
                    elapsed = round((time.time() - start_time) * 1000)
                    return {
                        "stdout": proc.stdout[-5000:] if len(proc.stdout) > 5000 else proc.stdout,
                        "stderr": proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr,
                        "exitCode": proc.returncode,
                        "executionTime": elapsed,
                    }
                finally:
                    import os
                    os.unlink(f.name)

    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Execution timed out (10s limit)", "exitCode": 1, "executionTime": 10000}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Runtime for '{language}' not found on server")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code-playground/explain")
async def explain_code(request: dict):
    """
    AI explains code step-by-step, debugs errors, or generates exercises.
    Body: { "code": str, "language": str, "action": "explain"|"debug"|"exercise"|"optimize", "error"?: str }
    """
    try:
        code = request.get("code", "").strip()
        language = request.get("language", "python")
        action = request.get("action", "explain")
        error = request.get("error", "")

        if not code:
            raise HTTPException(status_code=400, detail="No code provided")

        from langchain_core.messages import SystemMessage, HumanMessage as HMsg
        llm = _get_code_ai_llm()

        prompts = {
            "explain": f"""You are a coding tutor. Explain the following {language} code step-by-step.
- Walk through each line/block and explain what it does.
- Highlight key concepts, patterns, and potential gotchas.
- Rate the code complexity (beginner/intermediate/advanced).
- Use markdown with syntax-highlighted code blocks.""",
            "debug": f"""You are a debugging expert. The student's {language} code has an error.
- Identify the bug(s) and explain why they occur.
- Show the corrected code with explanations.
- Suggest how to avoid similar bugs in the future.
Error message: {error}""",
            "exercise": f"""You are a coding exercise generator. Based on this {language} code, create:
1. Three practice exercises of increasing difficulty (easy, medium, hard).
2. Each with: title, description, starter code, expected output, hints.
3. Return as structured markdown with clear sections.""",
            "optimize": f"""You are a code optimization expert. Review this {language} code and:
1. Identify performance issues or anti-patterns.
2. Show the optimized version with explanations.
3. Compare time/space complexity before and after.
4. Suggest best practices.""",
        }

        system = SystemMessage(content=prompts.get(action, prompts["explain"]))
        user_msg = f"```{language}\n{code}\n```"

        result = await llm.ainvoke([system, HMsg(content=user_msg)])
        return {"result": result.content, "action": action}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code explain error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
