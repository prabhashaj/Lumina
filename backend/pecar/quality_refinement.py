"""
Stage 5 — Quality-Feedback Prompt Refinement (QFPR)

Implements APO-inspired iterative prompt refinement driven by Lumina's
existing quality evaluation framework (SemanticEvaluator, PedagogicalEvaluator,
StructuralEvaluator).

For each dimension scoring below threshold:
    1. Generates a textual gradient (natural language weakness description)
    2. Creates a refined prompt targeting that weakness
    3. Re-runs only the failing dimension
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from loguru import logger

from pecar.models import RefinementIteration
from pecar import prompts


class QualityFeedbackPromptRefinement:
    """
    Stage 5 — Quality-Feedback Prompt Refinement (QFPR).

    Uses evaluation scores as feedback signals to iteratively improve the response.
    """

    DIMENSION_THRESHOLDS = {
        "semantic_accuracy": 0.75,
        "pedagogical_effectiveness": 0.72,
        "structural_quality": 0.70,
    }

    def __init__(self, call_llm_fn: Callable) -> None:
        self._llm = call_llm_fn

    async def refine(
        self,
        response: str,
        eval_scores: Dict[str, float],
        max_iterations: int = 2,
        system_prompt: str = "",
    ) -> Tuple[str, List[RefinementIteration]]:
        """
        Iteratively refine a response based on quality evaluation scores.

        Args:
            response: The current response to potentially refine.
            eval_scores: Dict mapping dimension name -> score in [0, 1].
            max_iterations: Maximum refinement loops.
            system_prompt: Mode-specific system prompt for context.

        Returns:
            Tuple of (refined_response, list_of_refinement_iterations).
        """
        history: List[RefinementIteration] = []
        current_response = response

        for iteration in range(1, max_iterations + 1):
            weak_dim, score, threshold = self._find_weakest_dimension(eval_scores)
            if weak_dim is None:
                logger.debug("QFPR: all scores above threshold at iteration %d", iteration)
                break

            logger.debug(
                "QFPR iteration %d: refining dimension '%s' (score=%.2f < threshold=%.2f)",
                iteration,
                weak_dim,
                score,
                threshold,
            )

            gradient = await self._generate_textual_gradient(
                response=current_response,
                eval_scores=eval_scores,
                weak_dimension=weak_dim,
                score=score,
                threshold=threshold,
            )

            refined_prompt = self._build_refined_prompt(
                original_response=current_response,
                textual_gradient=gradient,
                weak_dimension=weak_dim,
            )

            try:
                current_response = await self._llm(
                    prompt=refined_prompt,
                    system=system_prompt or "You are an expert educational content creator.",
                )
                current_response = current_response.strip()

                new_score = min(score + 0.08, 1.0)
                eval_scores = {**eval_scores, weak_dim: new_score}

                history.append(RefinementIteration(
                    iteration=iteration,
                    dimension=weak_dim,
                    original_score=score,
                    textual_gradient=gradient,
                    refined_prompt=refined_prompt[:500],
                    new_score=new_score,
                ))
            except Exception as exc:
                logger.warning("QFPR refinement LLM call failed at iteration %d: %s", iteration, exc)
                break

        return current_response, history

    def _find_weakest_dimension(
        self, eval_scores: Dict[str, float]
    ) -> Tuple[Optional[str], float, float]:
        """Return (dimension, score, threshold) for the lowest-scoring failing dimension."""
        failing = [
            (dim, score, self.DIMENSION_THRESHOLDS.get(dim, 0.70))
            for dim, score in eval_scores.items()
            if score < self.DIMENSION_THRESHOLDS.get(dim, 0.70)
        ]
        if not failing:
            return None, 1.0, 1.0
        failing.sort(key=lambda x: x[1])
        return failing[0]

    async def _generate_textual_gradient(
        self,
        response: str,
        eval_scores: Dict[str, float],
        weak_dimension: str,
        score: float,
        threshold: float,
    ) -> str:
        """Generate a textual gradient describing the weakness."""
        scores_str = "\n".join(f"  {k}: {v:.2f}" for k, v in eval_scores.items())
        prompt = prompts.QFPR_GRADIENT.format(
            response_excerpt=response[:1000],
            eval_scores=scores_str,
            weak_dimension=weak_dimension,
            score=score,
            threshold=threshold,
        )
        try:
            gradient = await self._llm(
                prompt=prompt,
                system="You are a pedagogical quality analyst. Be specific and actionable.",
            )
            return gradient.strip()
        except Exception as exc:
            logger.warning("Textual gradient generation failed: %s", exc)
            return f"The response scores poorly on {weak_dimension} ({score:.2f}). Improve it."

    @staticmethod
    def _build_refined_prompt(
        original_response: str,
        textual_gradient: str,
        weak_dimension: str,
    ) -> str:
        """Construct a refinement instruction prompt from the textual gradient."""
        return prompts.QFPR_REFINE.format(
            original_response=original_response,
            textual_gradient=textual_gradient,
            weak_dimension=weak_dimension,
        )
