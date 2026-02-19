"""
Search Router - Intelligent query planning & cost optimization for Tavily API.

Classifies query complexity using the already-computed IntentAnalysis and produces
a SearchPlan that controls:
  • search_depth (basic vs advanced)
  • max_results per query
  • number of queries to execute
  • whether to fetch raw page content
  • domain allow/deny lists
  • time-range / topic filters
  • image inclusion

Design goal: minimise API cost & latency while maximising context quality for the
downstream LLM synthesis step.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from loguru import logger

from shared.schemas.models import IntentAnalysis, DifficultyLevel, QuestionType


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class SearchComplexity(str, Enum):
    """How heavy the Tavily search should be."""
    SIMPLE = "simple"        # Single-fact / definition lookup
    MODERATE = "moderate"    # Multi-aspect educational query
    COMPLEX = "complex"      # Deep research, RAG, synthesis


@dataclass
class SearchPlan:
    """Output of the router – consumed by WebSearchAgent."""
    complexity: SearchComplexity
    search_depth: str                        # "basic" | "advanced"
    max_results: int                         # per-query cap
    num_queries: int                         # how many search queries to fire
    include_raw_content: bool                # fetch full page text?
    include_images: bool
    include_answer: bool                     # Tavily's built-in answer
    include_domains: List[str] = field(default_factory=list)
    exclude_domains: List[str] = field(default_factory=list)
    topic: str = "general"                   # "general" | "news"
    time_range: Optional[str] = None         # e.g. "week", "month", "year"
    context_budget_chars: int = 8000         # max chars to keep per result

    def estimated_cost_weight(self) -> float:
        """Relative cost multiplier (1.0 = cheapest baseline)."""
        w = 1.0
        if self.search_depth == "advanced":
            w *= 2.0
        w *= self.num_queries
        if self.include_raw_content:
            w *= 1.5
        return w


# ---------------------------------------------------------------------------
# Domain lists (educational quality)
# ---------------------------------------------------------------------------

TRUSTED_EDUCATIONAL_DOMAINS = [
    "wikipedia.org", "khanacademy.org", "brilliant.org",
    "geeksforgeeks.org", "stackoverflow.com", "mathworld.wolfram.com",
    "docs.python.org", "developer.mozilla.org", "w3schools.com",
    "tutorialspoint.com", "arxiv.org", "nature.com", "sciencedirect.com",
    "medium.com", "towardsdatascience.com", "realpython.com",
    "freecodecamp.org", "coursera.org", "mit.edu", "stanford.edu",
]

LOW_QUALITY_DOMAINS = [
    "pinterest.com", "quora.com", "tiktok.com",
    "facebook.com", "instagram.com", "twitter.com",
]


# ---------------------------------------------------------------------------
# In-memory TTL cache for search results
# ---------------------------------------------------------------------------

class SearchCache:
    """Simple in-memory TTL cache keyed by (query, depth, max_results)."""

    def __init__(self, ttl: int = 3600, max_size: int = 256):
        self._store: Dict[str, Tuple[float, object]] = {}
        self._ttl = ttl
        self._max_size = max_size

    @staticmethod
    def _make_key(query: str, depth: str, max_results: int, include_raw: bool) -> str:
        raw = f"{query.strip().lower()}|{depth}|{max_results}|{include_raw}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, query: str, depth: str, max_results: int, include_raw: bool):
        key = self._make_key(query, depth, max_results, include_raw)
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, data = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        logger.debug(f"Search cache HIT for query: {query[:60]}")
        return data

    def put(self, query: str, depth: str, max_results: int, include_raw: bool, data):
        # Evict oldest if at capacity
        if len(self._store) >= self._max_size:
            oldest_key = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest_key]
        key = self._make_key(query, depth, max_results, include_raw)
        self._store[key] = (time.time(), data)

    def clear(self):
        self._store.clear()


# Singleton cache instance
_search_cache = SearchCache()


def get_search_cache() -> SearchCache:
    return _search_cache


# ---------------------------------------------------------------------------
# Router logic
# ---------------------------------------------------------------------------

class SearchRouter:
    """
    Zero-LLM-call router: derives the SearchPlan purely from IntentAnalysis
    + simple heuristics on the raw query string. This adds *no* latency.
    """

    # ---- complexity classification ----
    @staticmethod
    def _classify_complexity(
        intent: Optional[IntentAnalysis],
        query: str,
    ) -> SearchComplexity:
        """Heuristic complexity bucketing."""

        # If no intent available, fall back to moderate
        if intent is None:
            return SearchComplexity.MODERATE

        # Simple: high confidence, single concept, basic difficulty
        is_simple = (
            intent.confidence >= 0.75
            and intent.difficulty_level == DifficultyLevel.BEGINNER
            and intent.question_type in (QuestionType.CONCEPTUAL, QuestionType.PRACTICAL)
            and len(intent.key_concepts) <= 2
            and len(query.split()) <= 15
        )
        if is_simple:
            return SearchComplexity.SIMPLE

        # Complex: advanced difficulty, math/code, many concepts, or long query
        is_complex = (
            intent.difficulty_level == DifficultyLevel.ADVANCED
            or intent.question_type == QuestionType.MATHEMATICAL
            or (intent.requires_math and intent.requires_code)
            or len(intent.key_concepts) >= 5
            or len(query.split()) > 40
        )
        if is_complex:
            return SearchComplexity.COMPLEX

        return SearchComplexity.MODERATE

    # ---- domain filter selection ----
    @staticmethod
    def _select_domains(
        intent: Optional[IntentAnalysis],
    ) -> Tuple[List[str], List[str]]:
        """Choose include/exclude domain lists based on query type."""
        exclude = list(LOW_QUALITY_DOMAINS)

        # For code questions, bias toward documentation sites
        if intent and intent.requires_code:
            return [], exclude  # don't restrict includes, just exclude junk

        # For math/academic, we might want scholarly sources
        if intent and intent.question_type == QuestionType.MATHEMATICAL:
            return [], exclude

        return [], exclude  # default: only exclude junk

    # ---- main planning method ----
    def plan(
        self,
        query: str,
        intent: Optional[IntentAnalysis] = None,
        force_images: bool = False,
    ) -> SearchPlan:
        """
        Produce a SearchPlan for the given query + intent.

        Parameters
        ----------
        query : str
            The user's raw question.
        intent : IntentAnalysis | None
            Output of the IntentClassifierAgent (already computed).
        force_images : bool
            Override to always request images.

        Returns
        -------
        SearchPlan
        """
        complexity = self._classify_complexity(intent, query)
        include_domains, exclude_domains = self._select_domains(intent)

        needs_images = force_images or (
            intent.requires_visuals if intent else True
        )

        if complexity == SearchComplexity.SIMPLE:
            plan = SearchPlan(
                complexity=complexity,
                search_depth="basic",
                max_results=3,
                num_queries=1,
                include_raw_content=False,
                include_images=needs_images,
                include_answer=True,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                context_budget_chars=4000,
            )

        elif complexity == SearchComplexity.MODERATE:
            plan = SearchPlan(
                complexity=complexity,
                search_depth="basic",
                max_results=5,
                num_queries=2,
                include_raw_content=False,
                include_images=needs_images,
                include_answer=True,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                context_budget_chars=6000,
            )

        else:  # COMPLEX
            plan = SearchPlan(
                complexity=complexity,
                search_depth="advanced",
                max_results=7,
                num_queries=3,
                include_raw_content=True,
                include_images=needs_images,
                include_answer=True,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                context_budget_chars=12000,
            )

        logger.info(
            f"SearchRouter plan: complexity={complexity.value}, "
            f"depth={plan.search_depth}, max_results={plan.max_results}, "
            f"queries={plan.num_queries}, raw_content={plan.include_raw_content}, "
            f"images={plan.include_images}, "
            f"est_cost_weight={plan.estimated_cost_weight():.1f}x"
        )
        return plan

    # ---- smart query generation ----
    def generate_queries(
        self,
        original_question: str,
        intent: Optional[IntentAnalysis],
        plan: SearchPlan,
    ) -> List[str]:
        """
        Generate the right number of search queries based on the plan.
        Avoids redundant queries for simple lookups.
        """
        concepts = intent.key_concepts if intent else []
        queries: List[str] = []

        if plan.num_queries == 1:
            # Single optimised query
            queries.append(original_question)

        elif plan.num_queries == 2:
            queries.append(original_question)
            if concepts:
                queries.append(f"{' '.join(concepts[:3])} explained with examples")
            else:
                queries.append(f"{original_question} tutorial explanation")

        else:
            # 3+ queries for complex research
            queries.append(original_question)
            if concepts:
                queries.append(f"{' '.join(concepts[:2])} in-depth explanation")
            else:
                queries.append(f"{original_question} detailed explanation")

            # Add specialised query
            if intent and intent.requires_math:
                queries.append(f"{original_question} formula derivation proof")
            elif intent and intent.requires_code:
                queries.append(f"{original_question} code implementation example")
            elif intent and intent.requires_visuals:
                queries.append(f"{original_question} diagram visual illustration")
            else:
                queries.append(f"{original_question} examples applications")

        # De-duplicate while preserving order
        seen = set()
        unique: List[str] = []
        for q in queries:
            normalised = q.strip().lower()
            if normalised not in seen:
                unique.append(q)
                seen.add(normalised)

        return unique[:plan.num_queries]
