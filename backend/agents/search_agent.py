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
            tavily_images = response.get("images", [])
            logger.info(f"Tavily returned {len(tavily_images)} images for query: {query[:80]}")
            if include_images and tavily_images:
                if results:
                    results[0].images = tavily_images[:settings.max_images_per_response]
            
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
        all_image_urls: List[str] = []
        seen_image_urls = set()
        
        for query in queries:
            results = await self.search(query)
            for result in results:
                # Collect images from every result before deduplication
                for img_url in result.images:
                    normalized = img_url.lower().split('?')[0]
                    if normalized not in seen_image_urls:
                        all_image_urls.append(img_url)
                        seen_image_urls.add(normalized)

                if result.url not in seen_urls:
                    all_results.append(result)
                    seen_urls.add(result.url)
        
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Ensure images are attached to the top result so the orchestrator finds them
        top_results = all_results[:self.max_results]
        if all_image_urls and top_results:
            # Merge collected images into the first result
            existing = set((u.lower().split('?')[0]) for u in top_results[0].images)
            for img_url in all_image_urls:
                if img_url.lower().split('?')[0] not in existing:
                    top_results[0].images.append(img_url)
                    existing.add(img_url.lower().split('?')[0])
        
        logger.info(f"Multi-query search: {len(queries)} queries → {len(top_results)} unique results, {len(all_image_urls)} images collected")
        return top_results
