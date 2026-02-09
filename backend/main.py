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
logger.add(
    settings.log_file,
    rotation="500 MB",
    retention="10 days",
    level=settings.log_level
)

# Global orchestrator instance
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator
    
    logger.info("Starting AI Research Teaching Agent...")
    orchestrator = ResearchOrchestrator()
    logger.info("Orchestrator initialized")
    
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
                        "stability": 0.65,
                        "similarity_boost": 0.80,
                        "style": 0.35,
                        "use_speaker_boost": False
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

        agent = orchestrator.teaching_agent

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

        llm_response = await agent._call_llm(quiz_prompt)

        import re
        json_match = re.search(r'\{[\s\S]*\}', llm_response)
        if not json_match:
            raise ValueError("Could not parse quiz from LLM response")

        quiz_data = json.loads(json_match.group())

        # Add IDs to questions
        for i, q in enumerate(quiz_data.get("questions", [])):
            q["id"] = f"q_{i}"

        return quiz_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _analyze_image_with_vlm(image_url: str, question: str = "") -> str:
    """Analyze an uploaded image with VLM"""
    try:
        if settings.replicate_api_token:
            import replicate
            prompt = f"""Describe this image in detail for educational purposes.
What do you see? Include:
- Main subject/content
- Key details, labels, or text visible
- Any diagrams, charts, or visual elements
- How this relates to: {question if question else 'the topic shown'}

Be specific and thorough."""

            output = replicate.run(
                "yorickvp/llava-13b:b5f6212d032508382d61ff00469ddda3e32fd8a0e75dc39d8a4191bb742157fb",
                input={
                    "image": image_url,
                    "prompt": prompt,
                    "max_tokens": 500
                }
            )
            return "".join(output)
        else:
            return "Image uploaded successfully. VLM analysis requires a Replicate API token."
    except Exception as e:
        logger.error(f"VLM analysis error: {str(e)}")
        return f"Image uploaded. VLM analysis unavailable: {str(e)}"


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


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
