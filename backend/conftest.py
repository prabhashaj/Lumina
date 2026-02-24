"""
conftest.py – Ensures backend/ and workspace root are on sys.path
for all pytest test modules.
"""
import sys
from pathlib import Path

# backend/ directory (agents, config, evaluation, graph, tools …)
BACKEND = Path(__file__).parent
# workspace root (shared/ schemas, prompts …)
ROOT = BACKEND.parent

for p in (str(BACKEND), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
