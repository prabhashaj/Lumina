"""
Lightweight Tavily cost tracking (per-request).
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import json

TAVILY_CREDIT_USD = 0.008


@dataclass
class TavilyUsage:
    basic_queries: int = 0
    advanced_queries: int = 0

    @property
    def credits(self) -> int:
        return self.basic_queries + (2 * self.advanced_queries)

    def to_summary(self) -> Dict[str, Any]:
        credits = self.credits
        usd = round(credits * TAVILY_CREDIT_USD, 6)
        return {
            "credits": credits,
            "usd": usd,
            "rate_per_credit_usd": TAVILY_CREDIT_USD,
            "queries": {
                "basic": self.basic_queries,
                "advanced": self.advanced_queries,
            },
            "pricing_basis": "basic=1 credit/query, advanced=2 credits/query",
        }


_usage_var: ContextVar[TavilyUsage | None] = ContextVar("tavily_cost_usage", default=None)


def start_tracking() -> TavilyUsage:
    usage = TavilyUsage()
    _usage_var.set(usage)
    return usage


def _get_usage() -> TavilyUsage:
    usage = _usage_var.get()
    if usage is None:
        usage = TavilyUsage()
        _usage_var.set(usage)
    return usage


def record_tavily_search(search_depth: str, count: int = 1) -> None:
    usage = _get_usage()
    if search_depth == "advanced":
        usage.advanced_queries += count
    else:
        usage.basic_queries += count


def summarize_cost() -> Dict[str, Any]:
    usage = _get_usage()
    summary = {
        "tavily": usage.to_summary(),
        "estimated": False,
    }
    _append_cost_log(summary)
    return summary


def _append_cost_log(summary: Dict[str, Any]) -> None:
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        log_line = json.dumps({"timestamp": timestamp, "cost": summary}, ensure_ascii=True)
        log_path = Path(__file__).resolve().parents[3] / "logs.txt"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(log_line + "\n")
    except Exception:
        # Never block a response on logging.
        return
