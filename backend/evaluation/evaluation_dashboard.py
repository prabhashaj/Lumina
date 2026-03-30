"""
Evaluation Dashboard - Aggregates all evaluators into a single
entry point and generates human-readable reports.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

try:
    from .pedagogical_evaluator import PedagogicalEvaluator
    from .semantic_evaluator import SemanticEvaluator
    from .structural_evaluator import StructuralEvaluator
except ImportError:
    from pedagogical_evaluator import PedagogicalEvaluator
    from semantic_evaluator import SemanticEvaluator
    from structural_evaluator import StructuralEvaluator


logger = logging.getLogger(__name__)


THRESHOLDS = {
    "semantic": 0.70,
    "pedagogical": 0.70,
    "structural": 0.65,
    "overall": 0.70,
}


class EvaluationDashboard:
    def __init__(self):
        self.semantic = SemanticEvaluator()
        self.pedagogical = PedagogicalEvaluator()
        self.structural = StructuralEvaluator()
        self._history: List[Dict[str, Any]] = []

    async def evaluate(
        self,
        question: str,
        response_dict: Dict[str, Any],
        sources: List[str],
        difficulty_level: str = "intermediate",
    ) -> Dict[str, Any]:
        timestamp = datetime.now().isoformat()
        semantic_task = asyncio.create_task(
            self.semantic.evaluate_teaching_response(question, response_dict.get("explanation", ""), sources)
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
            "summary": self._build_summary(overall, passed, semantic_scores, pedagogical_scores, structural_scores),
        }
        self._history.append(result)
        logger.info(
            "Evaluation complete | overall=%.2f | pass=%s | question='%s...'",
            overall,
            passed,
            question[:60],
        )
        return result

    def generate_report(self) -> str:
        if not self._history:
            return "No evaluations yet."
        n = len(self._history)
        passed = sum(1 for e in self._history if e["pass"])

        def avg(key_path: str) -> float:
            return sum(self._nested_get(e, key_path) for e in self._history) / n

        lines = [
            "",
            "=" * 52,
            "      LLM OUTPUT EVALUATION REPORT",
            "=" * 52,
            f"  Total Evaluations : {n}",
            f"  Pass Rate         : {(passed / n) * 100:.1f}%  ({passed}/{n})",
            "",
            "  Average Scores (0-1 scale):",
            f"    Semantic Accuracy   : {avg('semantic_scores.overall_semantic_score'):.3f}  (weight 40%)",
            f"      |- Factual Accuracy     : {avg('semantic_scores.factual_accuracy'):.3f}",
            f"      |- Logical Coherence    : {avg('semantic_scores.logical_coherence'):.3f}",
            f"      |- Concept Coverage     : {avg('semantic_scores.concept_coverage'):.3f}",
            f"      |- Misconception Handle : {avg('semantic_scores.misconception_handling'):.3f}",
            f"      '- Evidence-Based       : {avg('semantic_scores.evidence_based'):.3f}",
            "",
            f"    Pedagogical Quality : {avg('pedagogical_scores.overall_pedagogical_score'):.3f}  (weight 40%)",
            f"      |- Clarity             : {avg('pedagogical_scores.clarity'):.3f}",
            f"      |- Analogy Quality     : {avg('pedagogical_scores.analogy_quality'):.3f}",
            f"      |- Example Quality     : {avg('pedagogical_scores.example_quality'):.3f}",
            f"      |- Practice Questions  : {avg('pedagogical_scores.practice_quality'):.3f}",
            f"      |- Scaffolding         : {avg('pedagogical_scores.scaffolding'):.3f}",
            f"      |- Engagement          : {avg('pedagogical_scores.engagement'):.3f}",
            f"      '- Difficulty Match    : {avg('pedagogical_scores.difficulty_match'):.3f}",
            "",
            f"    Structural Quality  : {avg('structural_scores.overall_structural_score'):.3f}  (weight 20%)",
            f"      |- Completeness        : {avg('structural_scores.completeness'):.3f}",
            f"      |- TL;DR Quality       : {avg('structural_scores.tldr_quality'):.3f}",
            f"      |- Length              : {avg('structural_scores.length_appropriateness'):.3f}",
            f"      |- Markdown Quality    : {avg('structural_scores.markdown_quality'):.3f}",
            f"      '- Citation Quality    : {avg('structural_scores.citation_quality'):.3f}",
            "",
            f"  -- OVERALL SCORE : {avg('overall_score'):.3f} --",
            "",
            "  Thresholds:",
            "    EXCELLENT : 0.85 - 1.00",
            "    GOOD      : 0.70 - 0.84",
            "    NEEDS WORK: < 0.70",
            "=" * 52,
            "",
        ]
        return "\n".join(lines)

    def _nested_get(self, d: dict, dotted_key: str) -> float:
        current: Any = d
        for key in dotted_key.split("."):
            if not isinstance(current, dict):
                return 0.0
            current = current.get(key, 0.0)
        return float(current) if isinstance(current, (int, float)) else 0.0

    def _build_summary(
        self,
        overall: float,
        passed: bool,
        semantic: dict,
        pedagogical: dict,
        structural: dict,
    ) -> str:
        label = "EXCELLENT" if overall >= 0.85 else "GOOD" if overall >= 0.70 else "NEEDS WORK"
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


async def _demo() -> None:
    dashboard = EvaluationDashboard()
    response = {
        "tldr": "Plants use sunlight to make glucose from water and carbon dioxide.",
        "explanation": "## Photosynthesis\n\nPlants capture sunlight using chlorophyll. They use that energy to convert water and carbon dioxide into glucose, and oxygen is released as a by-product.\n\n- Light absorption starts the process.\n- Chemical reactions store energy in glucose.\n",
        "analogy": "Think of a leaf like a solar-powered kitchen that makes sugar.",
        "examples": [
            "Houseplants lean toward bright windows because light powers growth.",
            "Pond plants make oxygen bubbles when placed in sunlight.",
        ],
        "practice_questions": [
            "Why is chlorophyll important?",
            "How do sunlight and water contribute to photosynthesis?",
        ],
        "sources": [
            {
                "title": "Biology reference",
                "url": "https://example.com/photosynthesis",
                "snippet": "Photosynthesis occurs in chloroplasts and produces glucose and oxygen.",
                "domain": "example.com",
            }
        ],
    }
    result = await dashboard.evaluate(
        question="How does photosynthesis work?",
        response_dict=response,
        sources=[response["sources"][0]["snippet"]],
        difficulty_level="intermediate",
    )
    print(result["summary"])
    print()
    print(dashboard.generate_report())


if __name__ == "__main__":
    asyncio.run(_demo())
