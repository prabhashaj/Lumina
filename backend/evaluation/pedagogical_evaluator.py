"""
Pedagogical Evaluator - Evaluates teaching quality, instructional
effectiveness, analogy quality, scaffolding, and engagement.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))          # backend/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))   # workspace root

import re
import json
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from loguru import logger

from config.settings import settings


def _build_evaluator_llm() -> ChatOpenAI:
    if settings.openrouter_api_key:
        return ChatOpenAI(
            model=settings.openrouter_model,
            temperature=0,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=1000,
        )
    if settings.mistral_api_key:
        return ChatOpenAI(
            model=settings.mistral_model,
            temperature=0,
            api_key=settings.mistral_api_key,
            base_url="https://api.mistral.ai/v1",
            max_tokens=1000,
        )
    raise ValueError("No API key found. Set OPENROUTER_API_KEY or MISTRAL_API_KEY.")


class PedagogicalEvaluator:
    """
    Evaluates teaching/instructional quality of LLM responses.

    Metrics:
        clarity, analogy_quality, example_quality, practice_quality,
        scaffolding, engagement, difficulty_match, overall_pedagogical_score
    """

    def __init__(self):
        self.llm = _build_evaluator_llm()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def evaluate_teaching_quality(
        self,
        question: str,
        difficulty_level: str,
        tldr: str,
        explanation: str,
        analogy: str,
        examples: List[str],
        practice_questions: List[str],
    ) -> Dict[str, float]:
        """
        Run all pedagogical checks and return metrics dict with scores 0-1.
        """
        metrics: Dict[str, float] = {}

        metrics["clarity"] = self._evaluate_clarity(explanation, difficulty_level)
        metrics["analogy_quality"] = await self._evaluate_analogy(question, analogy)
        metrics["example_quality"] = await self._evaluate_examples(question, examples)
        metrics["practice_quality"] = await self._evaluate_practice_questions(
            question, practice_questions
        )
        metrics["scaffolding"] = await self._evaluate_scaffolding(tldr, explanation)
        metrics["engagement"] = self._evaluate_engagement(explanation)
        metrics["difficulty_match"] = self._evaluate_difficulty_match(
            explanation, difficulty_level
        )

        metrics["overall_pedagogical_score"] = round(
            sum(v for k, v in metrics.items()) / len(metrics), 4
        )
        return metrics

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _call(self, prompt: str) -> dict:
        """Call LLM and parse JSON, with safe fallback."""
        try:
            res = await self.llm.ainvoke([HumanMessage(content=prompt)])
            text = res.content.strip().strip("```json").strip("```").strip()
            return json.loads(text)
        except Exception as exc:
            logger.warning(f"PedagogicalEvaluator LLM parse error: {exc}")
            return {}

    def _evaluate_clarity(self, text: str, target_difficulty: str) -> float:
        """
        Score clarity using heuristics (sentence length, passive voice, etc.)
        without requiring external readability libraries.
        """
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.5

        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)

        # Target average words-per-sentence per level
        targets = {"beginner": 12, "intermediate": 17, "advanced": 22}
        target = targets.get(target_difficulty, 17)

        diff = abs(avg_words - target)
        clarity = max(0.0, 1.0 - (diff / target))
        return round(min(1.0, clarity), 4)

    async def _evaluate_analogy(self, topic: str, analogy: str) -> float:
        if not analogy or len(analogy.split()) < 5:
            return 0.2

        prompt = f"""Evaluate the quality of this analogy for teaching "{topic}":

Analogy: {analogy}

A good analogy:
1. Maps a familiar concept to the unfamiliar topic
2. Highlights essential similarities
3. Avoids confusing differences
4. Is easy to visualise
5. Builds a clear mental model

Rate 0.0-1.0.

Respond with ONLY valid JSON (no markdown):
{{"analogy_score": 0.8, "strengths": [], "weaknesses": [], "reasoning": "..."}}"""
        data = await self._call(prompt)
        return float(data.get("analogy_score", 0.5))

    async def _evaluate_examples(self, topic: str, examples: List[str]) -> float:
        if not examples:
            return 0.0

        diversity_score = min(1.0, len(examples) / 3)  # 3+ examples = full diversity

        prompt = f"""Evaluate these examples for teaching "{topic}":

{chr(10).join(f"- {e}" for e in examples[:5])}

Check:
1. Are examples concrete and relatable?
2. Do they cover different aspects of the topic?
3. Are they at an appropriate difficulty?
4. Do they reinforce the core concept?
5. Are they memorable?

Rate 0.0-1.0.

Respond with ONLY valid JSON (no markdown):
{{"example_score": 0.85, "strengths": [], "improvements": [], "reasoning": "..."}}"""
        data = await self._call(prompt)
        example_score = float(data.get("example_score", 0.5))
        return round((example_score * 0.7) + (diversity_score * 0.3), 4)

    async def _evaluate_practice_questions(
        self, topic: str, questions: List[str]
    ) -> float:
        if not questions:
            return 0.0

        prompt = f"""Evaluate these practice questions for "{topic}":

{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions[:5]))}

Good practice questions:
1. Test understanding, not just recall
2. Increase gradually in difficulty
3. Cover different aspects of the topic
4. Are clear and unambiguous
5. Can be answered with the taught content

Rate 0.0-1.0.

Respond with ONLY valid JSON (no markdown):
{{"question_quality": 0.8, "strengths": [], "improvements": [], "reasoning": "..."}}"""
        data = await self._call(prompt)
        return float(data.get("question_quality", 0.5))

    async def _evaluate_scaffolding(self, tldr: str, detailed: str) -> float:
        if not tldr or not detailed:
            return 0.3

        prompt = f"""Evaluate the scaffolding (simple → complex progression) in this teaching content.

Summary (simple): {tldr}
Detailed Explanation (complex): {detailed}

Good scaffolding:
1. Summary is noticeably simpler than the detailed explanation
2. Concepts build progressively on each other
3. Simpler vocabulary is used first
4. Examples progress from basic to complex
5. Earlier points support later ones

Rate scaffolding 0.0-1.0.

Respond with ONLY valid JSON (no markdown):
{{"scaffolding_score": 0.85, "progression": "good", "reasoning": "..."}}"""
        data = await self._call(prompt)
        return float(data.get("scaffolding_score", 0.5))

    def _evaluate_engagement(self, text: str) -> float:
        """Heuristic engagement score based on rhetorical techniques."""
        score = 0.0

        # Rhetorical questions
        if len(re.findall(r"\?", text)) >= 1:
            score += 0.2

        # Interactive starters (Imagine, Consider, Think about, etc.)
        if re.search(r"\b(?:Imagine|Consider|Try|Think about|Notice|Remember)\b", text, re.I):
            score += 0.2

        # Sentence variety (mix of short and long sentences)
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if sentences:
            lengths = [len(s.split()) for s in sentences]
            if max(lengths, default=0) > min(lengths, default=0) * 2:
                score += 0.2

        # Emphasis / highlighting
        if re.search(r"\*\*.*?\*\*|__.*?__", text):
            score += 0.2

        # At least one analogy signal
        if re.search(r"\b(?:like|similar to|just as|think of it as|analogous)\b", text, re.I):
            score += 0.2

        return round(min(1.0, score), 4)

    def _evaluate_difficulty_match(self, text: str, target: str) -> float:
        """Rough difficulty match via average sentence length."""
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if not sentences:
            return 0.5

        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        # Expected avg words-per-sentence per level
        targets = {"beginner": 12, "intermediate": 17, "advanced": 22}
        target_len = targets.get(target, 17)

        diff = abs(avg_words - target_len)
        return round(max(0.0, 1.0 - (diff / target_len)), 4)
