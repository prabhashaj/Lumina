"""
Structural Evaluator - Evaluates format, completeness, markdown quality,
TL;DR quality, response length, and citation completeness.
No external LLM calls — purely rule-based and heuristic.
"""
import re
import json
from typing import Dict, List, Any


class StructuralEvaluator:
    """
    Evaluates structure and format of LLM teaching responses.

    Metrics:
        completeness, tldr_quality, length_appropriateness,
        json_validity, markdown_quality, citation_quality,
        overall_structural_score
    """

    # Required top-level fields in a teaching response
    REQUIRED_FIELDS = ["tldr", "explanation", "analogy", "practice_questions", "sources"]

    async def evaluate_teaching_response_structure(
        self, response_dict: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Check all structural dimensions and return scores 0-1.
        """
        metrics: Dict[str, float] = {}

        # 1. Completeness — are all required fields present and non-empty?
        present = sum(
            1 for f in self.REQUIRED_FIELDS if response_dict.get(f) not in (None, "", [], {})
        )
        metrics["completeness"] = round(present / len(self.REQUIRED_FIELDS), 4)

        # 2. TL;DR quality
        metrics["tldr_quality"] = self._evaluate_tldr(response_dict.get("tldr", ""))

        # 3. Explanation length
        metrics["length_appropriateness"] = self._evaluate_length(
            response_dict.get("explanation", "")
        )

        # 4. JSON validity (only when response is a raw string)
        raw = response_dict.get("_raw_response")
        if isinstance(raw, str):
            metrics["json_validity"] = 1.0 if self._is_valid_json(raw) else 0.0
        else:
            metrics["json_validity"] = 1.0  # Already parsed → valid

        # 5. Markdown formatting
        metrics["markdown_quality"] = self._evaluate_markdown(
            response_dict.get("explanation", "")
        )

        # 6. Citation quality
        metrics["citation_quality"] = self._evaluate_citations(
            response_dict.get("sources", [])
        )

        metrics["overall_structural_score"] = round(
            sum(v for k, v in metrics.items()) / len(metrics), 4
        )
        return metrics

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _evaluate_tldr(self, tldr: str) -> float:
        """TL;DR should be brief (15-50 words) and non-empty."""
        if not tldr:
            return 0.0
        word_count = len(tldr.split())
        if 15 <= word_count <= 50:
            return 1.0
        elif 10 <= word_count <= 75:
            return 0.8
        elif 5 <= word_count <= 150:
            return 0.6
        return 0.3

    def _evaluate_length(self, text: str) -> float:
        """Teaching explanation should be 200-2500 words."""
        if not text:
            return 0.0
        word_count = len(text.split())
        if 300 <= word_count <= 2000:
            return 1.0
        elif 200 <= word_count <= 3000:
            return 0.8
        elif 100 <= word_count <= 4000:
            return 0.6
        return 0.3

    def _is_valid_json(self, text: str) -> bool:
        try:
            json.loads(text)
            return True
        except Exception:
            return False

    def _evaluate_markdown(self, text: str) -> float:
        """Check proper use of markdown formatting elements."""
        if not text:
            return 0.0

        checks = {
            "headers": bool(re.search(r"^#{1,6}\s", text, re.MULTILINE)),
            "lists": bool(re.search(r"^[\*\-\+]\s|\d+\.\s", text, re.MULTILINE)),
            "emphasis": bool(re.search(r"\*\*.*?\*\*|\*[^*]+?\*|__.*?__", text)),
            "code_or_math": bool(re.search(r"```|`[^`]+`|\$[^$]+\$", text)),
        }

        score = sum(1 for v in checks.values() if v) / len(checks)
        return round(score, 4)

    def _evaluate_citations(self, sources: List[Any]) -> float:
        """
        Each source is scored on presence of: url, title, snippet, domain.
        Average across first 5 sources.
        """
        if not sources:
            return 0.0

        field_weights = {"url": 0.35, "title": 0.30, "snippet": 0.20, "domain": 0.15}
        scores = []

        for src in sources[:5]:
            if not isinstance(src, dict):
                try:
                    src = src.dict()
                except Exception:
                    src = {}
            src_score = sum(
                w for field, w in field_weights.items() if src.get(field)
            )
            scores.append(src_score)

        return round(sum(scores) / len(scores), 4)
