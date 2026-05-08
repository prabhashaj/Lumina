from __future__ import annotations

import pytest

from graph.orchestrator import ResearchOrchestrator


@pytest.mark.asyncio
async def test_select_images_node_returns_empty_list_when_search_unavailable():
    orchestrator = ResearchOrchestrator.__new__(ResearchOrchestrator)

    result = await orchestrator.select_images_node(
        {
            "original_question": "Who is the prime minister of India?",
            "metadata": {"search_unavailable": True},
            "intent": None,
        }
    )

    assert result == {"images": []}