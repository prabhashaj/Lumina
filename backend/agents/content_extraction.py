"""
Content Extraction Agent - Extracts and processes relevant content from sources
"""
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from bs4 import BeautifulSoup
import requests
from loguru import logger

from config.settings import settings
from shared.prompts.templates import CONTENT_EXTRACTION_PROMPT
from shared.schemas.models import SearchResult


class ContentExtractionAgent:
    """Extracts and cleans educational content from web sources"""
    
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
                model=settings.fallback_llm_model,
                temperature=0.0,
                api_key=settings.openai_api_key
            )
        
    async def extract_content(
        self, 
        search_result: SearchResult,
        topic: str
    ) -> str:
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
                return ""
            
            # Use LLM to extract most relevant parts
            prompt_text = CONTENT_EXTRACTION_PROMPT.format(
                topic=topic,
                content=content[:4000]  # Limit to avoid token limits
            )
            messages = [HumanMessage(content=prompt_text)]

            response = await self.llm.ainvoke(messages)
            extracted = response.content.strip()
            
            logger.info(f"Extracted {len(extracted)} chars from {search_result.url}")
            return extracted
            
        except Exception as e:
            logger.error(f"Content extraction error: {str(e)}")
            return search_result.content  # Fallback to original
    
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
        
        tasks = [
            self.extract_content(result, topic)
            for result in top_results
        ]
        
        extracted_contents = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors and empty content
        valid_content = [
            content for content in extracted_contents
            if isinstance(content, str) and len(content) > 50
        ]
        
        logger.info(f"Processed {len(top_results)} sources → {len(valid_content)} valid extractions")
        return valid_content
