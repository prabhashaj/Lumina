"""Runtime optimization helpers for PeCAR and search budgets.

These helpers centralize lightweight heuristics based on intent complexity so
orchestrator decisions stay consistent and easy to tune.
"""

from __future__ import annotations


def get_complexity_category(complexity: float) -> str:
    """Map a normalized complexity score to low/medium/high."""
    score = float(complexity or 0.0)
    if score < 0.35:
        return "low"
    if score < 0.7:
        return "medium"
    return "high"


def get_pecar_config(complexity: float) -> dict:
    """Return PeCAR path/step budget tuned by complexity."""
    category = get_complexity_category(complexity)
    if category == "low":
        return {"enabled": False, "max_paths": 1, "max_steps": 3}
    if category == "medium":
        return {"enabled": True, "max_paths": 2, "max_steps": 5}
    return {"enabled": True, "max_paths": 3, "max_steps": 6}


def get_latency_budget(complexity: float) -> dict:
    """Return soft stage budgets (seconds) for observability/tuning."""
    category = get_complexity_category(complexity)
    if category == "low":
        return {"search": 5, "extraction": 4, "reasoning": 0, "synthesis": 10}
    if category == "medium":
        return {"search": 8, "extraction": 6, "reasoning": 10, "synthesis": 14}
    return {"search": 12, "extraction": 8, "reasoning": 16, "synthesis": 18}


def get_synthesis_timeout(complexity: float) -> int:
    """Return synthesis timeout in seconds by complexity tier."""
    category = get_complexity_category(complexity)
    if category == "low":
        return 18
    if category == "medium":
        return 24
    return 30


def get_search_depth(complexity: float) -> str:
    """Return Tavily depth hint for planner/orchestrator use."""
    return "advanced" if get_complexity_category(complexity) == "high" else "basic"
