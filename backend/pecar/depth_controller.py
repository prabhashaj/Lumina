"""
Stage 2 — Adaptive Reasoning Depth Controller (ARDC)

Implements the depth formula:
    D(q, l, m) = alpha * C(q) + beta * (1 - L(l)) + gamma * W(m)

Maps the resulting depth_score to a concrete number of reasoning steps.
"""

from __future__ import annotations

from typing import Optional, Tuple

from loguru import logger

from pecar.models import (
    DepthConfig,
    LearnerProfile,
    LearningMode,
    PecarIntentAnalysis,
)


class AdaptiveReasoningDepthController:
    """
    Stage 2 — Adaptive Reasoning Depth Controller (ARDC).

    Computes a normalised depth score and maps it to a step count.
    """

    def __init__(self, config: Optional[DepthConfig] = None) -> None:
        self.cfg = config or DepthConfig()

    def compute_depth_score(
        self,
        intent: PecarIntentAnalysis,
        learner: LearnerProfile,
        mode: LearningMode,
    ) -> float:
        """
        Compute the normalised depth score D in [0, 1].
        """
        c_q = intent.complexity
        l_l = learner.knowledge_level
        w_m = self.cfg.mode_weights.get(mode, 0.6)

        score = self.cfg.alpha * c_q + self.cfg.beta * (1.0 - l_l) + self.cfg.gamma * w_m
        return round(min(max(score, 0.0), 1.0), 4)

    def map_to_steps(self, depth_score: float) -> int:
        """
        Map a depth score to a concrete reasoning step count.
        """
        if depth_score < self.cfg.medium_threshold:
            lo, hi = self.cfg.steps_low
        elif depth_score < self.cfg.high_threshold:
            lo, hi = self.cfg.steps_medium
        else:
            lo, hi = self.cfg.steps_high

        if depth_score < self.cfg.medium_threshold:
            fraction = depth_score / self.cfg.medium_threshold if self.cfg.medium_threshold else 0
        elif depth_score < self.cfg.high_threshold:
            denom = self.cfg.high_threshold - self.cfg.medium_threshold
            fraction = (depth_score - self.cfg.medium_threshold) / denom if denom else 0
        else:
            denom = 1.0 - self.cfg.high_threshold
            fraction = (depth_score - self.cfg.high_threshold) / denom if denom else 0

        steps = lo + round(fraction * (hi - lo))
        return int(min(max(steps, lo), hi))

    def compute(
        self,
        intent: PecarIntentAnalysis,
        learner: LearnerProfile,
        mode: LearningMode,
    ) -> Tuple[float, int]:
        """Convenience method: returns (depth_score, num_steps)."""
        score = self.compute_depth_score(intent, learner, mode)
        steps = self.map_to_steps(score)
        logger.debug("ARDC: depth_score=%.4f -> %d steps (mode=%s)", score, steps, mode)
        return score, steps
