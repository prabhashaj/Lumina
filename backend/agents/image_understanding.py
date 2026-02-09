"""
Image Understanding Agent - Uses VLM to caption and rank images
"""
from typing import List, Dict, Any
import replicate
from loguru import logger

from config.settings import settings
from shared.schemas.models import ImageData
from shared.prompts.templates import IMAGE_CAPTION_PROMPT


class ImageUnderstandingAgent:
    """Understands and captions images using Vision Language Models"""
    
    def __init__(self):
        self.replicate_token = settings.replicate_api_token
        if self.replicate_token:
            replicate.Client(api_token=self.replicate_token)
        
    async def analyze_image(
        self,
        image_url: str,
        topic: str,
        concepts: List[str]
    ) -> ImageData:
        """
        Analyze an image using VLM for educational relevance and detailed understanding
        
        Args:
            image_url: URL of the image
            topic: The topic being taught
            concepts: Key concepts to consider
            
        Returns:
            ImageData with VLM-generated caption and relevance score
        """
        try:
            logger.info(f"Analyzing image with VLM: {image_url[:60]}...")
            
            if not self.replicate_token:
                logger.warning("No Replicate API token - using basic image analysis")
                # Fallback: Create basic image data without VLM
                return ImageData(
                    url=image_url,
                    caption=f"Visual diagram or illustration related to {topic}",
                    relevance_score=0.6,
                    alt_text=f"Educational image about {topic}"
                )
            
            # Use VLM (LLaVA) for detailed image understanding
            prompt = f"""You are an educational AI analyzing this image for a lesson about: {topic}

Key concepts to look for: {', '.join(concepts[:5])}

Analyze this image and respond with:
1. DETAILED DESCRIPTION: What exactly is shown in the image? (diagrams, charts, text, illustrations, examples)
2. EDUCATIONAL VALUE: How does this help understand {topic}?
3. RELEVANCE SCORE: Rate 0.0-1.0 how relevant this is for learning {topic}
4. KEY INSIGHT: What's the main thing a student learns from this image?

Be specific about charts, diagrams, formulas, or visual elements you see."""

            try:
                # Call Replicate API with LLaVA model for vision understanding
                import replicate
                output = replicate.run(
                    "yorickvp/llava-13b:b5f6212d032508382d61ff00469ddda3e32fd8a0e75dc39d8a4191bb742157fb",
                    input={
                        "image": image_url,
                        "prompt": prompt,
                        "max_tokens": 300
                    }
                )
                
                # Concatenate output (generator)
                vlm_response = "".join(output)
                logger.info(f"VLM analysis: {vlm_response[:150]}...")
                
                # Parse relevance score from response
                relevance_score = 0.7  # Default
                if "relevance" in vlm_response.lower():
                    import re
                    score_match = re.search(r'(0\.[0-9]+|1\.0|0|1)', vlm_response)
                    if score_match:
                        relevance_score = float(score_match.group(1))
                
                # Use VLM description as caption
                caption = vlm_response[:300].strip()
                
                return ImageData(
                    url=image_url,
                    caption=caption,
                    relevance_score=min(relevance_score, 1.0),
                    alt_text=f"Educational visualization: {caption[:100]}",
                    source_url=image_url
                )
                
            except Exception as vlm_error:
                logger.warning(f"VLM API call failed: {str(vlm_error)}. Using fallback.")
                # Intelligent fallback based on concepts
                caption = f"Visual explanation showing {' and '.join(concepts[:2])} related to {topic}"
                return ImageData(
                    url=image_url,
                    caption=caption,
                    relevance_score=0.65,
                    alt_text=caption
                )
            
        except Exception as e:
            logger.error(f"Image analysis error: {str(e)}")
            # Final fallback with lower relevance
            return ImageData(
                url=image_url,
                caption=f"Diagram or chart related to {topic}",
                relevance_score=0.5,
                alt_text="Educational image"
            )
    
    async def process_images(
        self,
        image_urls: List[str],
        topic: str,
        concepts: List[str],
        max_images: int = None
    ) -> List[ImageData]:
        """
        Process multiple images with VLM and rank by relevance
        
        Args:
            image_urls: List of unique image URLs (already deduplicated)
            topic: Topic being taught
            concepts: Key concepts
            max_images: Maximum best images to return (default: 2)
            
        Returns:
            Sorted list of best ImageData by VLM relevance analysis
        """
        import asyncio
        
        if not image_urls:
            return []
        
        max_images = max_images or 2  # Default to 2 best images
        
        # Process fewer images for speed, focus on quality and diversity
        process_count = min(len(image_urls), 6)  # Process 6 images max for speed
        
        logger.info(f"Processing {process_count} images with VLM analysis (parallel)...")
        
        # STRONG deduplication by extracting unique image identifiers
        unique_urls = []
        seen_paths = set()
        seen_domains = {}
        
        for url in image_urls[:process_count * 2]:  # Look at more candidates
            # Extract filename/path for deduplication
            path_part = url.split('/')[-1].split('?')[0].lower()
            
            # Extract domain for diversity
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                domain_count = seen_domains.get(domain, 0)
            except:
                domain = 'unknown'
                domain_count = 0
            
            # Only add if unique path and reasonable domain diversity
            if path_part not in seen_paths and domain_count < 2:
                unique_urls.append(url)
                seen_paths.add(path_part)
                seen_domains[domain] = domain_count + 1
                
                if len(unique_urls) >= process_count:
                    break
        
        logger.info(f"Selected {len(unique_urls)} strongly unique URLs for VLM processing")
        
        # Process images in parallel with VLM
        tasks = [
            self.analyze_image(url, topic, concepts)
            for url in unique_urls[:6]
        ]
        
        image_data = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter valid results with good relevance scores
        valid_images = [
            img for img in image_data
            if isinstance(img, ImageData) and img.relevance_score > 0.5
        ]
        
        # Sort by VLM relevance score (highest first)
        valid_images.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Return EXACTLY 2 best unique images
        best_images = valid_images[:2]
        
        logger.info(f"VLM selected exactly {len(best_images)} unique images from {len(image_urls)} candidates")
        for idx, img in enumerate(best_images, 1):
            logger.info(f"  Image #{idx}: Score {img.relevance_score:.2f} - URL: {img.url[:80]}")
            logger.info(f"           Caption: {img.caption[:100]}")
        
        return best_images
