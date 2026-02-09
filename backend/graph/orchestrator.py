"""
LangGraph Orchestrator - Coordinates all agents in a workflow
"""
import time
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from loguru import logger

from agents.intent_classifier import IntentClassifierAgent
from agents.search_agent import WebSearchAgent
from agents.content_extraction import ContentExtractionAgent
from agents.image_understanding import ImageUnderstandingAgent
from agents.teaching_synthesis import TeachingSynthesisAgent
from shared.schemas.models import (
    ResearchRequest, TeachingResponse, AgentState,
    SearchResult, Source, ImageData, SourceType
)
from config.settings import settings


class ResearchOrchestrator:
    """Orchestrates the multi-agent research and teaching workflow"""
    
    def __init__(self):
        # Initialize all agents
        self.intent_agent = IntentClassifierAgent()
        self.search_agent = WebSearchAgent()
        self.content_agent = ContentExtractionAgent()
        self.image_agent = ImageUnderstandingAgent()
        self.teaching_agent = TeachingSynthesisAgent()
        
        # Build the workflow graph
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Use the shared AgentState Pydantic model as the StateGraph schema
        workflow = StateGraph(AgentState)
        
        # Add nodes (agents)
        workflow.add_node("classify_intent", self.classify_intent_node)
        workflow.add_node("generate_queries", self.generate_queries_node)
        workflow.add_node("search_web", self.search_web_node)
        workflow.add_node("extract_content", self.extract_content_node)
        workflow.add_node("process_images", self.process_images_node)
        workflow.add_node("synthesize_teaching", self.synthesize_teaching_node)
        workflow.add_node("assess_quality", self.assess_quality_node)
        
        # Define the flow with parallelization
        workflow.add_edge("classify_intent", "generate_queries")
        workflow.add_edge("generate_queries", "search_web")
        workflow.add_edge("search_web", "extract_content")
        workflow.add_edge("search_web", "process_images")  # Parallel with extract_content
        workflow.add_edge("extract_content", "synthesize_teaching")
        workflow.add_edge("process_images", "synthesize_teaching")
        workflow.add_edge("synthesize_teaching", "assess_quality")
        
        # Conditional edge: retry if quality is low
        workflow.add_conditional_edges(
            "assess_quality",
            self.should_retry,
            {
                "retry": "generate_queries",  # Loop back for more research
                "complete": END
            }
        )
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        return workflow.compile()
    
    async def process_question(self, request: ResearchRequest) -> TeachingResponse:
        """
        Process a student question through the full workflow
        
        Args:
            request: ResearchRequest with student question
            
        Returns:
            Complete TeachingResponse
        """
        start_time = time.time()
        
        logger.info(f"Starting research workflow for: {request.question}")
        
        # Initialize state
        initial_state = AgentState(
            original_question=request.question,
            metadata={"start_time": start_time}
        )
        
        # Run the graph
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            # Extract teaching response from final state (handle both dict and Pydantic model)
            if isinstance(final_state, dict):
                metadata = final_state.get("metadata", {})
            else:
                metadata = final_state.metadata if hasattr(final_state, 'metadata') else {}
            
            teaching_response = metadata.get("teaching_response")
            
            if not teaching_response:
                logger.error(f"No teaching response in final state. Metadata keys: {metadata.keys()}")
                raise Exception("Teaching response not generated")
            
            # Set processing time
            teaching_response.processing_time = time.time() - start_time
            
            # Generate follow-up suggestions
            teaching_response.follow_up_suggestions = await self._generate_follow_ups(
                request.question,
                teaching_response.difficulty_level.value
            )
            
            logger.info(f"Workflow complete in {teaching_response.processing_time:.2f}s")
            return teaching_response
            
        except Exception as e:
            logger.error(f"Workflow error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    # ========================================
    # Node Functions
    # ========================================
    
    async def classify_intent_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Classify student intent and question characteristics"""
        logger.info("NODE: Classifying intent...")
        
        intent = await self.intent_agent.analyze(state["original_question"] if isinstance(state, dict) else state.original_question)
        
        return {"intent": intent}
    
    async def generate_queries_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Generate optimized search queries"""
        logger.info("NODE: Generating search queries...")
        
        # Handle both dict and Pydantic model
        if isinstance(state, dict):
            base_query = state["original_question"]
            intent = state.get("intent")
            metadata = state.get("metadata", {})
        else:
            base_query = state.original_question
            intent = state.intent
            metadata = state.metadata
        
        concepts = intent.key_concepts if intent else []
        
        queries = [
            base_query,
            f"{base_query} explanation beginner",
            f"{base_query} visual diagram",
            f"{' '.join(concepts[:2])} examples" if concepts else base_query,
        ]
        
        # Add specialized query based on type
        if intent:
            if intent.requires_math:
                queries.append(f"{base_query} formula derivation")
            if intent.requires_code:
                queries.append(f"{base_query} code example tutorial")
        
        metadata["search_queries"] = queries[:5]
        
        return {"metadata": metadata}
    
    async def search_web_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Execute web searches"""
        logger.info("NODE: Searching web...")
        
        if isinstance(state, dict):
            metadata = state.get("metadata", {})
            original_question = state["original_question"]
        else:
            metadata = state.metadata
            original_question = state.original_question
        
        queries = metadata.get("search_queries", [original_question])
        
        search_results = await self.search_agent.multi_query_search(queries)
        
        # Collect and aggressively deduplicate image URLs
        all_images = []
        seen_images = set()
        seen_domains = {}  # Track domain diversity
        
        for result in search_results:
            for img_url in result.images:
                # Normalize URL for better deduplication
                normalized_url = img_url.lower().split('?')[0]  # Remove query params
                
                if normalized_url not in seen_images:
                    # Extract domain for diversity
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(img_url).netloc
                        seen_domains[domain] = seen_domains.get(domain, 0) + 1
                    except:
                        domain = 'unknown'
                    
                    all_images.append(img_url)
                    seen_images.add(normalized_url)
        
        logger.info(f"Collected {len(all_images)} strongly deduplicated unique images from search results")
        metadata["raw_images"] = all_images[:10]  # Limit to top 10 for VLM processing (faster)
        
        return {"search_results": search_results, "metadata": metadata}
    
    async def extract_content_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Extract and clean content from sources"""
        logger.info("NODE: Extracting content...")
        
        if isinstance(state, dict):
            search_results = state.get("search_results", [])
            original_question = state["original_question"]
        else:
            search_results = state.search_results
            original_question = state.original_question
        
        extracted = await self.content_agent.process_multiple(
            search_results,
            original_question
        )
        
        # Create Source objects
        sources = []
        for idx, result in enumerate(search_results[:len(extracted)]):
            source = Source(
                title=result.title,
                url=result.url,
                snippet=extracted[idx][:200] if idx < len(extracted) else result.content[:200],
                domain=self._extract_domain(result.url),
                relevance_score=result.score,
                source_type=SourceType.ARTICLE
            )
            sources.append(source)
        
        return {"extracted_content": extracted, "sources": sources}
    
    async def process_images_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Analyze and rank images using VLM"""
        logger.info("NODE: Processing images with VLM...")
        
        if isinstance(state, dict):
            metadata = state.get("metadata", {})
            intent = state.get("intent")
            original_question = state["original_question"]
        else:
            metadata = state.metadata
            intent = state.intent
            original_question = state.original_question
        
        raw_images = metadata.get("raw_images", [])
        concepts = intent.key_concepts if intent else []

        # Fallback: if no images were found in the primary search, do a dedicated image search
        if not raw_images:
            logger.info("No images from primary search — running dedicated image search...")
            # Extract a short topic from the (possibly very long) question
            short_topic = original_question.strip().split('\n')[0][:120]
            # Remove any prompt instructions that leak into topic
            for prefix in ["Teach me about '", "Teach me about "]:
                if short_topic.startswith(prefix):
                    short_topic = short_topic[len(prefix):].rstrip("'").split("'")[0]
                    break
            try:
                image_query = f"{short_topic} diagram illustration"
                image_results = await self.search_agent.search(
                    query=image_query,
                    search_depth="basic",
                    include_images=True
                )
                for r in image_results:
                    for img_url in r.images:
                        normalized = img_url.lower().split('?')[0]
                        if normalized not in set(u.lower().split('?')[0] for u in raw_images):
                            raw_images.append(img_url)
                logger.info(f"Dedicated image search found {len(raw_images)} images for: {image_query[:80]}")
            except Exception as e:
                logger.warning(f"Dedicated image search failed: {e}")
        
        # Always process images if available, VLM will analyze and rank them
        if raw_images:
            images = await self.image_agent.process_images(
                raw_images,
                original_question,
                concepts,
                max_images=2  # Limit to exactly 2 best unique images
            )
            logger.info(f"Selected exactly {len(images)} unique images after VLM analysis")
        else:
            images = []
        
        return {"images": images}
    
    async def synthesize_teaching_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Synthesize teaching content"""
        logger.info("NODE: Synthesizing teaching content...")
        
        if isinstance(state, dict):
            original_question = state["original_question"]
            intent = state.get("intent")
            extracted_content = state.get("extracted_content", [])
            images = state.get("images", [])
            sources = state.get("sources", [])
            metadata = state.get("metadata", {})
        else:
            original_question = state.original_question
            intent = state.intent
            extracted_content = state.extracted_content
            images = state.images
            sources = state.sources
            metadata = state.metadata
        
        teaching_response = await self.teaching_agent.synthesize(
            question=original_question,
            intent=intent,
            extracted_content=extracted_content,
            images=images,
            sources=sources
        )
        
        metadata["teaching_response"] = teaching_response
        
        return {"metadata": metadata}
    
    async def assess_quality_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Assess quality of teaching response"""
        logger.info("NODE: Assessing quality...")
        
        if isinstance(state, dict):
            metadata = state.get("metadata", {})
        else:
            metadata = state.metadata
        
        teaching_response = metadata.get("teaching_response")
        
        # Simple quality assessment
        quality_score = 0.0
        
        if teaching_response:
            # Check completeness
            if teaching_response.tldr:
                quality_score += 0.2
            if teaching_response.explanation.content:
                quality_score += 0.3
            if teaching_response.analogy:
                quality_score += 0.2
            if teaching_response.sources:
                quality_score += 0.2
            if teaching_response.practice_questions:
                quality_score += 0.1
        
        logger.info(f"Quality score: {quality_score:.2f}")
        
        return {"quality_score": quality_score}
    
    def should_retry(self, state: AgentState) -> str:
        """Decide whether to retry or complete"""
        # Handle both dict and Pydantic model
        if isinstance(state, dict):
            quality_score = state.get("quality_score", 0.0)
            retries = state.get("retries", 0)
        else:
            quality_score = state.quality_score
            retries = state.retries
        
        # Accept any response with quality >= 0.3 (has at least TL;DR + explanation)
        # Only retry if completely broken (< 0.2) or missing critical parts
        if quality_score < 0.2 and retries < settings.max_retries:
            retries += 1
            logger.warning(f"Very low quality ({quality_score:.2f}), retrying ({retries}/{settings.max_retries})...")
            return "retry"
        
        logger.info(f"Accepting response with quality score: {quality_score:.2f}")
        return "complete"
    
    # ========================================
    # Helper Functions
    # ========================================
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc
            return domain.replace('www.', '')
        except:
            return url
    
    async def _generate_follow_ups(self, question: str, difficulty: str) -> List[str]:
        """Generate follow-up question suggestions"""
        # Simple follow-up generation
        follow_ups = [
            f"Can you explain more about the key concepts in {question}?",
            f"What are some practical applications of this?",
            f"How does this relate to other topics?"
        ]
        
        return follow_ups[:3]
