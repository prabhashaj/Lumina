"""
Content Extraction Agent - Extracts and processes relevant content from sources
"""
import asyncio
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from bs4 import BeautifulSoup
import requests
from loguru import logger

from config.settings import settings
from shared.prompts.templates import CONTENT_EXTRACTION_PROMPT, COMPARATIVE_EXTRACTION_PROMPT
from shared.schemas.models import SearchResult


class ContentExtractionAgent:
    """Extracts and cleans educational content from web sources"""
    
    def __init__(self):
        # Use Mistral API only.
        self.llm = None
        self.backup_llm = None

        if settings.mistral_api_key:
            logger.info("Content Extraction: Using Mistral API")
            self.llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.0,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
                max_tokens=3000
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
                logger.warning(f"Primary LLM failed, using backup Mistral API")
                return await self.backup_llm.ainvoke(messages)
            raise
        
    @staticmethod
    def _is_comparison_query(topic: str) -> bool:
        """Detect if topic is a comparison/contrast query."""
        q = (topic or "").strip().lower()
        comparison_keywords = [
            "compare", "versus", "vs", "contrast", "difference", 
            "trade-off", "tradeoff", "pros and cons", "advantage",
            "better", "worse", "similar", "distinguish",
            "which is", "what's the difference", "how do they differ"
        ]
        return any(keyword in q for keyword in comparison_keywords)

    async def extract_content(
        self, 
        search_result: SearchResult,
        topic: str
    ) -> tuple[str, bool]:
        """
        Extract relevant educational content from a search result
        
        Args:
            search_result: Search result to extract from
            topic: The topic/question being researched
            
        Returns:
            Extracted and cleaned content
        """
        try:
            # Use the content from Tavily (already cleaned)
            content = search_result.content
            
            if not content or len(content) < 100:
                logger.warning(f"Short/missing content from {search_result.url}")
                return "", False
            
            # Use LLM to extract most relevant parts
            # Choose prompt based on query type
            if self._is_comparison_query(topic):
                logger.info(f"Using comparative extraction for: {topic[:60]}")
                extraction_prompt = COMPARATIVE_EXTRACTION_PROMPT.format(
                    topic=topic,
                    query=topic,
                    content=content[:4000]
                )
            else:
                extraction_prompt = CONTENT_EXTRACTION_PROMPT.format(
                    topic=topic,
                    content=content[:4000]  # Limit to avoid token limits
                )
            
            messages = [HumanMessage(content=extraction_prompt)]

            extraction_timeout = max(
                10,
                int(getattr(settings, "content_extraction_timeout_seconds", 30)),
            )
            response = await asyncio.wait_for(
                self._call_llm_with_fallback(messages),
                timeout=extraction_timeout,
            )
            extracted = response.content.strip()
            
            logger.info(f"Extracted {len(extracted)} chars from {search_result.url}")
            return extracted, True

        except asyncio.TimeoutError:
            logger.warning(f"Content extraction timed out for {search_result.url}; using raw snippet fallback")
            return search_result.content[:1200], False
            
        except Exception as e:
            logger.error(f"Content extraction error: {str(e)}")
            return search_result.content, False  # Fallback to original
    
    async def process_multiple(
        self,
        search_results: List[SearchResult],
        topic: str,
        max_sources: int = 5
    ) -> List[str]:
        """
        Process multiple search results in parallel
        
        Args:
            search_results: List of search results
            topic: Topic being researched
            max_sources: Maximum sources to process
            
        Returns:
            List of extracted content strings
        """
        import asyncio
        
        # Process top results
        top_results = search_results[:max_sources]
        
        tasks = [self.extract_content(result, topic) for result in top_results]

        extracted_contents = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out errors and empty content while preserving successful order.
        valid_content = []
        for content in extracted_contents:
            if isinstance(content, tuple):
                text, _used_fallback = content
            elif isinstance(content, str):
                text = content
            else:
                continue

            if isinstance(text, str) and len(text) > 50:
                valid_content.append(text)
        
        logger.info(f"Processed {len(top_results)} sources → {len(valid_content)} valid extractions")
        return valid_content
