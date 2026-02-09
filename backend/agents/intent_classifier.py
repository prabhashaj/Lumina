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
        # Priority: Mistral > Groq > OpenAI
        if settings.mistral_api_key:
            self.llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.0,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1"
            )
        elif settings.groq_api_key:
            self.llm = ChatOpenAI(
                model=settings.groq_model,
                temperature=0.0,
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        else:
            self.llm = ChatOpenAI(
                model=settings.primary_llm_model,
                temperature=0.0,
                api_key=settings.openai_api_key
            )
        
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

            response = await self.llm.ainvoke(messages)
            
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
