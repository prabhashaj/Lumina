"""
Shared data models and schemas for the AI Research Teaching Agent
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class DifficultyLevel(str, Enum):
    """Student difficulty level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class QuestionType(str, Enum):
    """Type of question asked"""
    CONCEPTUAL = "conceptual"
    PRACTICAL = "practical"
    MATHEMATICAL = "mathematical"
    MIXED = "mixed"


class SourceType(str, Enum):
    """Type of source"""
    ARTICLE = "article"
    ACADEMIC = "academic"
    VIDEO = "video"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class Source(BaseModel):
    """Source citation model"""
    title: str
    url: str
    snippet: str
    domain: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_type: SourceType = SourceType.OTHER
    published_date: Optional[str] = None


class ImageData(BaseModel):
    """Image data model"""
    url: str
    caption: str
    alt_text: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_url: Optional[str] = None


class TeachingSection(BaseModel):
    """Teaching content section"""
    title: str
    content: str
    subsections: Optional[List['TeachingSection']] = None


class ResearchRequest(BaseModel):
    """Request for research and teaching"""
    question: str = Field(min_length=3, max_length=2000)
    conversation_history: Optional[List[Dict[str, str]]] = []
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    image_context: Optional[str] = None  # VLM-analyzed image description
    file_context: Optional[str] = None   # Extracted text from attached files


class IntentAnalysis(BaseModel):
    """Analysis of user intent and question characteristics"""
    difficulty_level: DifficultyLevel
    question_type: QuestionType
    requires_visuals: bool
    requires_math: bool
    requires_code: bool
    key_concepts: List[str]
    confidence: float = Field(ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Web search result"""
    title: str
    url: str
    content: str
    score: float
    images: List[str] = []


class TeachingResponse(BaseModel):
    """Complete teaching response"""
    question: str
    tldr: str
    explanation: TeachingSection
    visual_explanation: Optional[str] = None
    images: List[ImageData] = []
    analogy: str
    practice_questions: List[str]
    sources: List[Source]
    difficulty_level: DifficultyLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    processing_time: float
    follow_up_suggestions: List[str] = []
    cost: Optional[Dict[str, Any]] = None


class StreamChunk(BaseModel):
    """Chunk for streaming responses"""
    type: str  # 'status', 'content', 'image', 'source', 'complete'
    data: Any
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentState(BaseModel):
    """State passed between agents in LangGraph"""
    original_question: str
    intent: Optional[IntentAnalysis] = None
    search_query: Optional[str] = None
    search_results: List[SearchResult] = []
    extracted_content: List[str] = []
    images: List[ImageData] = []
    teaching_content: Optional[str] = None
    sources: List[Source] = []
    retries: int = 0
    quality_score: float = 0.0
    errors: List[str] = []
    metadata: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
