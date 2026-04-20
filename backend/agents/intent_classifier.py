"""
Intent Classifier Agent - Analyzes student questions to determine learning needs
"""
import json
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from loguru import logger

from config.settings import settings
from shared.schemas.models import IntentAnalysis, DifficultyLevel, QuestionType
from shared.prompts.templates import INTENT_CLASSIFIER_PROMPT

try:
    from utils.json_parsing import parse_llm_json
except Exception:
    parse_llm_json = None


def extract_json_from_response(content: str) -> dict:
    """Extract JSON from response, handling markdown code blocks and invalid control chars."""

    if parse_llm_json is not None:
        try:
            return parse_llm_json(content)
        except Exception:
            pass

    def find_json_bounds(text: str) -> tuple[int, int]:
        depth = 0
        in_string = False
        escape_next = False
        start_pos = -1

        for i, ch in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                if start_pos == -1:
                    start_pos = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start_pos != -1:
                    return start_pos, i + 1

        return -1, -1

    def sanitize_json_text(text: str) -> str:
        # Escape literal newlines/tabs/carriage returns inside strings.
        out = []
        in_string = False
        escape_next = False

        for ch in text:
            if escape_next:
                out.append(ch)
                escape_next = False
                continue

            if ch == "\\" and in_string:
                out.append(ch)
                escape_next = True
                continue

            if ch == '"':
                in_string = not in_string
                out.append(ch)
                continue

            if in_string and ch == "\n":
                out.append("\\n")
                continue
            if in_string and ch == "\r":
                out.append("\\r")
                continue
            if in_string and ch == "\t":
                out.append("\\t")
                continue

            # Drop other ASCII control chars.
            if ord(ch) < 32 and ch not in ("\n", "\r", "\t"):
                continue

            out.append(ch)

        cleaned = "".join(out)
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
        return cleaned

    content = content.strip()
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.DOTALL)
    search_content = code_block_match.group(1) if code_block_match else content

    start_pos, end_pos = find_json_bounds(search_content)
    if start_pos == -1 or end_pos == -1:
        # Fallback for truncated model outputs: recover key fields with regex.
        def extract_bool(name: str, default: bool = False) -> bool:
            m = re.search(rf'"{name}"\s*:\s*(true|false)', search_content, re.IGNORECASE)
            if not m:
                return default
            return m.group(1).lower() == "true"

        def extract_str(name: str, default: str) -> str:
            m = re.search(rf'"{name}"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', search_content)
            if not m:
                return default
            return m.group(1)

        def extract_conf(default: float = 0.5) -> float:
            m = re.search(r'"confidence"\s*:\s*([0-9]*\.?[0-9]+)', search_content)
            if not m:
                return default
            try:
                return float(m.group(1))
            except ValueError:
                return default

        concepts: list[str] = []
        concepts_match = re.search(r'"key_concepts"\s*:\s*\[(.*?)\]', search_content, re.DOTALL)
        if concepts_match:
            concepts = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', concepts_match.group(1))

        recovered = {
            "difficulty_level": extract_str("difficulty_level", "intermediate"),
            "question_type": extract_str("question_type", "conceptual"),
            "requires_visuals": extract_bool("requires_visuals", True),
            "requires_math": extract_bool("requires_math", False),
            "requires_code": extract_bool("requires_code", False),
            "key_concepts": concepts,
            "confidence": extract_conf(0.5),
        }

        logger.warning("Recovered partial intent JSON from truncated model output")
        return recovered

    json_str = search_content[start_pos:end_pos]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        cleaned = sanitize_json_text(json_str)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error after cleanup: {str(e)}")
            logger.debug(f"Failed JSON (first 500 chars): {cleaned[:500]}")
            logger.debug(f"Error at position {e.pos}: {repr(cleaned[max(0, e.pos-20):e.pos+20])}")
            raise ValueError(f"Could not parse JSON from response: {str(e)}")


class IntentClassifierAgent:
    """Analyzes student questions to determine difficulty, intent, and learning needs"""

    def __init__(self):
        # Use Mistral API only.
        self.llm = None
        self.backup_llm = None

        if settings.mistral_api_key:
            logger.info("Intent Classifier: Using Mistral API")
            self.llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.0,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
                max_tokens=500,
            )

        if not self.llm:
            raise ValueError("No valid API key found. Please set MISTRAL_API_KEY")

    async def _call_llm_with_fallback(self, messages):
        """Call LLM with automatic fallback to backup on errors"""
        try:
            return await self.llm.ainvoke(messages)
        except Exception as e:
            error_str = str(e)
            if self.backup_llm and (
                "402" in error_str
                or "credits" in error_str.lower()
                or "payment" in error_str.lower()
            ):
                logger.warning(f"Primary LLM failed ({error_str[:100]}), using backup Mistral API")
                return await self.backup_llm.ainvoke(messages)
            raise

    async def analyze(self, question: str, conversation_memory: str = "") -> IntentAnalysis:
        """
        Analyze a student question to determine learning characteristics.

        Args:
            question: The student's question

        Returns:
            IntentAnalysis object with classification results
        """
        try:
            logger.info(f"Analyzing intent for question: {question[:100]}...")

            prompt_text = INTENT_CLASSIFIER_PROMPT.format(question=question)
            if conversation_memory:
                prompt_text += (
                    "\n\nConversation context from earlier turns (use this to resolve follow-up references):\n"
                    f"{conversation_memory}"
                )
            messages = [HumanMessage(content=prompt_text)]

            response = await self._call_llm_with_fallback(messages)
            logger.debug(f"Raw LLM response: {response.content[:200]}")

            result = extract_json_from_response(response.content)

            difficulty_val = result["difficulty_level"]
            complexity_map = {"beginner": 0.3, "intermediate": 0.55, "advanced": 0.8}
            base_complexity = complexity_map.get(difficulty_val, 0.5)
            qtype = result["question_type"]
            type_boost = {"mathematical": 0.1, "mixed": 0.05, "practical": 0.0, "conceptual": 0.0}
            complexity_score = min(1.0, base_complexity + type_boost.get(qtype, 0.0))

            pecar_qtype_map = {
                "conceptual": "conceptual",
                "practical": "procedural",
                "mathematical": "procedural",
                "mixed": "evaluative",
            }

            intent = IntentAnalysis(
                difficulty_level=DifficultyLevel(difficulty_val),
                question_type=QuestionType(qtype),
                requires_visuals=result["requires_visuals"],
                requires_math=result["requires_math"],
                requires_code=result["requires_code"],
                key_concepts=result["key_concepts"],
                confidence=result["confidence"],
                complexity_score=complexity_score,
                pecar_question_type=pecar_qtype_map.get(qtype, "conceptual"),
            )

            logger.info(f"Intent analysis complete: {intent.difficulty_level}, {intent.question_type}")
            return intent

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            logger.error(f"Response content was: {response.content if 'response' in locals() else 'No response'}")
            return IntentAnalysis(
                difficulty_level=DifficultyLevel.INTERMEDIATE,
                question_type=QuestionType.CONCEPTUAL,
                requires_visuals=True,
                requires_math=False,
                requires_code=False,
                key_concepts=[],
                confidence=0.5,
            )
        except Exception as e:
            logger.error(f"Error in intent classification: {str(e)}")
            logger.error(f"Response content was: {response.content if 'response' in locals() else 'No response'}")
            return IntentAnalysis(
                difficulty_level=DifficultyLevel.INTERMEDIATE,
                question_type=QuestionType.CONCEPTUAL,
                requires_visuals=True,
                requires_math=False,
                requires_code=False,
                key_concepts=[],
                confidence=0.5,
            )
