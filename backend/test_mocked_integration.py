"""Fast mocked integration tests for the backend API surface."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

import main
from shared.schemas.models import (
    DifficultyLevel,
    ImageData,
    ResearchRequest,
    Source,
    TeachingResponse,
    TeachingSection,
)


def _mock_response() -> TeachingResponse:
    return TeachingResponse(
        question="What is photosynthesis?",
        tldr="Plants use sunlight to turn water and carbon dioxide into glucose and oxygen.",
        explanation=TeachingSection(
            title="Explanation",
            content="## Photosynthesis\n\nPlants capture light and convert it into chemical energy.",
        ),
        visual_explanation="A leaf acts like a solar-powered factory.",
        images=[
            ImageData(
                url="https://example.com/leaf.png",
                caption="Leaf diagram",
                relevance_score=0.9,
            )
        ],
        analogy="A leaf is like a solar-powered kitchen.",
        practice_questions=[
            "Why do plants need sunlight?",
            "What role does carbon dioxide play?",
        ],
        sources=[
            Source(
                title="Example source",
                url="https://example.com/photosynthesis",
                snippet="Plants convert light into chemical energy.",
                domain="example.com",
                relevance_score=0.95,
            )
        ],
        difficulty_level=DifficultyLevel.BEGINNER,
        confidence_score=0.92,
        processing_time=0.0,
    )


class _MockTeachingAgent:
    def __init__(self):
        self.llm = _MockQuizLLM()

    async def _call_llm(self, prompt: str, system: str = "", **kwargs: Any) -> str:
        lower_prompt = prompt.lower()
        if "personalized learning plan" in lower_prompt:
            return json.dumps(
                {
                    "knowledgeLevel": "beginner",
                    "overallScore": 50,
                    "strengthAreas": [],
                    "weaknessAreas": ["Basics"],
                    "learningPlan": [],
                    "personalizedTips": ["Start with core terms"],
                    "recommendedStyle": "visual",
                    "motivationalNote": "You have a clear place to start.",
                }
            )
        if "diagnostic assessment" in lower_prompt:
            return json.dumps(
                {
                    "topic": "Photosynthesis",
                    "questions": [
                        {
                            "id": "q_0",
                            "question": "What is the primary purpose of photosynthesis?",
                            "options": ["Make food", "Make rocks", "Make sound", "Make heat"],
                            "correctIndex": 0,
                            "difficulty": "foundational",
                            "cognitiveLevel": "recall",
                            "subTopic": "Basics",
                        }
                    ],
                }
            )
        if "curriculum designer" in lower_prompt:
            return json.dumps(
                {
                    "subject": "Biology",
                    "chapters": [
                        {
                            "title": "Foundations",
                            "description": "Core ideas first.",
                            "topics": ["Photosynthesis basics", "Energy conversion"],
                        }
                    ],
                }
            )
        if "expert exam question writer" in lower_prompt:
            return json.dumps(
                {
                    "questions": [
                        {
                            "question": "What does chlorophyll absorb?",
                            "options": ["Light", "Water", "Soil", "Oxygen"],
                            "correctIndex": 0,
                            "explanation": "Chlorophyll captures light energy.",
                        }
                    ]
                }
            )
        return json.dumps({"response": "mock"})


class _MockQuizLLM:
    async def ainvoke(self, messages):
        return type(
            "MockLLMResponse",
            (),
            {
                "content": json.dumps(
                    {
                        "questions": [
                            {
                                "question": "What does chlorophyll absorb?",
                                "options": ["Light", "Water", "Soil", "Oxygen"],
                                "correctIndex": 0,
                                "explanation": "Chlorophyll captures light energy.",
                            }
                        ]
                    }
                )
            },
        )()


class _MockOrchestrator:
    def __init__(self):
        self.teaching_agent = _MockTeachingAgent()

    async def process_question(self, request: ResearchRequest, progress_callback=None):
        if progress_callback:
            progress_callback("Mock research started")
            progress_callback("Mock synthesis")
        return _mock_response()


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main, "ResearchOrchestrator", _MockOrchestrator)
    monkeypatch.setattr(main.settings, "mistral_api_key", "")
    monkeypatch.setattr(main.settings, "elevenlabs_api_key", "")
    monkeypatch.setattr(main, "orchestrator", None)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.mark.integration
@pytest.mark.mocked_integration
def test_mocked_core_app_surface(client):
    health = client.get("/")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    config = client.get("/api/config")
    assert config.status_code == 200
    assert config.json()["features"]["file_upload"] is True

    research = client.post("/api/research", json={"question": "What is photosynthesis?"})
    assert research.status_code == 200
    data = research.json()
    assert data["tldr"]
    assert data["practice_questions"]

    stream = client.post("/api/research/stream", json={"question": "What is photosynthesis?"})
    assert stream.status_code == 200
    assert "text/event-stream" in stream.headers.get("content-type", "")
    assert "complete" in stream.text

    roadmap = client.post("/api/exam-prep/roadmap", json={"subject": "Biology"})
    assert roadmap.status_code == 200
    assert roadmap.json()["chapters"]

    quiz = client.post("/api/exam-prep/quiz", json={"subject": "Biology", "topic": "Photosynthesis"})
    assert quiz.status_code == 200
    assert quiz.json()["questions"]

    assessment = client.post("/api/personalized/assess", json={"topic": "Photosynthesis"})
    assert assessment.status_code == 200
    assert assessment.json()["questions"]

    profile = client.post(
        "/api/personalized/analyze-profile",
        json={
            "topic": "Photosynthesis",
            "questions": [{"correctIndex": 0, "difficulty": "foundational", "subTopic": "Basics"}],
            "answers": [0],
        },
    )
    assert profile.status_code == 200
    assert profile.json()["knowledgeLevel"] == "beginner"

    image_upload = client.post(
        "/api/upload/image",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        data={"question": "What is this?"},
    )
    assert image_upload.status_code == 200
    assert image_upload.json()["preview_url"].startswith("data:image/png;base64,")

    file_upload = client.post(
        "/api/upload/file",
        files={"file": ("test.txt", b"Photosynthesis is the process of turning light into energy.", "text/plain")},
    )
    assert file_upload.status_code == 200
    assert file_upload.json()["extracted_text"]

    tts = client.post("/api/tts", json={"text": "Hello world"})
    assert tts.status_code == 200
    assert tts.json()["use_browser_tts"] is True
