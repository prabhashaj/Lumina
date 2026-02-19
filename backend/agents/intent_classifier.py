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


def extract_json_from_response(content: str) -> dict:
    """Extract JSON from response, handling markdown code blocks"""
    content = content.strip()
    
    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        content = json_match.group(1)
    
    # Try direct JSON parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        raise


class IntentClassifierAgent:
    """Analyzes student questions to determine difficulty, intent, and learning needs"""
    
    def __init__(self):
        # Use OpenRouter Mistral Small (primary), then Mistral API Medium (backup)
        self.llm = None
        self.backup_llm = None
        
        if settings.openrouter_api_key:
            logger.info("Intent Classifier: Using Mistral Small via OpenRouter")
            self.llm = ChatOpenAI(
                model=settings.openrouter_model,
                temperature=0.0,
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                max_tokens=500  # Small response for classification
            )
            # Set backup to Mistral API if available
            if settings.mistral_api_key:
                self.backup_llm = ChatOpenAI(
                    model=settings.mistral_model,
                    temperature=0.0,
                    api_key=settings.mistral_api_key,
                    base_url="https://api.mistral.ai/v1",
                    max_tokens=500
                )
        elif settings.mistral_api_key:
            logger.info("Intent Classifier: Using Mistral Medium via Mistral API")
            self.llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.0,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
                max_tokens=500
            )
        
        if not self.llm:
            raise ValueError("No valid API key found. Please set OPENROUTER_API_KEY or MISTRAL_API_KEY")

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
            
            # Parse response with robust JSON extraction
            result = extract_json_from_response(response.content)
            
            intent = IntentAnalysis(
                difficulty_level=DifficultyLevel(result["difficulty_level"]),
                question_type=QuestionType(result["question_type"]),
                requires_visuals=result["requires_visuals"],
                requires_math=result["requires_math"],
                requires_code=result["requires_code"],
                key_concepts=result["key_concepts"],
                confidence=result["confidence"]
            )
            
            logger.info(f"Intent analysis complete: {intent.difficulty_level}, {intent.question_type}")
            return intent
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            logger.error(f"Response content was: {response.content if 'response' in locals() else 'No response'}")
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
        except Exception as e:
            logger.error(f"Error in intent classification: {str(e)}")
            logger.error(f"Response content was: {response.content if 'response' in locals() else 'No response'}")
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
