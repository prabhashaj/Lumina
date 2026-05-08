"""
LLM Output Evaluation Tests
Run: pytest test_llm_evaluation.py -v
Run specific layer: pytest test_llm_evaluation.py -m structural -v   (no API calls)
Run all including LLM: pytest test_llm_evaluation.py -v
"""
import sys
from pathlib import Path

# backend/ itself (for evaluation, agents, config, etc.)
sys.path.insert(0, str(Path(__file__).parent))
# workspace root (for shared/)
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
from typing import Dict, List, Any

from evaluation.structural_evaluator import StructuralEvaluator


# ---------------------------------------------------------------------------
# Shared fixture – a realistic teaching response dict
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_response() -> Dict[str, Any]:
    return {
        "tldr": (
            "Photosynthesis is the process by which plants convert sunlight, "
            "water, and carbon dioxide into glucose and oxygen."
        ),
        "explanation": (
            "## What is Photosynthesis?\n\n"
            "Photosynthesis is the fundamental process that allows plants, algae, "
            "and some bacteria to produce their own food using light energy.\n\n"
            "## Key Steps\n\n"
            "**1. Light Absorption**\nChlorophyll molecules in the chloroplasts absorb "
            "sunlight — mainly red and blue wavelengths.\n\n"
            "**2. Water Splitting (Photolysis)**\nLight energy splits water molecules "
            "into hydrogen ions, electrons, and oxygen. The oxygen is released as a "
            "by-product — this is the oxygen we breathe.\n\n"
            "**3. The Calvin Cycle**\nCarbon dioxide from the air is fixed into "
            "glucose through a series of enzyme-driven reactions.\n\n"
            "## Why It Matters\n\n"
            "Without photosynthesis, there would be no oxygen in the atmosphere "
            "and no food chains as we know them. Consider this: every calorie you "
            "eat traces back to a plant capturing sunlight.\n\n"
            "**Summary equation:**\n"
            "```\n6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂\n```"
        ),
        "analogy": (
            "Think of a plant as a tiny solar-powered factory. "
            "Sunlight is the electricity, water and CO₂ are the raw materials, "
            "and glucose is the finished product that powers everything inside."
        ),
        "examples": [
            "Aquatic plants like elodea produce visible oxygen bubbles in sunlight.",
            "Autumn leaf colour change happens because chlorophyll breaks down "
            "and stops capturing light.",
            "C4 plants like maize have evolved a more efficient photosynthesis "
            "pathway that reduces water loss in hot climates.",
        ],
        "practice_questions": [
            "What is the role of chlorophyll in photosynthesis?",
            "Why do plants need water for photosynthesis and what happens to it?",
            "Explain why photosynthesis is described as an endothermic reaction.",
            "Compare the light-dependent and light-independent reactions.",
        ],
        "sources": [
            {
                "title": "Photosynthesis Overview – Khan Academy",
                "url": "https://www.khanacademy.org/science/biology/photosynthesis",
                "snippet": "Detailed overview of light reactions and the Calvin cycle.",
                "domain": "khanacademy.org",
                "relevance_score": 0.95,
            },
            {
                "title": "Photosynthesis – Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Photosynthesis",
                "snippet": "Comprehensive reference covering all stages of photosynthesis.",
                "domain": "wikipedia.org",
                "relevance_score": 0.90,
            },
        ],
    }


@pytest.fixture
def incomplete_response() -> Dict[str, Any]:
    """Response that is missing several required components."""
    return {
        "tldr": "Plants make food from sunlight.",
        "explanation": "It involves chlorophyll.",
        # analogy, practice_questions, sources all missing
    }


# ---------------------------------------------------------------------------
# Structural Tests (no API calls – fast, always runnable)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.structural
class TestStructuralEvaluator:
    """Rule-based format and completeness checks — no LLM calls."""

    @pytest.fixture
    def evaluator(self) -> StructuralEvaluator:
        return StructuralEvaluator()

    @pytest.mark.asyncio
    async def test_complete_response_scores_high(self, evaluator, sample_response):
        """A well-formed response should score highly on structural metrics."""
        metrics = await evaluator.evaluate_teaching_response_structure(sample_response)

        assert metrics["completeness"] == 1.0, "All required fields present"
        assert metrics["tldr_quality"] >= 0.8, "TL;DR is appropriate length"
        assert metrics["length_appropriateness"] >= 0.6, "Explanation has adequate length"
        assert metrics["markdown_quality"] >= 0.5, "Markdown headers/lists present"
        assert metrics["citation_quality"] >= 0.8, "Sources have url, title, snippet, domain"
        assert metrics["overall_structural_score"] >= 0.7

    @pytest.mark.asyncio
    async def test_incomplete_response_scores_low(self, evaluator, incomplete_response):
        """Missing fields should lower the completeness score."""
        metrics = await evaluator.evaluate_teaching_response_structure(incomplete_response)

        assert metrics["completeness"] < 0.5, "Several required fields missing"
        assert metrics["citation_quality"] == 0.0, "No sources provided"

    @pytest.mark.asyncio
    async def test_tldr_word_count_scoring(self, evaluator):
        """TL;DR scoring thresholds."""
        cases = [
            ("", 0.0),
            ("Too short", 0.3),           # 2 words
            ("A " * 20, 1.0),              # 20 words — ideal range
            ("Word " * 80, 0.3),           # 80 words — too long
        ]
        for tldr, expected_min in cases:
            score = evaluator._evaluate_tldr(tldr)
            assert score >= expected_min - 0.05, (
                f"TL;DR '{tldr[:30]}' expected ≥{expected_min}, got {score}"
            )

    @pytest.mark.asyncio
    async def test_markdown_quality_detection(self, evaluator):
        """Markdown with headers, lists, and emphasis should score well."""
        rich_markdown = (
            "## Header\n\n- item 1\n- item 2\n\n**bold text** and `code`"
        )
        plain_text = "This is a plain sentence without any markdown formatting at all."

        rich_score = evaluator._evaluate_markdown(rich_markdown)
        plain_score = evaluator._evaluate_markdown(plain_text)

        assert rich_score > plain_score, "Rich markdown should score higher"
        assert rich_score >= 0.75

    @pytest.mark.asyncio
    async def test_citation_quality_per_field(self, evaluator):
        """Sources with all fields score higher than sparse sources."""
        full_sources = [
            {"url": "https://example.com", "title": "Title", "snippet": "Snip", "domain": "example.com"}
        ]
        sparse_sources = [{"url": "https://example.com"}]
        no_sources: list = []

        full_score = evaluator._evaluate_citations(full_sources)
        sparse_score = evaluator._evaluate_citations(sparse_sources)
        no_score = evaluator._evaluate_citations(no_sources)

        assert full_score > sparse_score > no_score
        assert no_score == 0.0
        assert full_score >= 0.9

    @pytest.mark.asyncio
    async def test_json_validity_flag(self, evaluator):
        """_raw_response key triggers JSON validity check."""
        valid = {"tldr": "x", "explanation": "x", "_raw_response": '{"key": "value"}'}
        invalid = {"tldr": "x", "explanation": "x", "_raw_response": "{bad json}"}

        valid_metrics = await evaluator.evaluate_teaching_response_structure(valid)
        invalid_metrics = await evaluator.evaluate_teaching_response_structure(invalid)

        assert valid_metrics["json_validity"] == 1.0
        assert invalid_metrics["json_validity"] == 0.0


# ---------------------------------------------------------------------------
# Pedagogical Tests — heuristic methods only (no API calls)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.pedagogical
class TestPedagogicalEvaluatorHeuristics:
    """Tests for the rule-based pedagogical methods."""

    @pytest.fixture
    def evaluator(self):
        from evaluation.pedagogical_evaluator import PedagogicalEvaluator
        return PedagogicalEvaluator()

    def test_clarity_beginner_short_sentences(self, evaluator):
        """Sentences around 12 words should score well at beginner level."""
        text = (
            "Plants make their own food using sunlight through a process called photosynthesis. "
            "Sunlight hits the green leaves and gives the plant the energy it needs to grow. "
            "Water and carbon dioxide are combined inside the leaf to create sugar and oxygen."
        )
        score = evaluator._evaluate_clarity(text, "beginner")
        assert score >= 0.7

    def test_clarity_advanced_longer_sentences(self, evaluator):
        """Longer, denser sentences are appropriate for advanced level."""
        text = (
            "The quantum mechanical treatment of the hydrogen atom requires solving "
            "the time-independent Schrödinger equation in spherical coordinates, "
            "yielding wavefunctions characterised by principal, azimuthal, and "
            "magnetic quantum numbers that determine orbital shape and energy."
        )
        score = evaluator._evaluate_clarity(text, "advanced")
        assert score >= 0.5

    def test_engagement_with_rhetorical_techniques(self, evaluator):
        """Text using questions and analogies should score higher."""
        engaging = (
            "Have you ever wondered why leaves are green? "
            "Think of chlorophyll **like a solar panel**. "
            "Consider how plants convert sunlight — it's similar to how we eat food.\n\n"
            "- They absorb light.\n- They release oxygen.\n"
        )
        boring = (
            "Chlorophyll is a pigment. It absorbs light. "
            "The light is used in photosynthesis."
        )
        assert evaluator._evaluate_engagement(engaging) > evaluator._evaluate_engagement(boring)

    def test_difficulty_match_intermediate(self, evaluator):
        """Medium-length sentences should match intermediate level best."""
        text = " ".join(["word"] * 17 + ["."] + ["word"] * 17 + ["."])
        score = evaluator._evaluate_difficulty_match(text, "intermediate")
        assert score >= 0.8


# ---------------------------------------------------------------------------
# Integration Tests — require LLM API (marked slow)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.slow
class TestSemanticEvaluator:
    """LLM-based semantic quality tests. Require valid API keys."""

    @pytest.fixture
    def evaluator(self):
        from evaluation.semantic_evaluator import SemanticEvaluator
        return SemanticEvaluator()

    @pytest.mark.asyncio
    async def test_accurate_response_scores_high(self, evaluator, sample_response):
        """A factually correct response should score high on semantic accuracy."""
        metrics = await evaluator.evaluate_teaching_response(
            question="How does photosynthesis work?",
            teaching_response=sample_response["explanation"],
            sources=[s["snippet"] for s in sample_response["sources"]],
        )

        assert metrics["factual_accuracy"] >= 0.7
        assert metrics["logical_coherence"] >= 0.7
        assert metrics["concept_coverage"] >= 0.7
        assert metrics["overall_semantic_score"] >= 0.65

    @pytest.mark.asyncio
    async def test_inaccurate_response_scores_low(self, evaluator):
        """A clearly wrong explanation should flag low factual accuracy."""
        bad_response = (
            "Photosynthesis happens in the mitochondria by consuming oxygen "
            "and releasing carbon dioxide. Plants do not need sunlight at all."
        )
        metrics = await evaluator.evaluate_teaching_response(
            question="How does photosynthesis work?",
            teaching_response=bad_response,
            sources=["Photosynthesis occurs in chloroplasts using sunlight."],
        )
        assert metrics["factual_accuracy"] < 0.6


@pytest.mark.integration
@pytest.mark.slow
class TestPedagogicalEvaluatorLLM:
    """LLM-based pedagogical evaluation. Require valid API keys."""

    @pytest.fixture
    def evaluator(self):
        from evaluation.pedagogical_evaluator import PedagogicalEvaluator
        return PedagogicalEvaluator()

    @pytest.mark.asyncio
    async def test_full_pedagogical_evaluation(self, evaluator, sample_response):
        metrics = await evaluator.evaluate_teaching_quality(
            question="How does photosynthesis work?",
            difficulty_level="intermediate",
            tldr=sample_response["tldr"],
            explanation=sample_response["explanation"],
            analogy=sample_response["analogy"],
            examples=sample_response["examples"],
            practice_questions=sample_response["practice_questions"],
        )

        assert metrics["analogy_quality"] >= 0.6
        assert metrics["example_quality"] >= 0.6
        assert metrics["practice_quality"] >= 0.6
        assert metrics["scaffolding"] >= 0.6
        assert metrics["overall_pedagogical_score"] >= 0.65

    @pytest.mark.asyncio
    async def test_missing_analogy_penalised(self, evaluator, sample_response):
        metrics = await evaluator.evaluate_teaching_quality(
            question="How does photosynthesis work?",
            difficulty_level="intermediate",
            tldr=sample_response["tldr"],
            explanation=sample_response["explanation"],
            analogy="",  # missing
            examples=sample_response["examples"],
            practice_questions=sample_response["practice_questions"],
        )
        assert metrics["analogy_quality"] <= 0.25, "Empty analogy should score very low"


@pytest.mark.integration
@pytest.mark.slow
class TestEvaluationDashboard:
    """End-to-end dashboard evaluation. Require valid API keys."""

    @pytest.fixture
    def dashboard(self):
        from evaluation.evaluation_dashboard import EvaluationDashboard
        return EvaluationDashboard()

    @pytest.mark.asyncio
    async def test_full_pipeline_evaluation(self, dashboard, sample_response):
        """Complete evaluation pipeline returns expected keys."""
        result = await dashboard.evaluate(
            question="How does photosynthesis work?",
            response_dict=sample_response,
            sources=[s["snippet"] for s in sample_response["sources"]],
            difficulty_level="intermediate",
        )

        assert "semantic_scores" in result
        assert "pedagogical_scores" in result
        assert "structural_scores" in result
        assert "overall_score" in result
        assert "pass" in result
        assert "summary" in result
        assert 0.0 <= result["overall_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_report_generation(self, dashboard, sample_response):
        """Report should contain key sections after at least one evaluation."""
        await dashboard.evaluate(
            question="How does photosynthesis work?",
            response_dict=sample_response,
            sources=[],
            difficulty_level="intermediate",
        )

        report = dashboard.generate_report()
        assert "OVERALL SCORE" in report
        assert "Pass Rate" in report
        assert "Semantic Accuracy" in report
        assert "Pedagogical Quality" in report
        assert "Structural Quality" in report
