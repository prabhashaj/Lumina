"""
Stage 4 — Pedagogical Multi-Path Synthesis (PMPS)

Generates N reasoning paths and evaluates each on three pedagogical
dimensions (accuracy, clarity, scaffolding). Fuses the best elements
of top-scoring paths into a single optimal response.

Pedagogical Consistency Score:
    PCS(path_i) = 0.40 * Accuracy(i) + 0.35 * Clarity(i) + 0.25 * Scaffolding(i)
"""

from __future__ import annotations

import asyncio
import re
from typing import Callable, List

from loguru import logger

from pecar.models import (
    LearnerProfile,
    PedagogicalScore,
    ReasoningPath,
    ReasoningStep,
    StrategyProfile,
)
from pecar import prompts


class PedagogicalMultiPathSynthesis:
    """
    Stage 4 — Pedagogical Multi-Path Synthesis (PMPS).

    Generates N reasoning paths, scores them on pedagogical quality,
    and fuses the best elements into a single optimal response.
    """

    ANALOGY_PATTERNS = [r"\blike\b", r"\banalog", r"\bsimilar to\b", r"\bjust as\b", r"\bthink of\b"]
    EXAMPLE_PATTERNS = [r"\bexample\b", r"\bfor instance\b", r"\bsuch as\b", r"\be\.g\.", r"\bconsider\b"]
    QUESTION_PATTERNS = [r"\?", r"\btry\b", r"\bpractice\b", r"\bexercise\b", r"\bcheck your\b"]

    def __init__(self, call_llm_fn: Callable) -> None:
        self._llm = call_llm_fn

    async def generate_paths(
        self,
        query: str,
        retrieved_context: str,
        strategy_profile: StrategyProfile,
        learner: LearnerProfile,
        num_steps: int,
        system_prompt: str,
    ) -> List[ReasoningPath]:
        """Generate ``strategy_profile.num_paths`` reasoning paths concurrently."""
        tasks = [
            self._generate_single_path(
                path_index=i,
                query=query,
                retrieved_context=retrieved_context,
                learner=learner,
                num_steps=num_steps,
                system_prompt=system_prompt,
                total_paths=strategy_profile.num_paths,
            )
            for i in range(strategy_profile.num_paths)
        ]
        paths = await asyncio.gather(*tasks, return_exceptions=True)

        valid_paths: List[ReasoningPath] = []
        for i, p in enumerate(paths):
            if isinstance(p, Exception):
                logger.warning("Path %d generation failed: %s", i, p)
            else:
                valid_paths.append(p)

        return valid_paths

    async def _generate_single_path(
        self,
        path_index: int,
        query: str,
        retrieved_context: str,
        learner: LearnerProfile,
        num_steps: int,
        system_prompt: str,
        total_paths: int,
    ) -> ReasoningPath:
        """Generate one complete reasoning path."""
        instruction = prompts.PATH_INSTRUCTIONS[
            path_index % len(prompts.PATH_INSTRUCTIONS)
        ]
        prompt = prompts.PMPS_GENERATE_PATH.format(
            system_prompt=system_prompt,
            query=query,
            retrieved_context=retrieved_context[:3000],
            knowledge_level=f"{learner.knowledge_level:.1f}",
            style=learner.preferred_style,
            path_index=path_index + 1,
            total_paths=total_paths,
            path_instruction=instruction,
            num_steps=num_steps,
        )

        raw = await self._llm(prompt=prompt, system=system_prompt)

        steps = self._parse_steps(raw)
        final_answer = self._parse_final_answer(raw)

        return ReasoningPath(
            index=path_index,
            steps=steps,
            final_answer=final_answer,
            raw_output=raw,
        )

    def score_paths(
        self,
        paths: List[ReasoningPath],
        retrieved_context: str,
        learner: LearnerProfile,
    ) -> List[ReasoningPath]:
        """Score each path on pedagogical dimensions and sort by PCS descending."""
        scored = []
        for path in paths:
            acc = self._score_factual_accuracy(path, retrieved_context)
            clarity = self._score_explanation_clarity(path, learner)
            scaffolding = self._score_scaffolding_completeness(path)

            path.score = PedagogicalScore.compute_composite(
                path_index=path.index,
                factual_accuracy=acc,
                explanation_clarity=clarity,
                scaffolding_completeness=scaffolding,
            )
            scored.append(path)

        scored.sort(key=lambda p: p.score.composite_score if p.score else 0.0, reverse=True)
        return scored

    async def merge_top_paths(
        self,
        scored_paths: List[ReasoningPath],
        learner: LearnerProfile,
        top_k: int = 2,
    ) -> str:
        """Fuse the best elements of the top-k scoring paths via LLM merge."""
        top = scored_paths[:top_k]

        if len(top) == 1:
            return top[0].final_answer or top[0].raw_output

        summaries = []
        for p in top:
            score_str = (
                f"accuracy={p.score.factual_accuracy:.2f}, "
                f"clarity={p.score.explanation_clarity:.2f}, "
                f"scaffolding={p.score.scaffolding_completeness:.2f}"
                if p.score else "unscored"
            )
            excerpt = (p.final_answer or p.raw_output)[:800]
            summaries.append(f"Path {p.index + 1} [{score_str}]:\n{excerpt}")

        prompt = prompts.PMPS_MERGE.format(
            top_paths_summary="\n\n---\n\n".join(summaries),
            knowledge_level=f"{learner.knowledge_level:.1f}",
            style=learner.preferred_style,
        )

        try:
            merged = await self._llm(prompt=prompt, system="You are an expert educational content editor.")
            return merged.strip()
        except Exception as exc:
            logger.warning("Path merge LLM call failed: %s — using top path", exc)
            return top[0].final_answer or top[0].raw_output

    # ---- Private scoring helpers ----

    def _score_factual_accuracy(self, path: ReasoningPath, retrieved_context: str) -> float:
        """Heuristic accuracy: fraction of key terms in path that appear in context."""
        if not retrieved_context:
            return 0.5

        path_text = path.raw_output.lower()
        context_text = retrieved_context.lower()

        words = re.findall(r"\b[a-z]{4,}\b", path_text)
        if not words:
            return 0.5

        matched = sum(1 for w in words if w in context_text)
        return round(min(matched / max(len(words), 1), 1.0), 4)

    def _score_explanation_clarity(self, path: ReasoningPath, learner: LearnerProfile) -> float:
        """Score clarity by sentence length distribution vs. learner level."""
        text = path.raw_output
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if not sentences:
            return 0.5

        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)

        ideal_min = 8 + learner.knowledge_level * 10
        ideal_max = 20 + learner.knowledge_level * 15

        if ideal_min <= avg_len <= ideal_max:
            return 1.0
        elif avg_len < ideal_min:
            return max(0.5, 1.0 - (ideal_min - avg_len) / ideal_min)
        else:
            return max(0.4, 1.0 - (avg_len - ideal_max) / ideal_max)

    def _score_scaffolding_completeness(self, path: ReasoningPath) -> float:
        """Score scaffolding: presence of analogies, examples, and practice questions."""
        text = path.raw_output.lower()

        has_analogy = any(re.search(p, text) for p in self.ANALOGY_PATTERNS)
        has_example = any(re.search(p, text) for p in self.EXAMPLE_PATTERNS)
        has_question = any(re.search(p, text) for p in self.QUESTION_PATTERNS)

        score = int(has_analogy) * 0.35 + int(has_example) * 0.40 + int(has_question) * 0.25
        return round(score, 4)

    def _parse_steps(self, raw: str) -> List[ReasoningStep]:
        """Extract numbered steps from raw LLM output."""
        step_pattern = re.compile(
            r"Step\s+(\d+):\s*(.*?)(?=Step\s+\d+:|Final Answer:|$)",
            re.DOTALL | re.IGNORECASE,
        )
        steps = []
        for match in step_pattern.finditer(raw):
            idx = int(match.group(1))
            content = match.group(2).strip()
            if content:
                steps.append(ReasoningStep(index=idx, content=content))
        return steps

    def _parse_final_answer(self, raw: str) -> str:
        """Extract the final answer section from raw LLM output."""
        match = re.search(r"Final Answer:\s*(.*)", raw, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
        return paragraphs[-1] if paragraphs else raw.strip()
