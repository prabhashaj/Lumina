"""
PeCAR data models — Pydantic models, enumerations, and dataclasses
used across all six pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class LearningMode(str, Enum):
    RESEARCH = "research"
    EXAM_PREP = "exam_prep"
    PERSONALIZED = "personalized"
    VIDEO_LECTURE = "video_lecture"
    DOUBT_SOLVER = "doubt_solver"


class PromptTechnique(str, Enum):
    RAG = "rag"
    COT = "cot"
    GENERATED_KNOWLEDGE = "generated_knowledge"
    SELF_CONSISTENCY = "self_consistency"
    FEW_SHOT = "few_shot"
    PLAN_AND_SOLVE = "plan_and_solve"
    PERSONA = "persona"
    LEARNER_PROFILE_INJECTION = "learner_profile_injection"
    ADAPTIVE_COT_DEPTH = "adaptive_cot_depth"
    SCAFFOLDED_PROMPTING = "scaffolded_prompting"
    ZERO_SHOT_COT = "zero_shot_cot"
    SELF_VERIFICATION = "self_verification"
    PROGRESSIVE_HINTS = "progressive_hints"
    TOT = "tot"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    UNVERIFIABLE = "unverifiable"
    PENDING = "pending"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ---------------------------------------------------------------------------
# Pydantic Data Models
# ---------------------------------------------------------------------------


class LearnerProfile(BaseModel):
    """Represents a learner's current knowledge state and preferences."""

    knowledge_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Normalised knowledge level: 0=beginner, 1=advanced",
    )
    preferred_style: str = Field(default="visual", description="visual | verbal | mixed")
    prior_concepts: List[str] = Field(default_factory=list)
    difficulty_preference: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    language: str = Field(default="en")

    @field_validator("knowledge_level", mode="before")
    @classmethod
    def clamp_level(cls, v: Any) -> float:
        return max(0.0, min(1.0, float(v)))


class PecarIntentAnalysis(BaseModel):
    """PeCAR-compatible intent analysis — extends data from Lumina's IntentClassifier."""

    question_type: str = Field(
        default="conceptual",
        description="conceptual | procedural | factual | evaluative",
    )
    complexity: float = Field(default=0.5, ge=0.0, le=1.0, description="Normalised query complexity")
    modality: str = Field(default="text", description="text | image | video | multimodal")
    concepts: List[str] = Field(default_factory=list)
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    requires_retrieval: bool = True
    requires_visual: bool = False


class StrategyProfile(BaseModel):
    """Ordered strategy plan produced by the Intent-Aware Strategy Selector."""

    mode: LearningMode
    techniques: List[PromptTechnique]
    persona: Optional[str] = None
    num_paths: int = Field(default=3, ge=1, le=5)
    use_retrieval_grounding: bool = True
    max_refinement_iterations: int = Field(default=2, ge=0, le=3)
    technique_params: Dict[str, Any] = Field(default_factory=dict)


class ReasoningStep(BaseModel):
    """A single step in a chain-of-thought reasoning sequence."""

    index: int
    content: str
    supporting_sources: List[str] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.PENDING
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    corrective_context: Optional[str] = None
    regenerated: bool = False


class VerificationResult(BaseModel):
    """Outcome of checking a reasoning step against retrieved sources."""

    step_index: int
    status: VerificationStatus
    contradicting_source: Optional[str] = None
    supporting_excerpt: Optional[str] = None
    corrective_context: Optional[str] = None
    confidence_delta: float = 0.0


class PedagogicalScore(BaseModel):
    """Per-path pedagogical quality scores used in multi-path synthesis."""

    path_index: int
    factual_accuracy: float = Field(ge=0.0, le=1.0)
    explanation_clarity: float = Field(ge=0.0, le=1.0)
    scaffolding_completeness: float = Field(ge=0.0, le=1.0)
    composite_score: float = Field(ge=0.0, le=1.0)

    @classmethod
    def compute_composite(
        cls,
        path_index: int,
        factual_accuracy: float,
        explanation_clarity: float,
        scaffolding_completeness: float,
        w_f: float = 0.40,
        w_c: float = 0.35,
        w_s: float = 0.25,
    ) -> "PedagogicalScore":
        composite = w_f * factual_accuracy + w_c * explanation_clarity + w_s * scaffolding_completeness
        return cls(
            path_index=path_index,
            factual_accuracy=factual_accuracy,
            explanation_clarity=explanation_clarity,
            scaffolding_completeness=scaffolding_completeness,
            composite_score=round(composite, 4),
        )


class ReasoningPath(BaseModel):
    """A complete multi-step reasoning path with its evaluation."""

    index: int
    steps: List[ReasoningStep] = Field(default_factory=list)
    final_answer: str = ""
    score: Optional[PedagogicalScore] = None
    raw_output: str = ""


class RefinementIteration(BaseModel):
    """Records one quality-feedback refinement loop."""

    iteration: int
    dimension: str
    original_score: float
    textual_gradient: str
    refined_prompt: str
    new_score: Optional[float] = None


class PeCARoutput(BaseModel):
    """Final assembled response from the PeCAR pipeline."""

    mode: LearningMode
    query: str
    final_response: str
    strategy_profile: StrategyProfile
    reasoning_steps: List[ReasoningStep] = Field(default_factory=list)
    paths_evaluated: List[PedagogicalScore] = Field(default_factory=list)
    refinement_history: List[RefinementIteration] = Field(default_factory=list)
    depth_score: float = 0.0
    num_reasoning_steps: int = 0
    sources_used: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Depth Configuration (used by ARDC)
# ---------------------------------------------------------------------------


@dataclass
class DepthConfig:
    """Configuration constants for the ARDC depth scoring formula."""

    alpha: float = 0.4   # weight for query complexity C(q)
    beta: float = 0.3    # weight for learner novice-ness (1 - L(l))
    gamma: float = 0.3   # weight for mode weight W(m)

    # Mode weights W(m)
    mode_weights: Dict[str, float] = field(default_factory=lambda: {
        LearningMode.EXAM_PREP: 0.9,
        LearningMode.PERSONALIZED: 0.8,
        LearningMode.RESEARCH: 0.7,
        LearningMode.VIDEO_LECTURE: 0.6,
        LearningMode.DOUBT_SOLVER: 0.5,
    })

    # Depth-score -> step-count mapping boundaries
    medium_threshold: float = 0.40
    high_threshold: float = 0.65

    steps_low: Tuple[int, int] = (3, 4)
    steps_medium: Tuple[int, int] = (5, 7)
    steps_high: Tuple[int, int] = (8, 12)
