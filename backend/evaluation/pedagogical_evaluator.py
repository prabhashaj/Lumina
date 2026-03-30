"""
Pedagogical Evaluator - Evaluates teaching quality, instructional
effectiveness, analogy quality, scaffolding, and engagement.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
except ImportError:
    ChatOpenAI = None
    HumanMessage = None

try:
    from config.settings import settings
except Exception:
    settings = None


logger = logging.getLogger(__name__)


def _build_evaluator_llm() -> Optional[Any]:
    if ChatOpenAI is None or HumanMessage is None or settings is None:
        return None
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
    return None


class PedagogicalEvaluator:
    def __init__(self):
        self.llm = _build_evaluator_llm()

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
        metrics: Dict[str, float] = {}
        metrics["clarity"] = self._evaluate_clarity(explanation, difficulty_level)
        metrics["analogy_quality"] = await self._evaluate_analogy(question, analogy)
        metrics["example_quality"] = await self._evaluate_examples(question, examples)
        metrics["practice_quality"] = await self._evaluate_practice_questions(question, practice_questions)
        metrics["scaffolding"] = await self._evaluate_scaffolding(tldr, explanation)
        metrics["engagement"] = self._evaluate_engagement(explanation)
        metrics["difficulty_match"] = self._evaluate_difficulty_match(explanation, difficulty_level)
        metrics["overall_pedagogical_score"] = round(sum(metrics.values()) / len(metrics), 4)
        return metrics

    async def _call(self, prompt: str) -> dict:
        if self.llm is None or HumanMessage is None:
            return {}
        try:
            res = await self.llm.ainvoke([HumanMessage(content=prompt)])
            text = res.content.strip().strip("```json").strip("```").strip()
            return json.loads(text)
        except Exception as exc:
            logger.warning("PedagogicalEvaluator LLM parse error: %s", exc)
            return {}

    def _evaluate_clarity(self, text: str, target_difficulty: str) -> float:
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if not sentences:
            return 0.5
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        targets = {"beginner": 12, "intermediate": 17, "advanced": 22}
        target = targets.get(target_difficulty, 17)
        diff = abs(avg_words - target)
        clarity = max(0.0, 1.0 - (diff / target))
        return round(min(1.0, clarity), 4)

    async def _evaluate_analogy(self, topic: str, analogy: str) -> float:
        if not analogy or len(analogy.split()) < 5:
            return 0.2
        if self.llm is None:
            return self._heuristic_analogy(analogy)
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
        diversity_score = min(1.0, len(examples) / 3)
        if self.llm is None:
            example_score = self._heuristic_examples(examples)
            return round((example_score * 0.7) + (diversity_score * 0.3), 4)
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

    async def _evaluate_practice_questions(self, topic: str, questions: List[str]) -> float:
        if not questions:
            return 0.0
        if self.llm is None:
            return self._heuristic_practice_questions(questions)
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
        if self.llm is None:
            return self._heuristic_scaffolding(tldr, detailed)
        prompt = f"""Evaluate the scaffolding (simple to complex progression) in this teaching content.

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
        score = 0.0
        if len(re.findall(r"\?", text)) >= 1:
            score += 0.2
        if re.search(r"\b(?:Imagine|Consider|Try|Think about|Notice|Remember)\b", text, re.I):
            score += 0.2
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if sentences:
            lengths = [len(s.split()) for s in sentences]
            if max(lengths, default=0) > min(lengths, default=0) * 2:
                score += 0.2
        if re.search(r"\*\*.*?\*\*|__.*?__", text):
            score += 0.2
        if re.search(r"\b(?:like|similar to|just as|think of it as|analogous)\b", text, re.I):
            score += 0.2
        return round(min(1.0, score), 4)

    def _evaluate_difficulty_match(self, text: str, target: str) -> float:
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if not sentences:
            return 0.5
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        targets = {"beginner": 12, "intermediate": 17, "advanced": 22}
        target_len = targets.get(target, 17)
        diff = abs(avg_words - target_len)
        return round(max(0.0, 1.0 - (diff / target_len)), 4)

    def _heuristic_analogy(self, analogy: str) -> float:
        score = 0.4
        if re.search(r"\b(like|as if|similar to|think of|just as)\b", analogy, re.I):
            score += 0.25
        if len(analogy.split()) >= 12:
            score += 0.2
        if "," in analogy or "because" in analogy.lower():
            score += 0.1
        return round(min(1.0, score), 4)

    def _heuristic_examples(self, examples: List[str]) -> float:
        lengths = [len(e.split()) for e in examples]
        concrete_bonus = sum(1 for e in examples if re.search(r"\b(for example|such as|like|when|in everyday life)\b", e, re.I))
        score = 0.45
        if lengths and min(lengths) >= 6:
            score += 0.2
        if lengths and max(lengths) - min(lengths) >= 4:
            score += 0.1
        score += min(0.25, concrete_bonus * 0.08)
        return round(min(1.0, score), 4)

    def _heuristic_practice_questions(self, questions: List[str]) -> float:
        score = 0.4
        varied_starters = len({q.split()[0].lower() for q in questions if q.split()})
        if all(q.strip().endswith("?") for q in questions):
            score += 0.15
        if varied_starters >= 2:
            score += 0.2
        if len(questions) >= 3:
            score += 0.15
        if any(re.search(r"\bcompare|explain why|how\b", q, re.I) for q in questions):
            score += 0.1
        return round(min(1.0, score), 4)

    def _heuristic_scaffolding(self, tldr: str, detailed: str) -> float:
        tldr_words = len(tldr.split())
        detailed_words = len(detailed.split())
        if detailed_words <= tldr_words:
            return 0.35
        ratio = detailed_words / max(tldr_words, 1)
        score = 0.45 + min(0.35, ratio / 10)
        if re.search(r"## |^\d+\.|\*\*", detailed, re.M):
            score += 0.15
        return round(min(1.0, score), 4)


async def _demo() -> None:
    evaluator = PedagogicalEvaluator()
    result = await evaluator.evaluate_teaching_quality(
        question="How does photosynthesis work?",
        difficulty_level="intermediate",
        tldr="Plants use sunlight to turn water and carbon dioxide into glucose and oxygen.",
        explanation="Imagine a plant as a tiny food factory. First, chlorophyll captures light. Then the plant uses that energy to rearrange water and carbon dioxide into glucose. This process also releases oxygen, which is why photosynthesis matters for life on Earth.",
        analogy="Think of a leaf like a solar-powered kitchen that cooks sugar from simple ingredients.",
        examples=[
            "A plant on a sunny windowsill grows faster than one kept in the dark.",
            "Aquatic plants release visible oxygen bubbles when exposed to light.",
        ],
        practice_questions=[
            "Why does photosynthesis need sunlight?",
            "How are water and carbon dioxide used during photosynthesis?",
            "Compare photosynthesis with how animals obtain energy.",
        ],
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(_demo())
