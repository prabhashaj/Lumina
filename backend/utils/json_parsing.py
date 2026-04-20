"""Robust parsing helpers for LLM-generated JSON payloads."""

from __future__ import annotations

import json
import re


def _find_json_bounds(text: str) -> tuple[int, int]:
    depth = 0
    in_string = False
    escape_next = False
    start_pos = -1

    for index, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            if start_pos == -1:
                start_pos = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start_pos != -1:
                return start_pos, index + 1

    return -1, -1


def _sanitize_json_text(text: str) -> str:
    out = []
    in_string = False
    escape_next = False

    for char in text:
        if escape_next:
            out.append(char)
            escape_next = False
            continue

        if char == "\\" and in_string:
            out.append(char)
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            out.append(char)
            continue

        if in_string and char == "\n":
            out.append("\\n")
            continue
        if in_string and char == "\r":
            out.append("\\r")
            continue
        if in_string and char == "\t":
            out.append("\\t")
            continue

        if ord(char) < 32 and char not in ("\n", "\r", "\t"):
            continue

        out.append(char)

    cleaned = "".join(out)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def parse_llm_json(content: str) -> dict:
    """Parse a JSON object from an LLM response."""
    content = (content or "").strip()
    if not content:
        raise ValueError("Empty LLM response")

    direct_candidates = [content]
    block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.DOTALL)
    if block_match:
        direct_candidates.insert(0, block_match.group(1).strip())

    for candidate in direct_candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            cleaned = _sanitize_json_text(candidate)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                start, end = _find_json_bounds(candidate)
                if start == -1 or end == -1:
                    continue

                extracted = candidate[start:end]
                try:
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    cleaned = _sanitize_json_text(extracted)
                    try:
                        return json.loads(cleaned)
                    except json.JSONDecodeError:
                        continue

    raise ValueError("Could not parse JSON from LLM response")
