"""
Semantic Evaluator - Evaluates factual accuracy, coherence,
concept coverage, and evidence support of LLM teaching responses.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))          # backend/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))   # workspace root

import json
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from loguru import logger

from config.settings import settings


def _build_evaluator_llm() -> ChatOpenAI:
    """Build a deterministic LLM for evaluation using available API keys."""
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


class SemanticEvaluator:
    """
    Evaluates factual accuracy, logical coherence, concept coverage,
    misconception handling, and evidence support of LLM outputs.
    """

    def __init__(self):
        self.llm = _build_evaluator_llm()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def evaluate_teaching_response(
        self,
        question: str,
        teaching_response: str,
        sources: List[str],
    ) -> Dict[str, float]:
        """
        Run all semantic checks and return a metrics dict with scores 0-1.

        Keys returned:
            factual_accuracy, logical_coherence, concept_coverage,
            misconception_handling, evidence_based, overall_semantic_score
        """
        metrics: Dict[str, float] = {}

        metrics["factual_accuracy"] = await self._evaluate_accuracy(
            question, teaching_response, sources
        )
        metrics["logical_coherence"] = await self._evaluate_coherence(teaching_response)
        metrics["concept_coverage"] = await self._evaluate_coverage(
            question, teaching_response
        )
        metrics["misconception_handling"] = await self._evaluate_misconceptions(
            teaching_response
        )
        metrics["evidence_based"] = await self._evaluate_evidence_support(
            teaching_response, sources
        )

        metrics["overall_semantic_score"] = round(
            sum(v for k, v in metrics.items()) / len(metrics), 4
        )
        return metrics

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _call(self, prompt: str) -> dict:
        """Call LLM and parse JSON response, with safe fallback."""
        try:
            res = await self.llm.ainvoke([HumanMessage(content=prompt)])
            # Strip markdown fences if present
            text = res.content.strip().strip("```json").strip("```").strip()
            return json.loads(text)
        except Exception as exc:
            logger.warning(f"SemanticEvaluator LLM parse error: {exc}")
            return {}

    async def _evaluate_accuracy(
        self, question: str, response: str, sources: List[str]
    ) -> float:
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

    async def _evaluate_evidence_support(
        self, response: str, sources: List[str]
    ) -> float:
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
