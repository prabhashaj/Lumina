"""
Web Search Agent - Performs intelligent web searches using Tavily API.

Optimised for cost, latency, and context quality via SearchPlan + caching.
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Optional

from tavily import TavilyClient
from loguru import logger

from config.settings import settings
from shared.schemas.models import SearchResult
from agents.search_router import SearchPlan, SearchComplexity, get_search_cache
from tools.cost_tracking import record_tavily_search


class WebSearchAgent:
    """Performs intelligent web searches and ranks results.

    Accepts a ``SearchPlan`` from the SearchRouter to dynamically tune
    every Tavily API call for cost/latency vs. context depth.
    """

    def __init__(self):
        self.client = TavilyClient(api_key=settings.tavily_api_key)
        self._cache = get_search_cache()
        self.last_error_kind: Optional[str] = None
        self.last_error_message: Optional[str] = None
        self.last_multi_status: dict = {}

    @staticmethod
    def _classify_search_error(error_message: str) -> str:
        msg = (error_message or "").lower()

        if (
            "nameresolutionerror" in msg
            or "failed to resolve" in msg
            or "getaddrinfo failed" in msg
            or "dns" in msg
        ):
            return "dns_resolution"
        if (
            "econnreset" in msg
            or "max retries exceeded" in msg
            or "connection" in msg
            or "httpsconnectionpool" in msg
        ):
            return "network_unavailable"
        if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
            return "auth_error"

        return "unknown"

    def get_last_multi_status(self) -> dict:
        return dict(self.last_multi_status)

    # ------------------------------------------------------------------
    # Single-query search (plan-aware + cached)
    # ------------------------------------------------------------------
    async def search(
        self,
        query: str,
        plan: Optional[SearchPlan] = None,
        # Legacy params kept for backward-compat (fallback image search, etc.)
        search_depth: str = "basic",
        include_images: bool = True,
    ) -> List[SearchResult]:
        """
        Search Tavily with parameters driven by *plan*.

        If no plan is supplied the legacy keyword arguments are used, but
        with safer defaults (``basic`` depth, no raw content).
        """
        # Resolve effective parameters from plan or kwargs
        self.last_error_kind = None
        self.last_error_message = None

        depth = plan.search_depth if plan else search_depth
        max_results = plan.max_results if plan else min(settings.max_search_results, 5)
        raw_content = plan.include_raw_content if plan else False
        images = plan.include_images if plan else include_images
        answer = plan.include_answer if plan else True
        include_domains = plan.include_domains if plan else []
        exclude_domains = plan.exclude_domains if plan else []
        topic = plan.topic if plan else "general"
        time_range = plan.time_range if plan else None
        context_budget = plan.context_budget_chars if plan else 6000

        # ---------- cache check ----------
        cached = self._cache.get(query, depth, max_results, raw_content)
        if cached is not None:
            logger.info(f"[cache-hit] Returning cached results for: {query[:60]}")
            return cached

        # ---------- API call ----------
        try:
            t0 = time.time()
            timeout_seconds = max(5, int(getattr(settings, "timeout_seconds", 30)))
            logger.info(
                f"Tavily search: depth={depth}, max={max_results}, "
                f"raw={raw_content}, images={images} | {query[:80]}"
            )

            kwargs = dict(
                query=query,
                search_depth=depth,
                max_results=max_results,
                include_images=images,
                include_answer=answer,
                include_raw_content=raw_content,
                topic=topic,
            )
            if include_domains:
                kwargs["include_domains"] = include_domains
            if exclude_domains:
                kwargs["exclude_domains"] = exclude_domains
            if time_range:
                kwargs["time_range"] = time_range

            record_tavily_search(depth, 1)
            response = await asyncio.wait_for(
                asyncio.to_thread(self.client.search, **kwargs),
                timeout=timeout_seconds,
            )
            elapsed = time.time() - t0

            # ---------- parse results ----------
            results: List[SearchResult] = []
            for item in response.get("results", []):
                content = item.get("content", "")
                # If raw_content returned and is richer, prefer it but cap length
                if raw_content and item.get("raw_content"):
                    raw = item["raw_content"]
                    if len(raw) > len(content):
                        content = raw[:context_budget]

                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        content=content,
                        score=item.get("score", 0.5),
                        images=[],
                    )
                )

            # Attach images to first result
            tavily_images = response.get("images", [])
            if images and tavily_images and results:
                results[0].images = tavily_images[: settings.max_images_per_response]

            logger.info(
                f"Tavily returned {len(results)} results, "
                f"{len(tavily_images)} images in {elapsed:.2f}s"
            )

            self.last_error_kind = None
            self.last_error_message = None

            # ---------- cache store ----------
            self._cache.put(query, depth, max_results, raw_content, results)

            return results

        except asyncio.TimeoutError:
            logger.error(
                f"Tavily search timed out after {timeout_seconds}s for query: {query[:80]}"
            )
            self.last_error_kind = "timeout"
            self.last_error_message = f"Timeout after {timeout_seconds}s"
            return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            self.last_error_kind = self._classify_search_error(str(e))
            self.last_error_message = str(e)
            return []

    # ------------------------------------------------------------------
    # Multi-query search (plan-aware)
    # ------------------------------------------------------------------
    async def multi_query_search(
        self,
        queries: List[str],
        plan: Optional[SearchPlan] = None,
    ) -> List[SearchResult]:
        """
        Execute *queries* list and combine/deduplicate results.

        The number of queries actually executed is capped by ``plan.num_queries``
        (or ``len(queries)`` when no plan is given).
        """
        max_queries = plan.num_queries if plan else len(queries)
        effective_queries = queries[:max_queries]

        all_results: List[SearchResult] = []
        seen_urls: set = set()
        all_image_urls: List[str] = []
        seen_image_urls: set = set()
        failed_queries = 0
        error_kind_counts: dict = {}

        for idx, query in enumerate(effective_queries, 1):
            logger.info(f"Executing web query {idx}/{len(effective_queries)}: {query[:100]}")
            results = await self.search(query, plan=plan)
            if not results and self.last_error_kind:
                failed_queries += 1
                error_kind_counts[self.last_error_kind] = error_kind_counts.get(self.last_error_kind, 0) + 1

            for result in results:
                # Collect images before URL dedup
                for img_url in result.images:
                    norm = img_url.lower().split("?")[0]
                    if norm not in seen_image_urls:
                        all_image_urls.append(img_url)
                        seen_image_urls.add(norm)

                if result.url not in seen_urls:
                    all_results.append(result)
                    seen_urls.add(result.url)

        # Sort by relevance score
        all_results.sort(key=lambda x: x.score, reverse=True)

        # Cap final set
        cap = plan.max_results if plan else settings.max_search_results
        top_results = all_results[:cap]

        # Merge images into first result
        if all_image_urls and top_results:
            existing = {u.lower().split("?")[0] for u in top_results[0].images}
            for img_url in all_image_urls:
                if img_url.lower().split("?")[0] not in existing:
                    top_results[0].images.append(img_url)
                    existing.add(img_url.lower().split("?")[0])

        logger.info(
            f"Multi-query: {len(effective_queries)} queries → "
            f"{len(top_results)} unique results, {len(all_image_urls)} images"
        )

        dominant_error = None
        if error_kind_counts:
            dominant_error = max(error_kind_counts.items(), key=lambda item: item[1])[0]

        search_unavailable = (
            len(effective_queries) > 0
            and failed_queries == len(effective_queries)
            and len(top_results) == 0
            and dominant_error in {"dns_resolution", "network_unavailable", "timeout"}
        )

        self.last_multi_status = {
            "total_queries": len(effective_queries),
            "failed_queries": failed_queries,
            "error_kind": dominant_error,
            "search_unavailable": search_unavailable,
            "last_error_message": self.last_error_message,
        }

        return top_results
