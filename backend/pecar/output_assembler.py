"""
Stage 6 — Mode-Specific Output Assembler (MSOA)

Formats the final synthesised response into the mode-appropriate structure,
applying persona overlays, ensuring structural compliance, and appending
source citations.
"""

from __future__ import annotations

import textwrap
from typing import Callable, List

from loguru import logger

from pecar.models import (
    LearnerProfile,
    LearningMode,
    ReasoningStep,
    StrategyProfile,
)
from pecar import prompts


class ModeSpecificOutputAssembler:
    """
    Stage 6 — Mode-Specific Output Assembler (MSOA).

    Reformats the merged response into a mode-appropriate template structure
    and applies persona overlays.
    """

    def __init__(self, call_llm_fn: Callable) -> None:
        self._llm = call_llm_fn

    async def assemble(
        self,
        merged_response: str,
        query: str,
        mode: LearningMode,
        sources: List[str],
        reasoning_steps: List[ReasoningStep],
        strategy_profile: StrategyProfile,
        learner: LearnerProfile,
    ) -> str:
        """
        Format and assemble the final output for delivery.

        Args:
            merged_response: Synthesised content from PMPS/QFPR stages.
            query: Original user query (used as title seed).
            mode: Active LearningMode for template selection.
            sources: Retrieved source URLs/identifiers.
            reasoning_steps: Verified CoT steps for potential inclusion.
            strategy_profile: Strategy profile (includes persona).
            learner: Learner profile for personalised framing.

        Returns:
            Fully formatted markdown response string.
        """
        system_prompt = prompts.SYSTEM_TEMPLATES[mode]

        if strategy_profile.persona:
            system_prompt = f"You are a {strategy_profile.persona}. {system_prompt}"

        assembly_prompt = self._build_assembly_prompt(
            mode=mode,
            merged_response=merged_response,
            query=query,
            sources=sources,
            learner=learner,
        )

        try:
            assembled = await self._llm(prompt=assembly_prompt, system=system_prompt)
            assembled = assembled.strip()
        except Exception as exc:
            logger.warning("MSOA LLM assembly failed: %s — returning merged response", exc)
            assembled = merged_response

        if sources:
            assembled += self._format_sources_section(sources)

        return assembled

    def _build_assembly_prompt(
        self,
        mode: LearningMode,
        merged_response: str,
        query: str,
        sources: List[str],
        learner: LearnerProfile,
    ) -> str:
        """Construct the assembly instruction prompt for the LLM."""
        template = prompts.OUTPUT_TEMPLATES[mode]
        sources_str = "\n".join(f"- {s}" for s in sources[:8]) if sources else "No external sources."

        return textwrap.dedent(f"""\
            Reformat and refine the following educational response according to
            this EXACT structural template for {mode.value} mode:

            TEMPLATE:
            {template}

            SOURCE CONTENT TO REFORMAT:
            {merged_response[:3000]}

            ORIGINAL QUERY: {query}

            AVAILABLE SOURCES:
            {sources_str}

            LEARNER LEVEL: {learner.knowledge_level:.1f} ({learner.difficulty_preference.value})
            LEARNER STYLE: {learner.preferred_style}

            Instructions:
            - Fill each section of the template with relevant content from the source material
            - Do not invent facts not present in the source content or sources
            - Adapt vocabulary to the learner level
            - Keep the response focused and well-structured
            - For missing template fields, generate appropriate brief content\
        """)

    @staticmethod
    def _format_sources_section(sources: List[str]) -> str:
        """Append a formatted sources section."""
        if not sources:
            return ""
        lines = ["\n\n---\n**Sources**"]
        for i, src in enumerate(sources[:10], 1):
            lines.append(f"{i}. {src}")
        return "\n".join(lines)
