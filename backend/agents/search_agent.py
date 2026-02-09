"""
Web Search Agent - Performs intelligent web searches using Tavily API
"""
from typing import List, Dict, Any
from tavily import TavilyClient
from loguru import logger

from config.settings import settings
from shared.schemas.models import SearchResult


class WebSearchAgent:
    """Performs intelligent web searches and ranks results"""
    
    def __init__(self):
        self.client = TavilyClient(api_key=settings.tavily_api_key)
        self.max_results = settings.max_search_results
        
    async def search(
        self, 
        query: str, 
        search_depth: str = "advanced",
        include_images: bool = True
    ) -> List[SearchResult]:
        """
        Search the web for relevant educational content
        
        Args:
            query: Search query
            search_depth: 'basic' or 'advanced'
            include_images: Whether to include images
            
        Returns:
            List of SearchResult objects
        """
        try:
            logger.info(f"Searching Tavily: {query}")
            
            response = self.client.search(
                query=query,
                search_depth=search_depth,
                max_results=self.max_results,
                include_images=include_images,
                include_answer=True,
                include_raw_content=True
            )
            
            results = []
            for item in response.get("results", []):
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.5),
                    images=[]
                )
                results.append(result)
            
            # Add images to top result if available
            if include_images and response.get("images"):
                if results:
                    results[0].images = response["images"][:settings.max_images_per_response]
            
            logger.info(f"Found {len(results)} search results")
            return results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
    
    async def multi_query_search(self, queries: List[str]) -> List[SearchResult]:
        """
        Execute multiple search queries and combine results
        
        Args:
            queries: List of search queries
            
        Returns:
            Combined and deduplicated search results
        """
        all_results = []
        seen_urls = set()
        
        for query in queries:
            results = await self.search(query)
            for result in results:
                if result.url not in seen_urls:
                    all_results.append(result)
                    seen_urls.add(result.url)
        
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Multi-query search: {len(queries)} queries → {len(all_results)} unique results")
        return all_results[:self.max_results]
