"""
Performance and quality optimization configuration
"""

# Complexity-based routing thresholds
COMPLEXITY_THRESHOLDS = {
    "very_simple": 0.35,      # Bypass PeCAR, use fast synthesis
    "simple": 0.50,           # Fast synthesis, no deep reasoning
    "moderate": 0.65,         # Standard synthesis, maybe light PeCAR
    "complex": 0.75,          # Full PeCAR pipeline
    "very_complex": 0.85,     # Full PeCAR + extra refinement
}

# Latency budgets by question complexity (seconds)
LATENCY_BUDGETS = {
    "very_simple": 3,         # Ultra-fast response
    "simple": 8,              # Fast response
    "moderate": 20,           # Medium response
    "complex": 45,            # Standard response
    "very_complex": 60,       # Thorough response
}

# PeCAR configuration by complexity
PECAR_CONFIG_BY_COMPLEXITY = {
    "very_simple": {"enabled": False, "max_paths": 0, "max_steps": 0},
    "simple": {"enabled": False, "max_paths": 0, "max_steps": 0},
    "moderate": {"enabled": True, "max_paths": 1, "max_steps": 3},
    "complex": {"enabled": True, "max_paths": 1, "max_steps": 5},
    "very_complex": {"enabled": True, "max_paths": 2, "max_steps": 6},
}

# Synthesis timeout by complexity (seconds)
SYNTHESIS_TIMEOUT_BY_COMPLEXITY = {
    "very_simple": 5,
    "simple": 12,
    "moderate": 25,
    "complex": 40,
    "very_complex": 50,
}

# Search depth by complexity
SEARCH_DEPTH_BY_COMPLEXITY = {
    "very_simple": "basic",    # No raw content
    "simple": "basic",         # No raw content
    "moderate": "basic",       # Balanced
    "complex": "advanced",     # Full research
    "very_complex": "advanced", # Full research
}

def get_complexity_category(score: float) -> str:
    """Classify complexity score into category."""
    if score < COMPLEXITY_THRESHOLDS["very_simple"]:
        return "very_simple"
    elif score < COMPLEXITY_THRESHOLDS["simple"]:
        return "simple"
    elif score < COMPLEXITY_THRESHOLDS["moderate"]:
        return "moderate"
    elif score < COMPLEXITY_THRESHOLDS["complex"]:
        return "complex"
    else:
        return "very_complex"

def get_pecar_config(complexity_score: float) -> dict:
    """Get PeCAR configuration for a given complexity score."""
    category = get_complexity_category(complexity_score)
    return PECAR_CONFIG_BY_COMPLEXITY.get(category, {"enabled": True, "max_paths": 1, "max_steps": 5})

def get_latency_budget(complexity_score: float) -> int:
    """Get latency budget in seconds for a given complexity score."""
    category = get_complexity_category(complexity_score)
    return LATENCY_BUDGETS.get(category, 45)

def get_synthesis_timeout(complexity_score: float) -> int:
    """Get synthesis timeout in seconds for a given complexity score."""
    category = get_complexity_category(complexity_score)
    return SYNTHESIS_TIMEOUT_BY_COMPLEXITY.get(category, 40)

def get_search_depth(complexity_score: float) -> str:
    """Get search depth for a given complexity score."""
    category = get_complexity_category(complexity_score)
    return SEARCH_DEPTH_BY_COMPLEXITY.get(category, "basic")
