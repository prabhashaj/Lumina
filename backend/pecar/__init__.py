"""
PeCAR: Pedagogical Chain-of-Adaptive-Reasoning
================================================
A 6-stage prompting orchestration framework that dynamically composes
mode-aware, multi-strategy reasoning pipelines for educational AI.

Stages:
    1. Intent-Aware Strategy Selector (IASS)
    2. Adaptive Reasoning Depth Controller (ARDC)
    3. Retrieval-Grounded Chain-of-Thought (RG-CoT)
    4. Pedagogical Multi-Path Synthesis (PMPS)
    5. Quality-Feedback Prompt Refinement (QFPR)
    6. Mode-Specific Output Assembly (MSOA)
"""

from pecar.models import (
    LearningMode,
    PromptTechnique,
    VerificationStatus,
    DifficultyLevel,
    LearnerProfile,
    StrategyProfile,
    ReasoningStep,
    VerificationResult,
    PedagogicalScore,
    ReasoningPath,
    RefinementIteration,
    PeCARoutput,
)
from pecar.orchestrator import PeCAR

__all__ = [
    "LearningMode",
    "PromptTechnique",
    "VerificationStatus",
    "DifficultyLevel",
    "LearnerProfile",
    "StrategyProfile",
    "ReasoningStep",
    "VerificationResult",
    "PedagogicalScore",
    "ReasoningPath",
    "RefinementIteration",
    "PeCARoutput",
    "PeCAR",
]
