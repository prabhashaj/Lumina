"""
FastAPI main application
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import json
import io
import base64
from loguru import logger
from langchain_openai import ChatOpenAI

from config.settings import settings
from graph.orchestrator import ResearchOrchestrator
from shared.schemas.models import ResearchRequest, TeachingResponse
from tools.cost_tracking import start_tracking, summarize_cost, record_tavily_search

try:
    from utils.json_parsing import parse_llm_json
except Exception:
    parse_llm_json = None


def _safe_json_loads(raw: str) -> dict:
    """Parse JSON from LLM output, handling various malformed JSON issues."""
    if parse_llm_json is not None:
        return parse_llm_json(raw)

    return json.loads(raw)


def _model_to_dict(obj):
    """Serialize Pydantic v2/v1 models safely without deprecation warnings."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def _attach_cost(payload: dict) -> dict:
    payload["cost"] = summarize_cost()
    return payload


# Processing time tracking
import time as _time
_request_start_time = None

def _start_timing():
    """Start timing a request"""
    global _request_start_time
    _request_start_time = _time.time()

def _get_processing_time() -> float:
    """Get elapsed time in seconds since start_timing() was called"""
    global _request_start_time
    if _request_start_time is None:
        return 0.0
    return round(_time.time() - _request_start_time, 3)


# Session-scoped conversational memory (fallback when client sends partial/no history)
_SESSION_MEMORY_TTL_SECONDS = 6 * 60 * 60
_SESSION_MEMORY_MAX_MESSAGES = 40
_session_memory_store = {}


def _session_memory_key(mode: str, session_id: str, user_id: str = "") -> str:
    safe_mode = (mode or "general").strip().lower()
    safe_session = (session_id or "").strip()
    safe_user = (user_id or "").strip()
    return f"{safe_mode}:{safe_user}:{safe_session}"


def _normalize_history_items(history, max_messages: int = 20):
    cleaned = []
    if not isinstance(history, list):
        return cleaned

    for item in history:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user")).strip().lower()
        if role not in {"user", "assistant", "system"}:
            role = "user"
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        cleaned.append({"role": role, "content": content})

    return cleaned[-max_messages:]


def _prune_session_memory() -> None:
    now = _time.time()
    stale_keys = []
    for key, entry in _session_memory_store.items():
        if now - entry.get("updated_at", 0) > _SESSION_MEMORY_TTL_SECONDS:
            stale_keys.append(key)
    for key in stale_keys:
        _session_memory_store.pop(key, None)


def _get_session_history(mode: str, session_id: str, user_id: str = ""):
    if not session_id:
        return []
    _prune_session_memory()
    key = _session_memory_key(mode, session_id, user_id)
    entry = _session_memory_store.get(key)
    if not entry:
        return []
    return list(entry.get("history", []))


def _save_session_history(mode: str, session_id: str, history, user_id: str = "") -> None:
    if not session_id:
        return
    key = _session_memory_key(mode, session_id, user_id)
    normalized = _normalize_history_items(history, max_messages=_SESSION_MEMORY_MAX_MESSAGES)
    _session_memory_store[key] = {
        "history": normalized,
        "updated_at": _time.time(),
    }


def _resolve_effective_history(mode: str, incoming_history, session_id: str = "", user_id: str = ""):
    normalized_incoming = _normalize_history_items(incoming_history, max_messages=_SESSION_MEMORY_MAX_MESSAGES)
    if normalized_incoming:
        _save_session_history(mode, session_id, normalized_incoming, user_id)
        return normalized_incoming
    return _get_session_history(mode, session_id, user_id)


def _append_session_turn(
    mode: str,
    session_id: str,
    user_text: str,
    assistant_text: str,
    user_id: str = "",
    base_history=None,
) -> None:
    if not session_id:
        return

    history = _normalize_history_items(base_history or _get_session_history(mode, session_id, user_id), max_messages=_SESSION_MEMORY_MAX_MESSAGES)

    user_msg = (user_text or "").strip()
    assistant_msg = (assistant_text or "").strip()

    if user_msg:
        history.append({"role": "user", "content": user_msg})
    if assistant_msg:
        history.append({"role": "assistant", "content": assistant_msg})

    _save_session_history(mode, session_id, history, user_id)


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


def _ensure_orchestrator() -> ResearchOrchestrator:
    """Return a ready orchestrator, lazily initializing when needed."""
    global orchestrator
    if orchestrator is None:
        logger.warning("Orchestrator was None at request time; attempting lazy initialization")
        orchestrator = ResearchOrchestrator()
    return orchestrator


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

# Custom CORS middleware that explicitly handles OPTIONS preflight
class CORSHandler(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400",
                },
            )
        
        # Process the actual request
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

app.add_middleware(CORSHandler)


@app.get("/")
async def root():
    """Health check endpoint"""
    _start_timing()
    start_tracking()
    return _attach_cost({
        "status": "healthy",
        "service": "AI Research Teaching Agent",
        "version": "1.0.0",
        "processing_time": _get_processing_time()
    })


@app.get("/health")
async def health_check():
    """Detailed health check"""
    _start_timing()
    start_tracking()
    return _attach_cost({
        "status": "healthy",
        "orchestrator": orchestrator is not None,
        "settings": {
            "llm_model": settings.mistral_model,
            "max_search_results": settings.max_search_results,
            "max_images": settings.max_images_per_response
        },
        "processing_time": _get_processing_time()
    })


# ─── Code AI Tutor ───────────────────────────────────────────────

_code_ai_llm = None

def _get_code_ai_llm():
    """Lazy-init an LLM for the code tutor using Mistral."""
    global _code_ai_llm
    if _code_ai_llm is None:
        if settings.mistral_api_key:
            _code_ai_llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.7,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
                max_tokens=4000
            )
        else:
            raise ValueError("No valid API key found. Please set MISTRAL_API_KEY")
    return _code_ai_llm


# ─── Doubt Solver (Mistral API) ──────────────────────────────────────────────

_doubt_solver_llm = None
_doubt_solver_backup_llm = None


def _is_credit_or_payment_error(error_text: str) -> bool:
    lowered = error_text.lower()
    return "402" in error_text or "credits" in lowered or "payment" in lowered


def _extract_affordable_tokens(error_text: str):
    import re as _re

    match = _re.search(r"can only afford\s+(\d+)", error_text, _re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


async def _invoke_doubt_solver_llm(messages):
    llm = _get_doubt_solver_llm()
    try:
        return await llm.ainvoke(messages)
    except Exception as e:
        error_str = str(e)
        if _is_credit_or_payment_error(error_str):
            affordable = _extract_affordable_tokens(error_str)
            if affordable and affordable >= 256:
                retry_max_tokens = max(256, min(3000, affordable - 64))
                logger.warning(
                    f"Doubt Solver token cap reached; retrying with max_tokens={retry_max_tokens}"
                )
                return await llm.bind(max_tokens=retry_max_tokens).ainvoke(messages)

            if _doubt_solver_backup_llm is not None:
                logger.warning("Doubt Solver primary call failed; falling back to backup Mistral call")
                return await _doubt_solver_backup_llm.ainvoke(messages)
        raise

def _get_doubt_solver_llm():
    """
    Get LLM for doubt solver using Mistral.
    """
    global _doubt_solver_llm, _doubt_solver_backup_llm
    if _doubt_solver_llm is None:
        if settings.mistral_api_key:
            logger.info("Initializing Doubt Solver with Mistral API")
            _doubt_solver_llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.7,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
                max_tokens=3000
            )
        else:
            raise ValueError("No valid API key found. Please set MISTRAL_API_KEY")
    return _doubt_solver_llm


@app.post("/api/code-ai/chat")
async def code_ai_chat(request: dict):
    """
    AI coding tutor chat endpoint.
    Accepts: message, systemPrompt, code, language, questionTitle,
             questionDescription, output, error, history
    Returns: { response: str }
    """
    try:
        _start_timing()
        start_tracking()
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
        return _attach_cost({"response": result.content, "processing_time": _get_processing_time()})

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
        _start_timing()
        start_tracking()
        
        # Validate question length
        question = request.question.strip()
        if len(question) < 3:
            raise HTTPException(status_code=400, detail="Question must be at least 3 characters long")
        if len(question) > 2000:
            raise HTTPException(status_code=400, detail="Question must not exceed 2000 characters")
        
        logger.info(f"Received research request: {request.question[:100]}...")
        
        try:
            ready_orchestrator = _ensure_orchestrator()
        except Exception as init_error:
            raise HTTPException(status_code=503, detail=f"Service not initialized: {init_error}")
        
        effective_history = _resolve_effective_history(
            mode="research",
            incoming_history=request.conversation_history,
            session_id=request.session_id or "",
            user_id=request.user_id or "",
        )
        effective_request = request.model_copy(update={"conversation_history": effective_history})

        # Process through the orchestrator
        response = await ready_orchestrator.process_question(effective_request)

        _append_session_turn(
            mode="research",
            session_id=request.session_id or "",
            user_id=request.user_id or "",
            user_text=request.question,
            assistant_text=(response.tldr or response.explanation.content[:300]),
            base_history=effective_history,
        )
        
        # Add processing time
        response.processing_time = _get_processing_time()
        response.cost = summarize_cost()
        return response
        
    except HTTPException:
        raise
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
            _start_timing()
            start_tracking()
            logger.info(f"Starting streaming research: {request.question[:100]}...")

            try:
                ready_orchestrator = _ensure_orchestrator()
            except Exception as init_error:
                yield f"data: {json.dumps({'type': 'error', 'data': f'Service not initialized: {init_error}'})}\n\n"
                return
            
            # Send status update: Starting
            yield f"data: {json.dumps({'type': 'status', 'data': 'Analyzing question...'})}\n\n"
            
            # Build enriched question with any attached context
            enriched_question = request.question
            if request.image_context:
                enriched_question += f"\n\n[User attached an image with the following content: {request.image_context}]"
            if request.file_context:
                enriched_question += f"\n\n[User attached a document with the following content:\n{request.file_context[:5000]}]"
            
            effective_history = _resolve_effective_history(
                mode="research",
                incoming_history=request.conversation_history,
                session_id=request.session_id or "",
                user_id=request.user_id or "",
            )

            # Create enriched request
            enriched_request = ResearchRequest(
                question=enriched_question,
                conversation_history=effective_history,
                user_id=request.user_id,
                session_id=request.session_id
            )

            progress_queue: asyncio.Queue = asyncio.Queue()

            def _on_progress(message: str) -> None:
                try:
                    progress_queue.put_nowait(message)
                except Exception:
                    pass

            # Run full workflow while streaming internal step updates
            workflow_task = asyncio.create_task(
                ready_orchestrator.process_question(
                    enriched_request,
                    progress_callback=_on_progress,
                )
            )

            last_stage = "Searching the web..."
            idle_ticks = 0

            while not workflow_task.done():
                try:
                    stage = await asyncio.wait_for(progress_queue.get(), timeout=2.0)
                    stage = (stage or "").strip()
                    if stage:
                        last_stage = stage
                        idle_ticks = 0
                        logger.info(f"STREAM stage: {stage}")
                        yield f"data: {json.dumps({'type': 'status', 'data': stage})}\n\n"
                except asyncio.TimeoutError:
                    idle_ticks += 1
                    # Keep the client informed during slow network/model calls.
                    if idle_ticks % 4 == 0:
                        heartbeat = f"Still working: {last_stage}"
                        logger.info(f"STREAM heartbeat: {heartbeat}")
                        yield f"data: {json.dumps({'type': 'status', 'data': heartbeat})}\n\n"

            response = await workflow_task

            _append_session_turn(
                mode="research",
                session_id=request.session_id or "",
                user_id=request.user_id or "",
                user_text=request.question,
                assistant_text=(response.tldr or response.explanation.content[:300]),
                base_history=effective_history,
            )

            while not progress_queue.empty():
                stage = (progress_queue.get_nowait() or "").strip()
                if stage:
                    logger.info(f"STREAM stage: {stage}")
                    yield f"data: {json.dumps({'type': 'status', 'data': stage})}\n\n"
            
            # Stream the complete response
            yield f"data: {json.dumps({'type': 'status', 'data': 'Synthesizing teaching content...'})}\n\n"
            
            # Send TL;DR first
            yield f"data: {json.dumps({'type': 'topic', 'data': response.question})}\n\n"
            yield f"data: {json.dumps({'type': 'tldr', 'data': response.tldr})}\n\n"
            
            # Send explanation
            yield f"data: {json.dumps({'type': 'explanation', 'data': _model_to_dict(response.explanation)})}\n\n"
            
            # Send images
            for img in response.images:
                yield f"data: {json.dumps({'type': 'image', 'data': _model_to_dict(img)})}\n\n"
            
            # Send sources
            for source in response.sources:
                yield f"data: {json.dumps({'type': 'source', 'data': _model_to_dict(source)})}\n\n"
            
            # Send analogy
            yield f"data: {json.dumps({'type': 'analogy', 'data': response.analogy})}\n\n"
            
            # Send practice questions
            logger.info(f"Streaming {len(response.practice_questions)} practice questions")
            for idx, q in enumerate(response.practice_questions, 1):
                logger.info(f"  Streaming Q{idx}: {q[:80]}")
                yield f"data: {json.dumps({'type': 'practice_question', 'data': q})}\n\n"

            # Send PeCAR metrics if available
            if response.pecar_metrics:
                yield f"data: {json.dumps({'type': 'pecar_metrics', 'data': response.pecar_metrics})}\n\n"

            # Add processing time
            response.processing_time = _get_processing_time()
            response.cost = summarize_cost()

            # Send complete signal with full response
            yield f"data: {json.dumps({'type': 'complete', 'data': _model_to_dict(response)})}\n\n"
            
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
    _start_timing()
    start_tracking()
    return _attach_cost({
        "max_search_results": settings.max_search_results,
        "max_images_per_response": settings.max_images_per_response,
        "cache_ttl": settings.cache_ttl,
        "supported_models": {
            "llm_primary": settings.mistral_model,
            "llm_backup": None,
            "embedding": settings.embedding_model
        },
        "features": {
            "tts_enabled": bool(settings.elevenlabs_api_key),
            "file_upload": True
        },
        "processing_time": _get_processing_time()
    })


@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...), question: str = Form("")):
    """Upload an image and return preview URL (VLM analysis removed)"""
    try:
        _start_timing()
        start_tracking()
        logger.info(f"Received image upload: {file.filename}, size: {file.size}")
        
        # Read file content
        content = await file.read()
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")
        
        # Convert to base64 data URL
        b64_data = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{file.content_type};base64,{b64_data}"
        
        return _attach_cost({
            "filename": file.filename,
            "content_type": file.content_type,
            "analysis": "Image uploaded successfully. Describe the image in your question for best results.",
            "preview_url": data_url,
            "processing_time": _get_processing_time()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/file")
async def upload_and_extract_file(file: UploadFile = File(...)):
    """Upload a document (PDF, DOCX, TXT) and extract its text content"""
    try:
        _start_timing()
        start_tracking()
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
        
        return _attach_cost({
            "filename": file.filename,
            "content_type": file.content_type,
            "extracted_text": extracted_text,
            "char_count": len(extracted_text),
            "processing_time": _get_processing_time()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts")
async def text_to_speech(request: dict):
    """Convert text to speech using ElevenLabs API"""
    try:
        _start_timing()
        start_tracking()
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        # Truncate very long text to avoid API limits
        if len(text) > 5000:
            text = text[:5000]
        
        if not settings.elevenlabs_api_key:
            # Fallback: Use browser TTS (return empty with flag)
            return _attach_cost({
                "audio": "",
                "use_browser_tts": True,
                "processing_time": _get_processing_time()
            })
        
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
        _start_timing()
        start_tracking()
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

        roadmap = _safe_json_loads(json_match.group())
        roadmap["processing_time"] = _get_processing_time()
        return _attach_cost(roadmap)

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
            _start_timing()
            start_tracking()
            if not orchestrator:
                yield f"data: {json.dumps({'type': 'error', 'data': 'Service not initialized'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'data': f'Researching: {topic}...'})}\n\n"

            enriched_request = ResearchRequest(question=question)
            response = await orchestrator.process_question(enriched_request)

            yield f"data: {json.dumps({'type': 'status', 'data': 'Synthesizing content...'})}\n\n"
            yield f"data: {json.dumps({'type': 'topic', 'data': topic})}\n\n"
            yield f"data: {json.dumps({'type': 'tldr', 'data': response.tldr})}\n\n"
            yield f"data: {json.dumps({'type': 'explanation', 'data': _model_to_dict(response.explanation)})}\n\n"

            for img in response.images:
                yield f"data: {json.dumps({'type': 'image', 'data': _model_to_dict(img)})}\n\n"

            for source in response.sources:
                yield f"data: {json.dumps({'type': 'source', 'data': _model_to_dict(source)})}\n\n"

            yield f"data: {json.dumps({'type': 'analogy', 'data': response.analogy})}\n\n"

            for q in response.practice_questions:
                yield f"data: {json.dumps({'type': 'practice_question', 'data': q})}\n\n"

            response_dict = _model_to_dict(response)
            response_dict["processing_time"] = _get_processing_time()
            response_dict["cost"] = summarize_cost()
            
            yield f"data: {json.dumps({'type': 'cost', 'data': response_dict['cost']})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'data': response_dict})}\n\n"

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
        _start_timing()
        start_tracking()
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

        # Priority 1: Teaching agent's LLM
        if orchestrator.teaching_agent:
            llm_candidates.append(("teaching_agent", orchestrator.teaching_agent.llm))

        # Priority 2: Mistral API
        if settings.mistral_api_key:
            llm_candidates.append(("mistral", ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.7,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
                max_tokens=4000
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

        quiz_data = _safe_json_loads(json_match.group())

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

        quiz_data["processing_time"] = _get_processing_time()
        return _attach_cost(quiz_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# VLM functionality removed - not needed for educational content generation
# Tavily search provides contextually relevant images already


# ── Personalized Learning Endpoints ──────────────────────────────

@app.post("/api/personalized/assess")
async def generate_assessment(request: dict):
    """Generate adaptive assessment questions to gauge the user's knowledge level on a topic"""
    try:
        _start_timing()
        start_tracking()
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
        assessment["processing_time"] = _get_processing_time()
        return _attach_cost(assessment)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assessment generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/personalized/analyze-profile")
async def analyze_learner_profile(request: dict):
    """Analyze assessment answers to build a detailed learner profile"""
    try:
        _start_timing()
        start_tracking()
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
                profile["processing_time"] = _get_processing_time()
                return _attach_cost(profile)
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
            _start_timing()
            start_tracking()
            if not orchestrator:
                yield f"data: {json.dumps({'type': 'error', 'data': 'Service not initialized'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'data': f'Personalizing content for your level: {knowledge_level}...'})}\n\n"

            enriched_request = ResearchRequest(question=personalized_question)
            response = await orchestrator.process_question(enriched_request)

            yield f"data: {json.dumps({'type': 'status', 'data': 'Tailoring explanation to your learning style...'})}\n\n"
            yield f"data: {json.dumps({'type': 'topic', 'data': topic})}\n\n"
            yield f"data: {json.dumps({'type': 'tldr', 'data': response.tldr})}\n\n"
            yield f"data: {json.dumps({'type': 'explanation', 'data': _model_to_dict(response.explanation)})}\n\n"

            for img in response.images:
                yield f"data: {json.dumps({'type': 'image', 'data': _model_to_dict(img)})}\n\n"

            for source in response.sources:
                yield f"data: {json.dumps({'type': 'source', 'data': _model_to_dict(source)})}\n\n"

            yield f"data: {json.dumps({'type': 'analogy', 'data': response.analogy})}\n\n"

            for q in response.practice_questions:
                yield f"data: {json.dumps({'type': 'practice_question', 'data': q})}\n\n"

            response_dict = _model_to_dict(response)
            response_dict["processing_time"] = _get_processing_time()
            response_dict["cost"] = summarize_cost()
            
            yield f"data: {json.dumps({'type': 'cost', 'data': response_dict['cost']})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'data': response_dict})}\n\n"

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

                record_tavily_search("basic", 1)
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
        _start_timing()
        start_tracking()
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

        presentation["cost"] = summarize_cost()
        presentation["processing_time"] = _get_processing_time()
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
            _start_timing()
            start_tracking()
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

            presentation["processing_time"] = _get_processing_time()
            presentation["cost"] = summarize_cost()
            
            yield f"data: {json.dumps({'type': 'cost', 'data': presentation['cost']})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'data': presentation})}\n\n"

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
        _start_timing()
        start_tracking()
        text = request.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        narration_agent = _get_narration_agent()
        result = await narration_agent.generate_slide_audio(text)
        result["processing_time"] = _get_processing_time()
        return _attach_cost(result)

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
        _start_timing()
        start_tracking()
        logger.info(f"Doubt solver upload: {file.filename}")
        content = await file.read()

        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")

        b64_data = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{file.content_type};base64,{b64_data}"

        # Image analysis disabled - user should describe the image in their question
        ocr_description = "[Image uploaded - please describe what you see in your question for best help]"

        # Step 2 – LLM explains / solves
        from langchain_core.messages import SystemMessage, HumanMessage as HMsg

        system = SystemMessage(content="""You are Lumina Doubt Solver — a brilliant, patient tutor who makes complex concepts click.
You receive OCR-extracted content from a student's uploaded image (textbook page, notes, problem set, etc.) plus an optional question.

Your teaching approach:
1. **Identify** what the student is looking at (subject, topic, type of content) and acknowledge it.
2. **Explain** the core concepts with clarity — use analogies, build from simple to complex, and always explain the "why" behind each step.
3. **Solve** any problems/equations step-by-step with detailed reasoning. Don't skip steps. Show your thought process so the student learns HOW to think, not just the answer.
4. **Highlight** common mistakes students make on this type of problem and how to avoid them.
5. **Practice** — generate 2-3 similar practice problems with hints (and answers at the end).

Teaching rules:
- Use LaTeX for all math: inline $...$ and display $$...$$
- Structure with clear markdown headers, bullet points, numbered steps, and bold key terms.
- Be warm, encouraging, and conversational — like the best tutor the student has ever had.
- Explain each step as if the student is seeing this type of problem for the first time.
- If the image contains multiple problems, address each one thoroughly.
- If unsure about OCR accuracy, note your assumptions clearly.
- End with a brief "Key Insight" that summarizes the most important takeaway.
""")

        user_msg = f"""## Extracted content from student's uploaded image:

{ocr_description}

## Student's question:
{question if question else "Please explain this and solve any problems shown."}"""

        result = await _invoke_doubt_solver_llm([system, HMsg(content=user_msg)])

        return _attach_cost({
            "filename": file.filename,
            "preview_url": "",
            "ocr_text": ocr_description,
            "solution": result.content,
            "processing_time": _get_processing_time()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Doubt solver error: {str(e)}")
        if _is_credit_or_payment_error(str(e)):
            raise HTTPException(
                status_code=402,
                detail="Insufficient Mistral API credits/quota for this request. Please reduce response length or increase your Mistral quota."
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/doubt-solver/chat")
async def doubt_solver_chat(request: dict):
    """
    Chat-based doubt solver with conversation memory.
    Supports follow-up questions and optional image uploads.
    Body: { "message": str, "conversation_history": [{"role":str,"content":str}], "image_base64"?: str, "image_type"?: str }
    """
    try:
        _start_timing()
        start_tracking()
        message = request.get("message", "").strip()
        history = request.get("conversation_history", [])
        session_id = str(request.get("session_id", "") or "")
        user_id = str(request.get("user_id", "") or "")
        image_b64 = request.get("image_base64", "")
        image_type = request.get("image_type", "image/png")

        if not message and not image_b64:
            raise HTTPException(status_code=400, detail="No message or image provided")

        from langchain_core.messages import SystemMessage, HumanMessage as HMsg

        # Image analysis disabled - user should describe the image
        image_context = ""
        if image_b64:
            image_context = "[Image uploaded - please describe what you see for best assistance]"

        system = SystemMessage(content="""You are Lumina Doubt Solver — a brilliant, patient tutor who helps students truly understand concepts through conversation.

Your teaching philosophy: Don't just give answers — build understanding. Every response should leave the student smarter.

Your capabilities:
1. **Explain** concepts with layered clarity — start simple, add depth, use analogies and real-world connections.
2. **Solve** problems step-by-step with transparent reasoning. Show your thought process: "First I notice X, which tells me Y, so I'll approach it by Z."
3. **Connect** new ideas to things the student already knows from the conversation.
4. **Challenge** — ask thought-provoking follow-up questions to deepen understanding.
5. **Practice** — suggest targeted practice problems when appropriate, with hints.

Teaching rules:
- Use LaTeX for all math: inline $...$ and display $$...$$
- Structure with clear markdown: headers, bullet points, numbered steps, **bold** key terms.
- Be warm, encouraging, and conversational — celebrate when the student shows understanding.
- Reference previous conversation context to build a learning arc.
- When explaining, always address the "why" — not just the "what" or "how."
- Highlight common mistakes and misconceptions proactively.
- Keep responses focused but thorough — cover what needs covering, nothing more.
""")

        effective_history = _resolve_effective_history(
            mode="doubt-solver",
            incoming_history=history,
            session_id=session_id,
            user_id=user_id,
        )

        # Build messages from history
        chat_messages = [system]
        for msg in effective_history[-20:]:  # Keep last 20 messages for context
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
            user_msg_parts.append(f"[Note: Image uploaded but analysis is disabled. Please describe the image content]:\n{image_context}")
        if message:
            user_msg_parts.append(message)

        chat_messages.append(HMsg(content="\n\n".join(user_msg_parts) if user_msg_parts else "Please help me understand this."))

        result = await _invoke_doubt_solver_llm(chat_messages)

        _append_session_turn(
            mode="doubt-solver",
            session_id=session_id,
            user_id=user_id,
            user_text=("\n\n".join(user_msg_parts) if user_msg_parts else message),
            assistant_text=result.content,
            base_history=effective_history,
        )

        return _attach_cost({
            "response": result.content,
            "image_context": image_context if image_context else None,
            "processing_time": _get_processing_time()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Doubt solver chat error: {str(e)}")
        if _is_credit_or_payment_error(str(e)):
            raise HTTPException(
                status_code=402,
                detail="Insufficient Mistral API credits/quota for this request. Please reduce response length or increase your Mistral quota."
            )
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────── Guide Chatbot ─────────────────────────────

@app.post("/api/guide/chat")
async def guide_chat(request: dict):
    """
    Context-aware guide chatbot for Exam Prep, Personalized Learning, and Video Lectures.
    Body: { "message": str, "mode": str, "context": str, "conversation_history": [{"role":str,"content":str}] }
    """
    try:
        _start_timing()
        start_tracking()
        message = request.get("message", "").strip()
        mode = request.get("mode", "general")
        context = request.get("context", "")
        history = request.get("conversation_history", [])
        session_id = str(request.get("session_id", "") or "")
        user_id = str(request.get("user_id", "") or "")

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

        effective_history = _resolve_effective_history(
            mode=f"guide:{mode}",
            incoming_history=history,
            session_id=session_id,
            user_id=user_id,
        )

        system = SystemMessage(content=system_prompt)

        chat_messages = [system]
        for msg in effective_history[-15:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant":
                chat_messages.append(AIMessage(content=content))
            else:
                chat_messages.append(HMsg(content=content))

        chat_messages.append(HMsg(content=message))

        result = await llm.ainvoke(chat_messages)

        _append_session_turn(
            mode=f"guide:{mode}",
            session_id=session_id,
            user_id=user_id,
            user_text=message,
            assistant_text=result.content,
            base_history=effective_history,
        )

        return _attach_cost({"response": result.content, "processing_time": _get_processing_time()})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Guide chat error: {str(e)}")
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
