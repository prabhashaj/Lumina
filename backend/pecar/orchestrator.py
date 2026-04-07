"""
PeCAR Orchestrator — chains all six stages into a single async pipeline.

Integrates with Lumina's LangGraph state via a dictionary-based interface.
Designed to be called from the Teaching Synthesis agent or as a LangGraph node.

Usage:
    pecar = PeCAR(call_llm_fn=agent._call_llm)
    result = await pecar.run(state=langgraph_state)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from pecar.models import (
    DepthConfig,
    LearnerProfile,
    LearningMode,
    PeCARoutput,
    PecarIntentAnalysis,
    ReasoningPath,
    ReasoningStep,
    RefinementIteration,
    VerificationStatus,
)
from pecar import prompts
from pecar.strategy_selector import IntentAwareStrategySelector
from pecar.depth_controller import AdaptiveReasoningDepthController
from pecar.rg_cot import RetrievalGroundedCoT
from pecar.multi_path import PedagogicalMultiPathSynthesis
from pecar.quality_refinement import QualityFeedbackPromptRefinement
from pecar.output_assembler import ModeSpecificOutputAssembler


class PeCAR:
    """
    PeCAR Orchestrator — chains all six stages into a single async pipeline.

    Accepts a Lumina-compatible LLM callable and runs:
        1. IASS  — Intent-Aware Strategy Selection
        2. ARDC  — Adaptive Reasoning Depth Control
        3. RG-CoT — Retrieval-Grounded Chain-of-Thought
        4. PMPS  — Pedagogical Multi-Path Synthesis
        5. QFPR  — Quality-Feedback Prompt Refinement
        6. MSOA  — Mode-Specific Output Assembly
    """

    def __init__(
        self,
        call_llm_fn: Callable,
        depth_config: Optional[DepthConfig] = None,
    ) -> None:
        """
        Args:
            call_llm_fn: Async LLM callable with signature:
                         async (prompt: str, system: str, **kwargs) -> str
            depth_config: Optional custom depth configuration.
        """
        self._llm = call_llm_fn

        self.iass = IntentAwareStrategySelector()
        self.ardc = AdaptiveReasoningDepthController(config=depth_config)
        self.rg_cot = RetrievalGroundedCoT(call_llm_fn=call_llm_fn)
        self.pmps = PedagogicalMultiPathSynthesis(call_llm_fn=call_llm_fn)
        self.qfpr = QualityFeedbackPromptRefinement(call_llm_fn=call_llm_fn)
        self.msoa = ModeSpecificOutputAssembler(call_llm_fn=call_llm_fn)

    async def run(self, state: Dict[str, Any]) -> PeCARoutput:
        """
        Execute the full PeCAR pipeline from LangGraph state.

        Expected state keys:
            - query (str): User query
            - intent_analysis (PecarIntentAnalysis | dict): From Intent Classifier
            - mode (str | LearningMode): Active learning mode
            - learner_profile (LearnerProfile | dict): Learner data
            - retrieved_context (str): Concatenated RAG context
            - sources (List[str]): Retrieved source URLs
            - eval_scores (Dict[str, float]): Optional pre-existing eval scores

        Returns:
            PeCARoutput with the final response and full pipeline metadata.
        """
        query: str = state.get("query", "")
        mode = self._coerce_mode(state.get("mode", LearningMode.RESEARCH))
        learner = self._coerce_learner(state.get("learner_profile", {}))
        intent = self._coerce_intent(state.get("intent_analysis", {}))
        retrieved_context: str = state.get("retrieved_context", "")
        sources: List[str] = state.get("sources", [])
        eval_scores: Dict[str, float] = state.get("eval_scores", {})

        logger.info("PeCAR pipeline start: mode=%s, query_len=%d", mode, len(query))

        # ---- Stage 1: Intent-Aware Strategy Selection ----
        strategy = self.iass.select(intent=intent, mode=mode, learner=learner)
        logger.info("Stage 1 complete: %d techniques selected", len(strategy.techniques))

        # ---- Stage 2: Adaptive Reasoning Depth ----
        depth_score, num_steps = self.ardc.compute(intent=intent, learner=learner, mode=mode)
        logger.info("Stage 2 complete: depth_score=%.4f -> %d steps", depth_score, num_steps)

        # ---- Stage 3: Retrieval-Grounded CoT ----
        system_prompt = prompts.SYSTEM_TEMPLATES[mode]
        reasoning_steps: List[ReasoningStep] = []

        if strategy.use_retrieval_grounding and retrieved_context:
            try:
                reasoning_steps = await self.rg_cot.generate_and_verify_steps(
                    query=query,
                    retrieved_context=retrieved_context,
                    sources=sources,
                    num_steps=num_steps,
                    system_prompt=system_prompt,
                    learner=learner,
                )
                logger.info(
                    "Stage 3 complete: %d steps, %d verified",
                    len(reasoning_steps),
                    sum(1 for s in reasoning_steps if s.verification_status == VerificationStatus.VERIFIED),
                )
            except Exception as exc:
                logger.error("Stage 3 (RG-CoT) failed: %s — continuing without verified steps", exc)
        else:
            logger.info("Stage 3 skipped: retrieval grounding not required or no context available")

        # ---- Stage 4: Pedagogical Multi-Path Synthesis ----
        paths: List[ReasoningPath] = []
        scored_paths: List[ReasoningPath] = []
        merged_response = ""

        try:
            paths = await self.pmps.generate_paths(
                query=query,
                retrieved_context=retrieved_context,
                strategy_profile=strategy,
                learner=learner,
                num_steps=num_steps,
                system_prompt=system_prompt,
            )
            scored_paths = self.pmps.score_paths(paths, retrieved_context, learner)
            merged_response = await self.pmps.merge_top_paths(scored_paths, learner)
            logger.info(
                "Stage 4 complete: %d paths scored, top PCS=%.4f",
                len(scored_paths),
                scored_paths[0].score.composite_score if scored_paths and scored_paths[0].score else 0.0,
            )
        except Exception as exc:
            logger.error("Stage 4 (PMPS) failed: %s — using raw query-based fallback", exc)
            merged_response = await self._fallback_generate(query, retrieved_context, system_prompt)

        # ---- Stage 5: Quality-Feedback Prompt Refinement ----
        refinement_history: List[RefinementIteration] = []

        if eval_scores and strategy.max_refinement_iterations > 0:
            try:
                merged_response, refinement_history = await self.qfpr.refine(
                    response=merged_response,
                    eval_scores=eval_scores,
                    max_iterations=strategy.max_refinement_iterations,
                    system_prompt=system_prompt,
                )
                logger.info("Stage 5 complete: %d refinement iterations", len(refinement_history))
            except Exception as exc:
                logger.error("Stage 5 (QFPR) failed: %s — using unrefined response", exc)
        else:
            logger.info("Stage 5 skipped: no eval_scores provided or zero refinement budget")

        # ---- Stage 6: Mode-Specific Output Assembly ----
        try:
            final_response = await self.msoa.assemble(
                merged_response=merged_response,
                query=query,
                mode=mode,
                sources=sources,
                reasoning_steps=reasoning_steps,
                strategy_profile=strategy,
                learner=learner,
            )
            logger.info("Stage 6 complete: final response len=%d", len(final_response))
        except Exception as exc:
            logger.error("Stage 6 (MSOA) failed: %s — using merged response", exc)
            final_response = merged_response

        # ---- Assemble output ----
        path_scores = [p.score for p in scored_paths if p.score]

        return PeCARoutput(
            mode=mode,
            query=query,
            final_response=final_response,
            strategy_profile=strategy,
            reasoning_steps=reasoning_steps,
            paths_evaluated=path_scores,
            refinement_history=refinement_history,
            depth_score=depth_score,
            num_reasoning_steps=num_steps,
            sources_used=sources,
            metadata={
                "techniques_applied": [t.value for t in strategy.techniques],
                "num_paths": strategy.num_paths,
                "use_retrieval_grounding": strategy.use_retrieval_grounding,
                "persona": strategy.persona,
            },
        )

    async def _fallback_generate(
        self, query: str, context: str, system_prompt: str
    ) -> str:
        """Simple fallback: single LLM call if multi-path synthesis fails."""
        prompt = (
            f"Answer the following educational query thoroughly.\n\n"
            f"Context:\n{context[:2000]}\n\nQuery: {query}\n\nAnswer:"
        )
        try:
            return await self._llm(prompt=prompt, system=system_prompt)
        except Exception as exc:
            logger.error("Fallback generation also failed: %s", exc)
            return f"I encountered an error generating a response for: {query}"

    # ---- State coercion helpers ----

    @staticmethod
    def _coerce_mode(data: Any) -> LearningMode:
        if isinstance(data, LearningMode):
            return data
        try:
            return LearningMode(str(data))
        except ValueError:
            return LearningMode.RESEARCH

    @staticmethod
    def _coerce_learner(data: Any) -> LearnerProfile:
        if isinstance(data, LearnerProfile):
            return data
        if isinstance(data, dict):
            return LearnerProfile(**{k: v for k, v in data.items() if k in LearnerProfile.model_fields})
        return LearnerProfile()

    @staticmethod
    def _coerce_intent(data: Any) -> PecarIntentAnalysis:
        if isinstance(data, PecarIntentAnalysis):
            return data
        if isinstance(data, dict):
            return PecarIntentAnalysis(
                **{k: v for k, v in data.items() if k in PecarIntentAnalysis.model_fields}
            )
        return PecarIntentAnalysis(question_type="factual", complexity=0.5)
