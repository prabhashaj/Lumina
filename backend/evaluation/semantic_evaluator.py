"""
Semantic Evaluator - Evaluates factual accuracy, coherence,
concept coverage, and evidence support of LLM teaching responses.
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


class SemanticEvaluator:
    def __init__(self):
        self.llm = _build_evaluator_llm()

    async def evaluate_teaching_response(
        self,
        question: str,
        teaching_response: str,
        sources: List[str],
    ) -> Dict[str, float]:
        metrics: Dict[str, float] = {}
        metrics["factual_accuracy"] = await self._evaluate_accuracy(question, teaching_response, sources)
        metrics["logical_coherence"] = await self._evaluate_coherence(teaching_response)
        metrics["concept_coverage"] = await self._evaluate_coverage(question, teaching_response)
        metrics["misconception_handling"] = await self._evaluate_misconceptions(teaching_response)
        metrics["evidence_based"] = await self._evaluate_evidence_support(teaching_response, sources)
        metrics["overall_semantic_score"] = round(sum(metrics.values()) / len(metrics), 4)
        return metrics

    async def _call(self, prompt: str) -> dict:
        if self.llm is None or HumanMessage is None:
            return {}
        try:
            res = await self.llm.ainvoke([HumanMessage(content=prompt)])
            text = res.content.strip().strip("```json").strip("```").strip()
            return json.loads(text)
        except Exception as exc:
            logger.warning("SemanticEvaluator LLM parse error: %s", exc)
            return {}

    async def _evaluate_accuracy(self, question: str, response: str, sources: List[str]) -> float:
        if self.llm is None:
            return self._heuristic_accuracy(question, response, sources)
        sources_text = "\n".join(sources[:3]) if sources else "No sources provided."
        prompt = f"""You are a fact-checking expert.

Question: {question}
Teaching Response: {response}
Source Materials: {sources_text}

Check the teaching response for:
1. Incorrect statements or hallucinations
2. Direct contradictions with source material
3. Unsupported or invented facts

Rate accuracy 0.0-1.0 where:
  1.0  = all facts verified, no errors
  0.8  = minor inaccuracies or unsupported claims
  0.6  = some factual errors but core message correct
  <0.6 = major errors or hallucinations

Respond with ONLY valid JSON (no markdown):
{{"accuracy_score": 0.85, "errors": [], "reasoning": "..."}}"""
        data = await self._call(prompt)
        return float(data.get("accuracy_score", 0.5))

    async def _evaluate_coherence(self, response: str) -> float:
        if self.llm is None:
            return self._heuristic_coherence(response)
        prompt = f"""Evaluate the logical coherence and flow of this teaching explanation:

{response}

Check:
1. Logical connections between ideas
2. Clear progression from simple to complex
3. Consistent terminology throughout
4. No internal contradictions
5. Clear cause-effect relationships

Rate coherence 0.0-1.0.

Respond with ONLY valid JSON (no markdown):
{{"coherence_score": 0.9, "issues": [], "reasoning": "..."}}"""
        data = await self._call(prompt)
        return float(data.get("coherence_score", 0.5))

    async def _evaluate_coverage(self, question: str, response: str) -> float:
        if self.llm is None:
            return self._heuristic_coverage(question, response)
        prompt = f"""Evaluate concept coverage in this teaching response.

Question: {question}
Response: {response}

Identify:
1. Key concepts the response SHOULD address
2. Which are present
3. Important concepts MISSING

coverage_score = concepts_covered / total_expected_concepts  (0.0-1.0)

Respond with ONLY valid JSON (no markdown):
{{"coverage_score": 0.85, "covered": [], "missing": [], "reasoning": "..."}}"""
        data = await self._call(prompt)
        return float(data.get("coverage_score", 0.5))

    async def _evaluate_misconceptions(self, response: str) -> float:
        if self.llm is None:
            return self._heuristic_misconceptions(response)
        prompt = f"""Review this teaching response for handling of common misconceptions:

{response}

Does the response:
1. Identify and clarify common mistakes about the topic?
2. Explain why misconceptions arise?
3. Provide evidence against wrong ideas?
4. Prevent students from learning incorrect concepts?

If the topic has no well-known misconceptions, score 0.7 (neutral).

Rate 0.0-1.0.

Respond with ONLY valid JSON (no markdown):
{{"misconception_score": 0.8, "addressed": [], "missed": [], "reasoning": "..."}}"""
        data = await self._call(prompt)
        return float(data.get("misconception_score", 0.5))

    async def _evaluate_evidence_support(self, response: str, sources: List[str]) -> float:
        if self.llm is None:
            return self._heuristic_evidence_support(response, sources)
        sources_text = "\n".join(sources[:3]) if sources else "No sources provided."
        prompt = f"""Evaluate evidence support in this teaching response.

Response: {response}
Available Sources: {sources_text}

Check:
1. Are major claims referenced or sourced?
2. Are statistics cited with evidence?
3. Is the evidence recent and credible?
4. Are sources diverse?

Rate evidence support 0.0-1.0.

Respond with ONLY valid JSON (no markdown):
{{"evidence_score": 0.9, "unsupported_claims": [], "credibility": "high", "reasoning": "..."}}"""
        data = await self._call(prompt)
        return float(data.get("evidence_score", 0.5))

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z0-9\\-]+", text.lower())

    def _keyword_set(self, text: str) -> set[str]:
        stopwords = {
            "the", "and", "for", "with", "this", "that", "from", "into", "your",
            "their", "have", "will", "would", "about", "what", "when", "where",
            "which", "while", "does", "work", "works", "using", "used", "need",
            "also", "than", "then", "them", "they", "there", "because", "through",
            "response", "question", "teaching", "explanation",
        }
        return {t for t in self._tokenize(text) if len(t) > 3 and t not in stopwords}

    def _heuristic_accuracy(self, question: str, response: str, sources: List[str]) -> float:
        response_text = response.lower()
        penalty = 0.0
        contradiction_signals = [
            ("photosynthesis", ["mitochondria", "do not need sunlight", "without sunlight"]),
            ("chlorophyll", ["animal cell", "mitochondria"]),
        ]
        for topic, bad_patterns in contradiction_signals:
            if topic in f"{question} {response_text}":
                for pattern in bad_patterns:
                    if pattern in response_text:
                        penalty += 0.25
        if sources:
            source_terms = self._keyword_set(" ".join(sources))
            response_terms = self._keyword_set(response)
            overlap = len(source_terms & response_terms) / max(len(source_terms), 1)
            base = 0.45 + min(0.45, overlap)
        else:
            base = 0.65 if len(self._tokenize(response)) >= 40 else 0.5
        return round(max(0.0, min(1.0, base - penalty)), 4)

    def _heuristic_coherence(self, response: str) -> float:
        sentences = [s.strip() for s in re.split(r"[.!?]+", response) if s.strip()]
        if not sentences:
            return 0.3
        transition_count = len(re.findall(r"\b(first|second|next|then|therefore|because|so|finally|for example)\b", response, re.I))
        variety = len({s[:25].lower() for s in sentences}) / len(sentences)
        score = 0.45 + min(0.25, transition_count * 0.05) + min(0.2, variety * 0.2)
        if len(sentences) >= 3:
            score += 0.1
        return round(max(0.0, min(1.0, score)), 4)

    def _heuristic_coverage(self, question: str, response: str) -> float:
        expected = self._keyword_set(question)
        if not expected:
            expected = set(list(self._keyword_set(response))[:5])
        covered = len(expected & self._keyword_set(response))
        return round(max(0.0, min(1.0, covered / max(len(expected), 1))), 4)

    def _heuristic_misconceptions(self, response: str) -> float:
        text = response.lower()
        score = 0.7
        if re.search(r"\b(common mistake|misconception|people often think|not to be confused)\b", text):
            score += 0.2
        if re.search(r"\bhowever|but|actually|instead\b", text):
            score += 0.1
        return round(min(1.0, score), 4)

    def _heuristic_evidence_support(self, response: str, sources: List[str]) -> float:
        if not sources:
            return 0.35 if len(self._tokenize(response)) > 80 else 0.2
        source_overlap = len(self._keyword_set(response) & self._keyword_set(" ".join(sources)))
        citation_signals = len(re.findall(r"https?://|\bsource\b|\bstudy\b|\bresearch\b|\baccording to\b", response, re.I))
        score = 0.5 + min(0.3, source_overlap * 0.03) + min(0.2, citation_signals * 0.05)
        return round(max(0.0, min(1.0, score)), 4)


async def _demo() -> None:
    evaluator = SemanticEvaluator()
    result = await evaluator.evaluate_teaching_response(
        question="How does photosynthesis work?",
        teaching_response="Photosynthesis happens in chloroplasts where chlorophyll absorbs light. Plants use sunlight, water, and carbon dioxide to build glucose and release oxygen.",
        sources=[
            "Photosynthesis occurs in chloroplasts and depends on light energy.",
            "Plants convert water and carbon dioxide into glucose and oxygen.",
        ],
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(_demo())
