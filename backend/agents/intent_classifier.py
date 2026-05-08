"""
Intent Classifier Agent - Analyzes student questions to determine learning needs
"""
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from loguru import logger

from config.settings import settings
from shared.schemas.models import IntentAnalysis, DifficultyLevel, QuestionType
from shared.prompts.templates import INTENT_CLASSIFIER_PROMPT
from utils.json_parsing import parse_llm_json


def _extract_partial_intent_fields(content: str) -> Dict[str, Any]:
    """Best-effort extraction for required intent fields from malformed JSON-like text."""
    raw = content or ""
    result: Dict[str, Any] = {}

    str_patterns = {
        "difficulty_level": r'"difficulty_level"\s*:\s*"(beginner|intermediate|advanced)"',
        "question_type": r'"question_type"\s*:\s*"(conceptual|practical|mathematical|mixed)"',
    }
    for key, pattern in str_patterns.items():
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            result[key] = match.group(1).lower()

    bool_patterns = {
        "requires_visuals": r'"requires_visuals"\s*:\s*(true|false)',
        "requires_math": r'"requires_math"\s*:\s*(true|false)',
        "requires_code": r'"requires_code"\s*:\s*(true|false)',
    }
    for key, pattern in bool_patterns.items():
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            result[key] = match.group(1).lower() == "true"

    confidence_match = re.search(r'"confidence"\s*:\s*([0-9]*\.?[0-9]+)', raw)
    if confidence_match:
        try:
            result["confidence"] = max(0.0, min(1.0, float(confidence_match.group(1))))
        except ValueError:
            pass

    concepts_match = re.search(r'"key_concepts"\s*:\s*\[(.*?)\]', raw, re.DOTALL)
    if concepts_match:
        items = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', concepts_match.group(1))
        cleaned = [item.strip() for item in items if item.strip()]
        result["key_concepts"] = cleaned

    return result


def _to_intent_analysis(result: Dict[str, Any]) -> IntentAnalysis:
    """Build IntentAnalysis and compute derived PeCAR fields."""
    difficulty_val = result["difficulty_level"]
    qtype = result["question_type"]

    complexity_map = {"beginner": 0.3, "intermediate": 0.55, "advanced": 0.8}
    base_complexity = complexity_map.get(difficulty_val, 0.5)
    type_boost = {"mathematical": 0.1, "mixed": 0.05, "practical": 0.0, "conceptual": 0.0}
    complexity_score = min(1.0, base_complexity + type_boost.get(qtype, 0.0))

    pecar_qtype_map = {
        "conceptual": "conceptual",
        "practical": "procedural",
        "mathematical": "procedural",
        "mixed": "evaluative",
    }

    return IntentAnalysis(
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
                max_tokens=500
            )
        
        if not self.llm:
            raise ValueError("No valid API key found. Please set MISTRAL_API_KEY")

    async def _call_llm_with_fallback(self, messages):
        """Call LLM with automatic fallback to backup on errors"""
        try:
            return await self.llm.ainvoke(messages)
        except Exception as e:
            error_str = str(e)
            # Check for payment/credit errors
            if self.backup_llm and ("402" in error_str or "credits" in error_str.lower() or "payment" in error_str.lower()):
                logger.warning(f"Primary LLM failed ({error_str[:100]}), using backup Mistral API")
                return await self.backup_llm.ainvoke(messages)
            raise

        
    async def analyze(self, question: str) -> IntentAnalysis:
        """
        Analyze a student question to determine learning characteristics
        
        Args:
            question: The student's question
            
        Returns:
            IntentAnalysis object with classification results
        """
        try:
            logger.info(f"Analyzing intent for question: {question[:100]}...")
            
            prompt_text = INTENT_CLASSIFIER_PROMPT.format(question=question)
            messages = [HumanMessage(content=prompt_text)]

            response = await self._call_llm_with_fallback(messages)
            
            # Log raw response for debugging
            logger.debug(f"Raw LLM response: {response.content[:200]}")
            
            # Parse response with shared robust parser
            result = parse_llm_json(response.content)
            intent = _to_intent_analysis(result)
            
            logger.info(f"Intent analysis complete: {intent.difficulty_level}, {intent.question_type}")
            return intent
            
        except Exception as e:
            raw_response = response.content if 'response' in locals() else ''
            logger.error(f"Error in intent classification: {str(e)}")
            logger.error(f"Response content was: {raw_response or 'No response'}")

            partial = _extract_partial_intent_fields(raw_response)
            required = {
                "difficulty_level",
                "question_type",
                "requires_visuals",
                "requires_math",
                "requires_code",
                "key_concepts",
                "confidence",
            }
            if required.issubset(partial.keys()):
                try:
                    logger.warning("Recovered intent from partial malformed LLM output")
                    return _to_intent_analysis(partial)
                except Exception as parse_recovery_error:
                    logger.warning(f"Partial recovery failed: {parse_recovery_error}")

            # Fallback to safe defaults
            return IntentAnalysis(
                difficulty_level=DifficultyLevel.INTERMEDIATE,
                question_type=QuestionType.CONCEPTUAL,
                requires_visuals=True,
                requires_math=False,
                requires_code=False,
                key_concepts=[],
                confidence=0.5
            )
