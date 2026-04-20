"""
Stage 1 — Intent-Aware Strategy Selector (IASS)

Maps (IntentAnalysis, LearningMode, LearnerProfile) to a StrategyProfile
that specifies which prompting techniques to apply, in what order, and
with what mode-specific parameters.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from pecar.models import (
    LearnerProfile,
    LearningMode,
    PecarIntentAnalysis,
    PromptTechnique,
    StrategyProfile,
)

# Static strategy profiles per mode — ordered list of techniques
_MODE_STRATEGY_MAP: Dict[LearningMode, List[PromptTechnique]] = {
    LearningMode.RESEARCH: [
        PromptTechnique.RAG,
        PromptTechnique.COT,
        PromptTechnique.GENERATED_KNOWLEDGE,
        PromptTechnique.SELF_CONSISTENCY,
    ],
    LearningMode.EXAM_PREP: [
        PromptTechnique.FEW_SHOT,
        PromptTechnique.PLAN_AND_SOLVE,
        PromptTechnique.COT,
        PromptTechnique.PERSONA,
    ],
    LearningMode.PERSONALIZED: [
        PromptTechnique.LEARNER_PROFILE_INJECTION,
        PromptTechnique.ADAPTIVE_COT_DEPTH,
        PromptTechnique.SCAFFOLDED_PROMPTING,
    ],
    LearningMode.VIDEO_LECTURE: [
        PromptTechnique.PLAN_AND_SOLVE,
        PromptTechnique.GENERATED_KNOWLEDGE,
        PromptTechnique.PERSONA,
        PromptTechnique.TOT,
    ],
    LearningMode.DOUBT_SOLVER: [
        PromptTechnique.ZERO_SHOT_COT,
        PromptTechnique.RAG,
        PromptTechnique.SELF_VERIFICATION,
        PromptTechnique.PROGRESSIVE_HINTS,
    ],
}

_MODE_PERSONAS: Dict[LearningMode, Optional[str]] = {
    LearningMode.RESEARCH: None,
    LearningMode.EXAM_PREP: "Expert Examiner",
    LearningMode.PERSONALIZED: None,
    LearningMode.VIDEO_LECTURE: "Engaging University Lecturer",
    LearningMode.DOUBT_SOLVER: "Socratic Tutor",
}


class IntentAwareStrategySelector:
    """
    Stage 1 — Intent-Aware Strategy Selector (IASS).

    Maps (IntentAnalysis, LearningMode, LearnerProfile) to a StrategyProfile
    that specifies which prompting techniques to apply, in what order, and
    with what mode-specific parameters.
    """

    HIGH_COMPLEXITY_THRESHOLD = 0.7
    LOW_COMPLEXITY_THRESHOLD = 0.35

    def select(
        self,
        intent: PecarIntentAnalysis,
        mode: LearningMode,
        learner: LearnerProfile,
    ) -> StrategyProfile:
        """
        Produce a StrategyProfile tailored to the query, mode, and learner.

        Args:
            intent: Classified intent (PeCAR-compatible).
            mode: The active Lumina learning mode.
            learner: The current learner's profile.

        Returns:
            A StrategyProfile with ordered techniques and configuration.
        """
        base_techniques = list(_MODE_STRATEGY_MAP[mode])
        persona = _MODE_PERSONAS[mode]
        technique_params: Dict[str, Any] = {}

        # --- Adjust for query complexity ---
        if intent.complexity >= self.HIGH_COMPLEXITY_THRESHOLD:
            if PromptTechnique.COT not in base_techniques:
                base_techniques.insert(1, PromptTechnique.COT)
            if PromptTechnique.RAG not in base_techniques:
                base_techniques.insert(0, PromptTechnique.RAG)
            num_paths = 2
        elif intent.complexity <= self.LOW_COMPLEXITY_THRESHOLD:
            base_techniques = base_techniques[:2]
            num_paths = 1
        else:
            num_paths = 1 if mode == LearningMode.DOUBT_SOLVER else 2

        # --- Learner-level adjustments ---
        if learner.knowledge_level < 0.4:
            if PromptTechnique.SCAFFOLDED_PROMPTING not in base_techniques:
                base_techniques.append(PromptTechnique.SCAFFOLDED_PROMPTING)
            if PromptTechnique.PROGRESSIVE_HINTS not in base_techniques:
                base_techniques.append(PromptTechnique.PROGRESSIVE_HINTS)
            technique_params["scaffolding_level"] = "high"
        elif learner.knowledge_level > 0.75:
            base_techniques = [
                t for t in base_techniques
                if t not in (PromptTechnique.SCAFFOLDED_PROMPTING, PromptTechnique.PROGRESSIVE_HINTS)
            ]
            technique_params["scaffolding_level"] = "low"
        else:
            technique_params["scaffolding_level"] = "medium"

        # --- Retrieval requirement ---
        use_retrieval = intent.requires_retrieval or PromptTechnique.RAG in base_techniques

        # --- Refinement budget ---
        max_refinements = 1 if intent.complexity >= self.HIGH_COMPLEXITY_THRESHOLD else 0

        logger.debug(
            "IASS selected %d techniques for mode=%s, complexity=%.2f, learner=%.2f",
            len(base_techniques),
            mode,
            intent.complexity,
            learner.knowledge_level,
        )

        return StrategyProfile(
            mode=mode,
            techniques=base_techniques,
            persona=persona,
            num_paths=num_paths,
            use_retrieval_grounding=use_retrieval,
            max_refinement_iterations=max_refinements,
            technique_params=technique_params,
        )
