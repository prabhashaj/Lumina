"""
Evaluation Dashboard - Aggregates all evaluators into a single
entry point and generates human-readable reports.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))          # backend/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))   # workspace root

import asyncio
from datetime import datetime
from typing import Dict, List, Any

from loguru import logger

from .semantic_evaluator import SemanticEvaluator
from .pedagogical_evaluator import PedagogicalEvaluator
from .structural_evaluator import StructuralEvaluator


# Minimum acceptable score per dimension
THRESHOLDS = {
    "semantic": 0.70,
    "pedagogical": 0.70,
    "structural": 0.65,
    "overall": 0.70,
}


class EvaluationDashboard:
    """
    Central hub that runs all three evaluators and produces
    aggregated quality reports for teaching responses.

    Usage:
        dashboard = EvaluationDashboard()
        result = await dashboard.evaluate(question, response_dict, sources, difficulty)
        print(dashboard.generate_report())
    """

    def __init__(self):
        self.semantic = SemanticEvaluator()
        self.pedagogical = PedagogicalEvaluator()
        self.structural = StructuralEvaluator()
        self._history: List[Dict] = []

    # ------------------------------------------------------------------
    # Main evaluation entry point
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        question: str,
        response_dict: Dict[str, Any],
        sources: List[str],
        difficulty_level: str = "intermediate",
    ) -> Dict[str, Any]:
        """
        Run all three evaluators concurrently and return a complete result dict.

        Args:
            question:         The student's original question
            response_dict:    The parsed teaching response (keys: tldr, explanation,
                              analogy, examples, practice_questions, sources)
            sources:          List of plain-text source strings used to generate the response
            difficulty_level: beginner | intermediate | advanced

        Returns:
            Dict with semantic_scores, pedagogical_scores, structural_scores,
            overall_score, pass (bool), timestamp, and a human-readable summary.
        """
        timestamp = datetime.now().isoformat()

        # Run LLM-based evaluators concurrently, structural is sync
        semantic_task = asyncio.create_task(
            self.semantic.evaluate_teaching_response(
                question,
                response_dict.get("explanation", ""),
                sources,
            )
        )
        pedagogical_task = asyncio.create_task(
            self.pedagogical.evaluate_teaching_quality(
                question,
                difficulty_level,
                response_dict.get("tldr", ""),
                response_dict.get("explanation", ""),
                response_dict.get("analogy", ""),
                response_dict.get("examples", []),
                response_dict.get("practice_questions", []),
            )
        )
        structural_task = asyncio.create_task(
            self.structural.evaluate_teaching_response_structure(response_dict)
        )

        semantic_scores, pedagogical_scores, structural_scores = await asyncio.gather(
            semantic_task, pedagogical_task, structural_task
        )

        # Weighted overall: semantic 40%, pedagogical 40%, structural 20%
        overall = round(
            semantic_scores["overall_semantic_score"] * 0.40
            + pedagogical_scores["overall_pedagogical_score"] * 0.40
            + structural_scores["overall_structural_score"] * 0.20,
            4,
        )

        passed = (
            semantic_scores["overall_semantic_score"] >= THRESHOLDS["semantic"]
            and pedagogical_scores["overall_pedagogical_score"] >= THRESHOLDS["pedagogical"]
            and structural_scores["overall_structural_score"] >= THRESHOLDS["structural"]
            and overall >= THRESHOLDS["overall"]
        )

        result = {
            "timestamp": timestamp,
            "question": question,
            "difficulty_level": difficulty_level,
            "semantic_scores": semantic_scores,
            "pedagogical_scores": pedagogical_scores,
            "structural_scores": structural_scores,
            "overall_score": overall,
            "pass": passed,
            "summary": self._build_summary(
                overall, passed, semantic_scores, pedagogical_scores, structural_scores
            ),
        }

        self._history.append(result)
        logger.info(
            f"Evaluation complete | overall={overall:.2f} | pass={passed} | "
            f"question='{question[:60]}...'"
        )
        return result

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(self) -> str:
        """Print a human-readable summary of all evaluations so far."""
        if not self._history:
            return "No evaluations yet."

        n = len(self._history)
        passed = sum(1 for e in self._history if e["pass"])

        avg = lambda key_path: sum(
            self._nested_get(e, key_path) for e in self._history
        ) / n

        lines = [
            "",
            "=" * 52,
            "      LLM OUTPUT EVALUATION REPORT",
            "=" * 52,
            f"  Total Evaluations : {n}",
            f"  Pass Rate         : {(passed/n)*100:.1f}%  ({passed}/{n})",
            "",
            "  Average Scores (0-1 scale):",
            f"    Semantic Accuracy   : {avg('semantic_scores.overall_semantic_score'):.3f}  (weight 40%)",
            f"      ├─ Factual Accuracy     : {avg('semantic_scores.factual_accuracy'):.3f}",
            f"      ├─ Logical Coherence    : {avg('semantic_scores.logical_coherence'):.3f}",
            f"      ├─ Concept Coverage     : {avg('semantic_scores.concept_coverage'):.3f}",
            f"      ├─ Misconception Handle : {avg('semantic_scores.misconception_handling'):.3f}",
            f"      └─ Evidence-Based       : {avg('semantic_scores.evidence_based'):.3f}",
            "",
            f"    Pedagogical Quality : {avg('pedagogical_scores.overall_pedagogical_score'):.3f}  (weight 40%)",
            f"      ├─ Clarity             : {avg('pedagogical_scores.clarity'):.3f}",
            f"      ├─ Analogy Quality     : {avg('pedagogical_scores.analogy_quality'):.3f}",
            f"      ├─ Example Quality     : {avg('pedagogical_scores.example_quality'):.3f}",
            f"      ├─ Practice Questions  : {avg('pedagogical_scores.practice_quality'):.3f}",
            f"      ├─ Scaffolding         : {avg('pedagogical_scores.scaffolding'):.3f}",
            f"      ├─ Engagement          : {avg('pedagogical_scores.engagement'):.3f}",
            f"      └─ Difficulty Match    : {avg('pedagogical_scores.difficulty_match'):.3f}",
            "",
            f"    Structural Quality  : {avg('structural_scores.overall_structural_score'):.3f}  (weight 20%)",
            f"      ├─ Completeness        : {avg('structural_scores.completeness'):.3f}",
            f"      ├─ TL;DR Quality       : {avg('structural_scores.tldr_quality'):.3f}",
            f"      ├─ Length              : {avg('structural_scores.length_appropriateness'):.3f}",
            f"      ├─ Markdown Quality    : {avg('structural_scores.markdown_quality'):.3f}",
            f"      └─ Citation Quality    : {avg('structural_scores.citation_quality'):.3f}",
            "",
            f"  ── OVERALL SCORE : {avg('overall_score'):.3f} ──",
            "",
            "  Thresholds:",
            "    ✓ EXCELLENT : 0.85 – 1.00",
            "    ~ GOOD      : 0.70 – 0.84",
            "    ✗ NEEDS WORK: < 0.70",
            "=" * 52,
            "",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _nested_get(self, d: dict, dotted_key: str) -> float:
        keys = dotted_key.split(".")
        for k in keys:
            d = d.get(k, {})
        return float(d) if isinstance(d, (int, float)) else 0.0

    def _build_summary(
        self,
        overall: float,
        passed: bool,
        semantic: dict,
        pedagogical: dict,
        structural: dict,
    ) -> str:
        label = (
            "EXCELLENT" if overall >= 0.85
            else "GOOD" if overall >= 0.70
            else "NEEDS WORK"
        )
        weak = []
        for name, score in [
            ("Factual Accuracy", semantic.get("factual_accuracy", 0)),
            ("Concept Coverage", semantic.get("concept_coverage", 0)),
            ("Analogy Quality", pedagogical.get("analogy_quality", 0)),
            ("Practice Questions", pedagogical.get("practice_quality", 0)),
            ("Completeness", structural.get("completeness", 0)),
            ("Citations", structural.get("citation_quality", 0)),
        ]:
            if score < 0.65:
                weak.append(f"{name} ({score:.2f})")

        summary = f"Overall: {overall:.2f} [{label}] | Pass: {passed}"
        if weak:
            summary += f" | Weaknesses: {', '.join(weak)}"
        return summary
