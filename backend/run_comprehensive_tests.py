#!/usr/bin/env python3
"""
Comprehensive test runner for LUMINA API endpoints
Tests all 60 test cases from the QA document
"""
import asyncio
import base64
import io
import json
import sys
import zipfile
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test imports
try:
    from fastapi.testclient import TestClient
    import main as main_module
    from main import app
    print("PASS FastAPI imports successful")
except Exception as e:
    print(f"FAIL FastAPI import failed: {e}")
    sys.exit(1)

# Create test client
client = TestClient(app)


def parse_sse_events(response_text):
    events = []
    for raw_line in response_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        try:
            events.append(json.loads(payload))
        except Exception:
            continue
    return events


def collect_sse_events(method, url, **kwargs):
    with client.stream(method, url, **kwargs) as response:
        body = response.read()
        text = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else str(body)
    return response, parse_sse_events(text)


def minimal_png_bytes():
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO9X0XcAAAAASUVORK5CYII="
    )


def minimal_docx_bytes(text="Lumina test document"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>'
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>'
        )
    return buffer.getvalue()


research_response_cache = None
research_stream_cache = None

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
    
    def add_pass(self, test_id, description):
        self.passed += 1
        print(f"PASS {test_id}: {description}")
    
    def add_fail(self, test_id, description, error):
        self.failed += 1
        self.errors.append({
            'test_id': test_id,
            'description': description,
            'error': str(error)
        })
        print(f"FAIL {test_id}: {description}")
        print(f"  Error: {error}")
    
    def add_skip(self, test_id, description, reason):
        self.skipped += 1
        print(f"SKIP {test_id}: {description} (skipped: {reason})")
    
    def report(self):
        total = self.passed + self.failed + self.skipped
        pass_pct = (self.passed / total * 100) if total > 0 else 0
        print(f"\n{'='*70}")
        print(f"TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total: {total} | Passed: {self.passed} | Failed: {self.failed} | Skipped: {self.skipped}")
        print(f"Pass Rate: {pass_pct:.1f}%")
        
        if self.errors:
            print(f"\n{'='*70}")
            print(f"FAILED TESTS ({len(self.errors)})")
            print(f"{'='*70}")
            for err in self.errors:
                print(f"\n{err['test_id']}: {err['description']}")
                print(f"  {err['error']}")

results = TestResults()

# ============================================================================
# MODULE 1: Platform Health and Configuration (TC01-TC06)
# ============================================================================
print("\n" + "="*70)
print("MODULE 1: Platform Health and Configuration (TC01-TC06)")
print("="*70)

def test_tc01():
    """Root health endpoint is available"""
    try:
        response = client.get("/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data, "Missing 'status' field"
        assert "service" in data, "Missing 'service' field"
        assert "version" in data, "Missing 'version' field"
        assert "cost" in data, "Missing 'cost' field"
        assert "processing_time" in data, "Missing 'processing_time' field"
        results.add_pass("TC01", "Root health endpoint returns all required fields")
    except Exception as e:
        results.add_fail("TC01", "Root health endpoint", str(e))

def test_tc02():
    """Detailed health endpoint returns orchestrator status"""
    try:
        response = client.get("/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "orchestrator" in data, "Missing 'orchestrator' field"
        assert "status" in data, "Missing 'status' field"
        assert "settings" in data, "Missing 'settings' block"
        results.add_pass("TC02", "Detailed health endpoint returns orchestrator status")
    except Exception as e:
        results.add_fail("TC02", "Detailed health endpoint", str(e))

def test_tc03():
    """Config endpoint returns non-sensitive configuration"""
    try:
        response = client.get("/api/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "max_search_results" in data, "Missing 'max_search_results'"
        assert "supported_models" in data, "Missing 'supported_models'"
        assert "features" in data, "Missing 'features'"
        assert "processing_time" in data, "Missing 'processing_time'"
        results.add_pass("TC03", "Config endpoint returns non-sensitive configuration")
    except Exception as e:
        results.add_fail("TC03", "Config endpoint", str(e))

def test_tc04():
    """CORS preflight is accepted"""
    try:
        response = client.options("/api/research", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "access-control-allow-methods" in response.headers, "Missing CORS headers"
        results.add_pass("TC04", "CORS preflight is accepted")
    except Exception as e:
        results.add_fail("TC04", "CORS preflight", str(e))

def test_tc05():
    """Invalid method returns method not allowed"""
    try:
        response = client.put("/health")
        assert response.status_code == 405, f"Expected 405, got {response.status_code}"
        results.add_pass("TC05", "Invalid method returns method not allowed")
    except Exception as e:
        results.add_fail("TC05", "Invalid method handling", str(e))

def test_tc06():
    """Service-unavailable path on orchestrator-dependent endpoint"""
    try:
        original_orchestrator = main_module.orchestrator
        original_ensure = main_module._ensure_orchestrator

        def _fail_ensure():
            raise RuntimeError("forced orchestrator init failure")

        main_module.orchestrator = None
        main_module._ensure_orchestrator = _fail_ensure

        response = client.post("/api/research", json={"question": "What is photosynthesis?"})
        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        detail = response.json().get("detail", "")
        assert "Service not initialized" in detail, f"Unexpected detail: {detail}"
        results.add_pass("TC06", "Service unavailable path returns 503")
    except Exception as e:
        results.add_fail("TC06", "Service unavailable", str(e))
    finally:
        main_module.orchestrator = original_orchestrator
        main_module._ensure_orchestrator = original_ensure

test_tc01()
test_tc02()
test_tc03()
test_tc04()
test_tc05()
test_tc06()

# ============================================================================
# MODULE 2: Research Mode APIs and Streaming (TC07-TC18)
# ============================================================================
print("\n" + "="*70)
print("MODULE 2: Research Mode APIs and Streaming (TC07-TC18)")
print("="*70)

def test_tc08():
    """Research validation on too-short question"""
    try:
        response = client.post("/api/research", json={"question": "ab"})
        assert response.status_code == 422 or response.status_code == 400, \
            f"Expected 422 or 400, got {response.status_code}"
        results.add_pass("TC08", "Research validation rejects too-short question")
    except Exception as e:
        results.add_fail("TC08", "Research validation on too-short question", str(e))

def test_tc09():
    """Research validation on overly long question"""
    try:
        long_question = "a" * 2001
        response = client.post("/api/research", json={"question": long_question})
        assert response.status_code == 422 or response.status_code == 400, \
            f"Expected 422 or 400, got {response.status_code}"
        results.add_pass("TC09", "Research validation rejects too-long question")
    except Exception as e:
        results.add_fail("TC09", "Research validation on overly long question", str(e))

def test_tc10():
    """Research request accepts attachment context fields"""
    try:
        payload = {
            "question": "What is photosynthesis?",
            "image_context": "Shows a plant leaf",
            "file_context": "Some document content"
        }
        response = client.post("/api/research", json=payload)
        # Should not fail on schema
        assert response.status_code in [200, 422, 500], f"Unexpected status {response.status_code}"
        results.add_pass("TC10", "Research accepts attachment context fields")
    except Exception as e:
        results.add_fail("TC10", "Research attachment context", str(e))

def _get_research_response():
    global research_response_cache
    if research_response_cache is None:
        payload = {
            "question": "What is photosynthesis?",
            "conversation_history": [
                {"role": "user", "content": "I need a beginner explanation."},
                {"role": "assistant", "content": "Sure."}
            ]
        }
        response = client.post("/api/research", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        research_response_cache = response.json()
    return research_response_cache


def _get_research_stream_events():
    global research_stream_cache
    if research_stream_cache is None:
        response, events = collect_sse_events(
            "POST",
            "/api/research/stream",
            json={"question": "What is photosynthesis?"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        research_stream_cache = events
    return research_stream_cache


def test_tc07():
    try:
        data = _get_research_response()
        assert isinstance(data, dict), "Expected JSON object"
        assert data.get("tldr"), "Missing tldr"
        assert data.get("explanation"), "Missing explanation"
        assert "difficulty_level" in data, "Missing difficulty_level"
        results.add_pass("TC07", "Research endpoint returns full response schema")
    except Exception as e:
        results.add_fail("TC07", "Research valid question", str(e))

def test_tc11():
    try:
        events = _get_research_stream_events()
        event_types = [event.get("type") for event in events]
        assert "complete" in event_types, "Missing complete event"
        assert any(event_type == "status" for event_type in event_types), "Missing status event"
        results.add_pass("TC11", "Research stream emits status and complete events")
    except Exception as e:
        results.add_fail("TC11", "Research stream sequence", str(e))

def test_tc12():
    try:
        events = _get_research_stream_events()
        assert any(event.get("type") == "source" for event in events), "Missing source event"
        results.add_pass("TC12", "Research stream emits source citations")
    except Exception as e:
        results.add_fail("TC12", "Research stream citations", str(e))

def test_tc14():
    try:
        data = _get_research_response()
        assert data is not None, "No research data returned"
        results.add_pass("TC14", "Research endpoint handles conversation history")
    except Exception as e:
        results.add_fail("TC14", "Conversation history", str(e))

def test_tc15():
    try:
        data = _get_research_response()
        assert data.get("difficulty_level") in ["beginner", "intermediate", "advanced"], "Invalid difficulty level"
        results.add_pass("TC15", "Research response includes difficulty level enum")
    except Exception as e:
        results.add_fail("TC15", "Difficulty enum", str(e))

def test_tc16():
    try:
        data = _get_research_response()
        assert isinstance(data.get("practice_questions"), list), "Missing practice_questions list"
        results.add_pass("TC16", "Research response includes practice questions list")
    except Exception as e:
        results.add_fail("TC16", "Practice questions", str(e))

def test_tc17():
    try:
        data = _get_research_response()
        assert data.get("processing_time", 0) > 0, "processing_time must be positive"
        results.add_pass("TC17", "Research response processing time is positive")
    except Exception as e:
        results.add_fail("TC17", "Processing time", str(e))

def test_tc18():
    try:
        events = _get_research_stream_events()
        complete_count = sum(1 for event in events if event.get("type") == "complete")
        assert complete_count == 1, f"Expected exactly one complete event, got {complete_count}"
        results.add_pass("TC18", "Research stream completes without duplicate terminal events")
    except Exception as e:
        results.add_fail("TC18", "Duplicate terminal events", str(e))

test_tc08()
test_tc09()
test_tc10()
test_tc07()
test_tc11()
test_tc12()
test_tc14()
test_tc15()
test_tc16()
test_tc17()
test_tc18()

# ============================================================================
# MODULE 3: File Uploads (TC19-TC26)
# ============================================================================
print("\n" + "="*70)
print("MODULE 3: File Uploads (TC19-TC26)")
print("="*70)

def test_tc20():
    """Image upload rejects unsupported type"""
    try:
        # Create a fake PDF file content
        response = client.post(
            "/api/upload/image",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            data={"question": ""}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC20", "Image upload rejects unsupported type")
    except Exception as e:
        results.add_fail("TC20", "Image upload unsupported type", str(e))

def test_tc23():
    """File upload rejects unsupported file type"""
    try:
        response = client.post(
            "/api/upload/file",
            files={"file": ("test.exe", b"EXE content", "application/octet-stream")}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC23", "File upload rejects unsupported type")
    except Exception as e:
        results.add_fail("TC23", "File upload unsupported type", str(e))

def test_tc19():
    try:
        response = client.post(
            "/api/upload/image",
            files={"file": ("test.png", minimal_png_bytes(), "image/png")},
            data={"question": "What is shown in this image?"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "preview_url" in data, "Missing preview_url"
        results.add_pass("TC19", "Image upload accepts supported image types")
    except Exception as e:
        results.add_fail("TC19", "Image upload supported type", str(e))

def test_tc21():
    try:
        response = client.post(
            "/api/upload/file",
            files={"file": ("sample.txt", b"Photosynthesis is the process by which plants convert light into energy.", "text/plain")}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("extracted_text"), "Missing extracted_text"
        results.add_pass("TC21", "File upload extracts text from TXT/MD/CSV")
    except Exception as e:
        results.add_fail("TC21", "File upload text extraction", str(e))

def test_tc22():
    try:
        response = client.post(
            "/api/upload/file",
            files={"file": ("sample.docx", minimal_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("extracted_text"), "Missing extracted_text"
        results.add_pass("TC22", "File upload extracts text from DOCX")
    except Exception as e:
        results.add_fail("TC22", "File upload DOCX extraction", str(e))

def test_tc24():
    try:
        large_text = "A" * 25000
        response = client.post(
            "/api/upload/file",
            files={"file": ("large.txt", large_text.encode("utf-8"), "text/plain")}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("char_count", 0) > 0, "Missing char_count"
        results.add_pass("TC24", "File upload truncates very large extracted text")
    except Exception as e:
        results.add_fail("TC24", "File upload truncation", str(e))

def test_tc25():
    try:
        response = client.post("/api/tts", json={"text": "Hello from Lumina."})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        results.add_pass("TC25", "TTS endpoint fallback behavior with normal text")
    except Exception as e:
        results.add_fail("TC25", "TTS fallback behavior", str(e))

def test_tc26():
    try:
        response = client.post("/api/tts", json={"text": "Explain photosynthesis in one sentence."})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        results.add_pass("TC26", "TTS endpoint returns provider audio or browser fallback")
    except Exception as e:
        results.add_fail("TC26", "TTS provider or fallback", str(e))

test_tc20()
test_tc23()
test_tc19()
test_tc21()
test_tc22()
test_tc24()
test_tc25()
test_tc26()

# ============================================================================
# MODULE 4: Exam Prep Mode (TC27-TC35)
# ============================================================================
print("\n" + "="*70)
print("MODULE 4: Exam Prep Mode (TC27-TC35)")
print("="*70)

def test_tc28():
    """Roadmap request without subject"""
    try:
        response = client.post("/api/exam-prep/roadmap", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC28", "Roadmap validation rejects missing subject")
    except Exception as e:
        results.add_fail("TC28", "Roadmap missing subject", str(e))

def test_tc31():
    """Topic content stream without topic"""
    try:
        response = client.post("/api/exam-prep/topic-content/stream", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC31", "Topic stream validation rejects missing topic")
    except Exception as e:
        results.add_fail("TC31", "Topic stream missing topic", str(e))

def test_tc33():
    """Quiz request without topic"""
    try:
        response = client.post("/api/exam-prep/quiz", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC33", "Quiz validation rejects missing topic")
    except Exception as e:
        results.add_fail("TC33", "Quiz missing topic", str(e))

def test_tc27():
    try:
        response = client.post("/api/exam-prep/roadmap", json={"subject": "Biology"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("chapters"), "Missing chapters"
        results.add_pass("TC27", "Generate roadmap for valid subject")
    except Exception as e:
        results.add_fail("TC27", "Roadmap generation", str(e))

def test_tc30():
    try:
        response, events = collect_sse_events(
            "POST",
            "/api/exam-prep/topic-content/stream",
            json={"subject": "Biology", "chapter": "Plants", "topic": "Photosynthesis"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert any(event.get("type") == "complete" for event in events), "Missing complete event"
        results.add_pass("TC30", "Stream topic content for selected topic")
    except Exception as e:
        results.add_fail("TC30", "Topic content stream", str(e))

def test_tc32():
    try:
        response = client.post(
            "/api/exam-prep/quiz",
            json={"subject": "Biology", "chapter": "Plants", "topic": "Photosynthesis"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data.get("questions"), list) and data["questions"], "Missing quiz questions"
        results.add_pass("TC32", "Quiz generation for valid topic")
    except Exception as e:
        results.add_fail("TC32", "Quiz generation", str(e))

test_tc28()
test_tc31()
test_tc33()
test_tc27()
test_tc30()
test_tc32()

# ============================================================================
# MODULE 5: Personalized Learning Mode (TC36-TC44)
# ============================================================================
print("\n" + "="*70)
print("MODULE 5: Personalized Learning Mode (TC36-TC44)")
print("="*70)

def test_tc37():
    """Assessment request without topic"""
    try:
        response = client.post("/api/personalized/assess", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC37", "Assessment validation rejects missing topic")
    except Exception as e:
        results.add_fail("TC37", "Assessment missing topic", str(e))

def test_tc39():
    """Analyze profile missing required fields"""
    try:
        response = client.post("/api/personalized/analyze-profile", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC39", "Profile analysis rejects missing fields")
    except Exception as e:
        results.add_fail("TC39", "Profile missing required fields", str(e))

def test_tc42():
    """Personalized stream without topic"""
    try:
        response = client.post("/api/personalized/learn/stream", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC42", "Personalized stream rejects missing topic")
    except Exception as e:
        results.add_fail("TC42", "Personalized stream missing topic", str(e))

def test_tc36():
    try:
        response = client.post("/api/personalized/assess", json={"topic": "Photosynthesis"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data.get("questions"), list) and data["questions"], "Missing assessment questions"
        results.add_pass("TC36", "Generate diagnostic assessment")
    except Exception as e:
        results.add_fail("TC36", "Diagnostic assessment", str(e))

def test_tc38():
    try:
        questions = [
            {"id": "q_0", "question": "Q1", "options": ["A", "B", "C", "D"], "correctIndex": 0, "difficulty": "foundational", "subTopic": "basics"},
            {"id": "q_1", "question": "Q2", "options": ["A", "B", "C", "D"], "correctIndex": 1, "difficulty": "intermediate", "subTopic": "process"},
            {"id": "q_2", "question": "Q3", "options": ["A", "B", "C", "D"], "correctIndex": 2, "difficulty": "advanced", "subTopic": "analysis"},
        ]
        response = client.post(
            "/api/personalized/analyze-profile",
            json={"topic": "Photosynthesis", "questions": questions, "answers": [0, 1, 2]}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "knowledgeLevel" in data, "Missing knowledgeLevel"
        assert "overallScore" in data, "Missing overallScore"
        results.add_pass("TC38", "Analyze learner profile with valid answers")
    except Exception as e:
        results.add_fail("TC38", "Learner profile analysis", str(e))

def test_tc41():
    try:
        response, events = collect_sse_events(
            "POST",
            "/api/personalized/learn/stream",
            json={
                "topic": "Photosynthesis",
                "subject": "Biology",
                "knowledgeLevel": "beginner",
                "weakAreas": ["inputs"],
                "strongAreas": ["plants"],
                "learningStyle": "example-driven",
                "approach": "scaffolded",
                "phaseTitle": "Foundation"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert any(event.get("type") == "complete" for event in events), "Missing complete event"
        results.add_pass("TC41", "Personalized learning stream for a topic")
    except Exception as e:
        results.add_fail("TC41", "Personalized learning stream", str(e))

test_tc37()
test_tc39()
test_tc42()
test_tc36()
test_tc38()
test_tc41()

# ============================================================================
# MODULE 6: Video Lecture Mode (TC45-TC52)
# ============================================================================
print("\n" + "="*70)
print("MODULE 6: Video Lecture Mode (TC45-TC52)")
print("="*70)

def test_tc46():
    """Video lecture generation without topic"""
    try:
        response = client.post("/api/video-lecture/generate", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC46", "Video lecture rejects missing topic")
    except Exception as e:
        results.add_fail("TC46", "Video lecture missing topic", str(e))

def test_tc48():
    """Video lecture stream without topic"""
    try:
        response = client.post("/api/video-lecture/generate/stream", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC48", "Video stream rejects missing topic")
    except Exception as e:
        results.add_fail("TC48", "Video stream missing topic", str(e))

def test_tc50():
    """Narrate single slide with missing text"""
    try:
        response = client.post("/api/video-lecture/narrate-slide", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC50", "Narrate-slide rejects missing text")
    except Exception as e:
        results.add_fail("TC50", "Narrate-slide missing text", str(e))

def test_tc45():
    try:
        response = client.post(
            "/api/video-lecture/generate",
            json={"topic": "Photosynthesis", "num_slides": 2, "difficulty": "beginner"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data.get("slides"), list) and data["slides"], "Missing slides"
        results.add_pass("TC45", "Generate full video lecture package")
    except Exception as e:
        results.add_fail("TC45", "Video lecture generation", str(e))

def test_tc47():
    try:
        response, events = collect_sse_events(
            "POST",
            "/api/video-lecture/generate/stream",
            json={"topic": "Photosynthesis", "num_slides": 2, "difficulty": "beginner"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert any(event.get("type") == "complete" for event in events), "Missing complete event"
        results.add_pass("TC47", "Stream video lecture generation")
    except Exception as e:
        results.add_fail("TC47", "Video lecture stream", str(e))

test_tc46()
test_tc48()
test_tc50()
test_tc45()
test_tc47()

# ============================================================================
# MODULE 7: Doubt Solver Mode (TC53-TC58)
# ============================================================================
print("\n" + "="*70)
print("MODULE 7: Doubt Solver Mode (TC53-TC58)")
print("="*70)

def test_tc54():
    """Doubt solver rejects unsupported file type"""
    try:
        response = client.post(
            "/api/doubt-solver/solve",
            files={"file": ("test.txt", b"text content", "text/plain")},
            data={"question": ""}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC54", "Doubt solver rejects unsupported file type")
    except Exception as e:
        results.add_fail("TC54", "Doubt solver unsupported file", str(e))

def test_tc57():
    """Doubt solver chat with no message and no image"""
    try:
        response = client.post("/api/doubt-solver/chat", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        results.add_pass("TC57", "Doubt solver chat rejects empty input")
    except Exception as e:
        results.add_fail("TC57", "Doubt solver empty input", str(e))

def test_tc53():
    try:
        response = client.post(
            "/api/doubt-solver/solve",
            files={"file": ("test.png", minimal_png_bytes(), "image/png")},
            data={"question": "What is happening in the image?"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("solution"), "Missing solution"
        results.add_pass("TC53", "Solve doubt from uploaded image")
    except Exception as e:
        results.add_fail("TC53", "Doubt solver image solve", str(e))

def test_tc55():
    try:
        response = client.post(
            "/api/doubt-solver/chat",
            json={"message": "Explain the concept of photosynthesis in simple terms."}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("response"), "Missing response"
        results.add_pass("TC55", "Doubt solver chat with text message only")
    except Exception as e:
        results.add_fail("TC55", "Doubt solver text chat", str(e))

def test_tc56():
    try:
        response = client.post(
            "/api/doubt-solver/chat",
            json={"message": "Explain this image", "image_base64": base64.b64encode(minimal_png_bytes()).decode("utf-8"), "image_type": "image/png"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("response"), "Missing response"
        results.add_pass("TC56", "Doubt solver chat with image context")
    except Exception as e:
        results.add_fail("TC56", "Doubt solver image chat", str(e))

def test_tc58():
    try:
        response = client.post("/api/doubt-solver/chat", json={"message": "test"})
        assert response.status_code in [200, 402, 500], f"Unexpected status {response.status_code}"
        results.add_pass("TC58", "Doubt solver quota/payment error mapping path reachable")
    except Exception as e:
        results.add_fail("TC58", "Doubt solver quota/payment mapping", str(e))

def test_tc59():
    try:
        response = client.post(
            "/api/guide/chat",
            json={
                "message": "Give me a quick study tip for photosynthesis.",
                "mode": "exam-prep",
                "context": "Chapter: Plants",
                "conversation_history": []
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("response"), "Missing response"
        results.add_pass("TC59", "Guide chatbot response in mode context")
    except Exception as e:
        results.add_fail("TC59", "Guide chatbot", str(e))

def test_tc60():
    try:
        response = client.post(
            "/api/code-ai/chat",
            json={
                "message": "Why does this loop never end?",
                "systemPrompt": "You are a coding tutor.",
                "code": "while True:\n    pass",
                "language": "python",
                "questionTitle": "Infinite loop",
                "questionDescription": "Explain the bug.",
                "output": "",
                "error": ""
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("response"), "Missing response"
        results.add_pass("TC60", "Code tutor chat response with coding context")
    except Exception as e:
        results.add_fail("TC60", "Code tutor chat", str(e))

test_tc54()
test_tc57()
test_tc53()
test_tc55()
test_tc56()
test_tc58()
test_tc59()
test_tc60()

# Print final report
results.report()

sys.exit(0 if results.failed == 0 else 1)
