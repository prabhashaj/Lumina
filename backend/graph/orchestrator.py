"""
LangGraph Orchestrator - Coordinates all agents in a workflow
"""
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Tuple
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from loguru import logger

from agents.intent_classifier import IntentClassifierAgent
from agents.search_agent import WebSearchAgent
from agents.content_extraction import ContentExtractionAgent
from agents.teaching_synthesis import TeachingSynthesisAgent
from agents.search_router import SearchRouter, SearchPlan, SearchComplexity
from shared.schemas.models import (
    ResearchRequest, TeachingResponse, AgentState,
    SearchResult, Source, ImageData, SourceType, IntentAnalysis
)
from config.settings import settings
from config.optimization_config import (
    get_pecar_config, get_latency_budget, get_synthesis_timeout, 
    get_search_depth, get_complexity_category
)
from pecar.orchestrator import PeCAR
from pecar.models import DepthConfig, LearnerProfile, LearningMode, PecarIntentAnalysis


# TypedDict schema for LangGraph StateGraph (LangGraph requires TypedDict, not Pydantic)
class GraphState(TypedDict, total=False):
    original_question: str
    intent: Optional[IntentAnalysis]
    search_query: Optional[str]
    search_results: List[SearchResult]
    extracted_content: List[str]
    images: List[ImageData]
    teaching_content: Optional[str]
    sources: List[Source]
    retries: int
    quality_score: float
    errors: List[str]
    metadata: Dict[str, Any]
    # PeCAR fields
    pecar_output: Optional[Dict[str, Any]]
    learning_mode: str
    learner_profile: Optional[Dict[str, Any]]


class ResearchOrchestrator:
    """Orchestrates the multi-agent research and teaching workflow"""
    
    def __init__(self):
        # Initialize all agents
        self.intent_agent = IntentClassifierAgent()
        self.search_agent = WebSearchAgent()
        self.content_agent = ContentExtractionAgent()
        self.teaching_agent = TeachingSynthesisAgent()
        self.search_router = SearchRouter()
        
        # Build the workflow graph
        self.graph = self._build_graph()

    def _emit_progress(self, state: AgentState, message: str) -> None:
        """Emit internal workflow progress for streaming/debug visibility."""
        try:
            metadata = state.get("metadata", {}) if isinstance(state, dict) else getattr(state, "metadata", {})
            callback = metadata.get("_progress_callback") if isinstance(metadata, dict) else None
            if callback:
                callback(message)
        except Exception:
            # Progress updates should never break the workflow.
            pass

    @staticmethod
    def _normalize_learning_mode(learning_mode: str) -> str:
        """Normalize learning mode to a supported enum value."""
        mode = str(learning_mode or "").strip().lower()
        valid_modes = {m.value for m in LearningMode}
        return mode if mode in valid_modes else LearningMode.RESEARCH.value

    @staticmethod
    def _extract_intent_features(intent: Optional[IntentAnalysis]) -> Dict[str, Any]:
        """Extract normalized intent features used for PeCAR routing decisions."""
        if not intent:
            return {
                "complexity": 0.5,
                "question_type": "conceptual",
                "pecar_question_type": "conceptual",
                "requires_math": False,
                "requires_code": False,
                "requires_visuals": False,
                "key_concepts_count": 0,
            }

        question_type = getattr(intent, "question_type", "conceptual")
        if hasattr(question_type, "value"):
            question_type = question_type.value

        key_concepts = getattr(intent, "key_concepts", []) or []

        return {
            "complexity": float(getattr(intent, "complexity_score", 0.5) or 0.5),
            "question_type": str(question_type).lower(),
            "pecar_question_type": str(getattr(intent, "pecar_question_type", "conceptual")).lower(),
            "requires_math": bool(getattr(intent, "requires_math", False)),
            "requires_code": bool(getattr(intent, "requires_code", False)),
            "requires_visuals": bool(getattr(intent, "requires_visuals", False)),
            "key_concepts_count": len(key_concepts),
        }

    def _should_run_pecar(
        self,
        *,
        learning_mode: str,
        intent: Optional[IntentAnalysis],
        original_question: str,
        extracted_content: List[str],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Decide if PeCAR should run for this query to balance quality and latency."""
        mode = self._normalize_learning_mode(learning_mode)
        features = self._extract_intent_features(intent)

        complexity = features["complexity"]
        question_type = features["question_type"]
        pecar_question_type = features["pecar_question_type"]
        requires_math = features["requires_math"]
        requires_code = features["requires_code"]
        requires_visuals = features["requires_visuals"]
        key_concepts_count = features["key_concepts_count"]
        question_text = (original_question or "").strip()
        question_chars = len(question_text)
        question_lower = question_text.lower()

        complexity_markers = {
            "compare",
            "trade-off",
            "tradeoff",
            "complexity",
            "algorithm",
            "dynamic programming",
            "recursion",
            "derive",
            "prove",
            "implement",
            "pitfall",
            "mistake",
            "optimiz",
            "design",
            "evaluate",
        }
        keyword_reasoning = any(marker in question_lower for marker in complexity_markers)

        reasoning_heavy = (
            pecar_question_type in {"procedural", "evaluative"}
            or question_type in {"practical", "mathematical", "mixed"}
            or requires_math
            or requires_code
            or keyword_reasoning
        )
        short_simple = (
            question_chars < settings.pecar_simple_question_chars
            and not reasoning_heavy
            and complexity < settings.pecar_general_complexity_threshold
        )
        has_context = bool(extracted_content)

        decision_meta = {
            "mode": mode,
            "complexity": round(complexity, 3),
            "question_type": question_type,
            "pecar_question_type": pecar_question_type,
            "requires_math": requires_math,
            "requires_code": requires_code,
            "requires_visuals": requires_visuals,
            "reasoning_heavy": reasoning_heavy,
            "keyword_reasoning": keyword_reasoning,
            "question_chars": question_chars,
            "key_concepts_count": key_concepts_count,
        }

        if not has_context:
            return False, "no extracted context available", decision_meta

        if short_simple:
            return False, "short low-complexity question", decision_meta

        if mode == LearningMode.RESEARCH.value:
            high_complexity = complexity >= settings.pecar_research_complexity_threshold
            concept_density = key_concepts_count >= 3 and question_chars >= settings.pecar_simple_question_chars
            should_run = high_complexity or (reasoning_heavy and concept_density) or (reasoning_heavy and question_chars >= settings.pecar_simple_question_chars)
            reason = "complex research reasoning required" if should_run else "research query is likely direct/extractive"
            return should_run, reason, decision_meta

        if mode in {LearningMode.EXAM_PREP.value, LearningMode.PERSONALIZED.value, LearningMode.VIDEO_LECTURE.value}:
            should_run = reasoning_heavy or complexity >= settings.pecar_general_complexity_threshold
            reason = "mode favors structured pedagogy" if should_run else "question is simple for this mode"
            return should_run, reason, decision_meta

        if mode == LearningMode.DOUBT_SOLVER.value:
            should_run = reasoning_heavy and complexity >= settings.pecar_general_complexity_threshold
            reason = "complex doubt needs deeper reasoning" if should_run else "doubt can be answered directly"
            return should_run, reason, decision_meta

        should_run = reasoning_heavy or complexity >= settings.pecar_general_complexity_threshold
        reason = "default complexity trigger" if should_run else "default direct response path"
        return should_run, reason, decision_meta

    def _compute_pecar_budget(
        self,
        intent: Optional[IntentAnalysis],
        decision_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        """Compute PeCAR budgets from intent complexity using optimization config."""
        features = self._extract_intent_features(intent)
        complexity = features["complexity"]
        
        # Get optimized configuration based on complexity
        pecar_config = get_pecar_config(complexity)
        synthesis_timeout = get_synthesis_timeout(complexity)
        search_depth = get_search_depth(complexity)
        
        budget = {
            "max_paths": pecar_config.get("max_paths", 1),
            "max_steps": pecar_config.get("max_steps", 5),
            "context_chars": settings.pecar_context_chars if complexity >= 0.65 else 3200,
            "timeout_seconds": settings.pecar_timeout_seconds if pecar_config.get("enabled") else 0,
            "max_sources": settings.extraction_max_sources,
            "synthesis_timeout": synthesis_timeout,
            "search_depth": search_depth,
        }
        
        logger.info(f"PeCAR budget for complexity {complexity:.2f}: {budget}")
        return budget
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Use TypedDict-based GraphState for LangGraph compatibility
        workflow = StateGraph(GraphState)
        
        # Add nodes (agents)
        workflow.add_node("classify_intent", self.classify_intent_node)
        workflow.add_node("plan_search", self.plan_search_node)
        workflow.add_node("generate_queries", self.generate_queries_node)
        workflow.add_node("search_web", self.search_web_node)
        workflow.add_node("extract_content", self.extract_content_node)
        workflow.add_node("select_images", self.select_images_node)
        workflow.add_node("pecar_reasoning", self.pecar_reasoning_node)
        workflow.add_node("synthesize_teaching", self.synthesize_teaching_node)
        workflow.add_node("assess_quality", self.assess_quality_node)

        # Define the flow (sequential pipeline with PeCAR between images and synthesis)
        workflow.add_edge("classify_intent", "plan_search")
        workflow.add_edge("plan_search", "generate_queries")
        workflow.add_edge("generate_queries", "search_web")
        workflow.add_edge("search_web", "extract_content")
        workflow.add_edge("extract_content", "select_images")
        workflow.add_edge("select_images", "pecar_reasoning")
        workflow.add_edge("pecar_reasoning", "synthesize_teaching")
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
    
    async def process_question(
        self,
        request: ResearchRequest,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> TeachingResponse:
        """
        Process a student question through the full workflow
        
        Args:
            request: ResearchRequest with student question
            
        Returns:
            Complete TeachingResponse
        """
        start_time = time.time()
        
        logger.info(f"Starting research workflow for: {request.question}")
        
        # Initialize state as dict (LangGraph StateGraph requires dict input)
        initial_state = {
            "original_question": request.question,
            "intent": None,
            "search_query": None,
            "search_results": [],
            "extracted_content": [],
            "images": [],
            "teaching_content": None,
            "sources": [],
            "retries": 0,
            "quality_score": 0.0,
            "errors": [],
            "metadata": {
                "start_time": start_time,
                "_progress_callback": progress_callback,
            },
            # PeCAR fields
            "pecar_output": None,
            "learning_mode": getattr(request, "learning_mode", "research"),
            "learner_profile": getattr(request, "learner_profile", None),
        }
        
        # Run the graph
        try:
            if progress_callback:
                progress_callback("Starting research workflow...")

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

            if progress_callback:
                progress_callback("Final answer ready")
            
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
        self._emit_progress(state, "Classifying question intent...")
        
        intent = await self.intent_agent.analyze(state["original_question"] if isinstance(state, dict) else state.original_question)
        
        return {"intent": intent}

    async def plan_search_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Use SearchRouter to create an optimised SearchPlan (zero LLM cost)."""
        logger.info("NODE: Planning search strategy...")
        self._emit_progress(state, "Planning search strategy...")

        if isinstance(state, dict):
            query = state["original_question"]
            intent = state.get("intent")
            metadata = state.get("metadata", {})
        else:
            query = state.original_question
            intent = state.intent
            metadata = state.metadata

        plan = self.search_router.plan(query, intent)

        # Serialise plan into metadata so downstream nodes can read it
        metadata["search_plan"] = plan
        metadata["search_complexity"] = plan.complexity.value

        return {"metadata": metadata}
    
    async def generate_queries_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Generate search queries – count is controlled by the SearchPlan."""
        logger.info("NODE: Generating search queries...")
        self._emit_progress(state, "Generating optimized search queries...")

        if isinstance(state, dict):
            base_query = state["original_question"]
            intent = state.get("intent")
            metadata = state.get("metadata", {})
        else:
            base_query = state.original_question
            intent = state.intent
            metadata = state.metadata

        plan: SearchPlan = metadata.get("search_plan")

        if plan:
            queries = self.search_router.generate_queries(base_query, intent, plan)
        else:
            # Fallback to simple single query
            queries = [base_query]

        queries = queries[: settings.max_search_queries]

        metadata["search_queries"] = queries
        logger.info(f"Generated {len(queries)} search queries (plan: {plan.complexity.value if plan else 'none'})")

        return {"metadata": metadata}
    
    async def search_web_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Execute web searches using plan-aware agent."""
        logger.info("NODE: Searching web...")

        if isinstance(state, dict):
            metadata = state.get("metadata", {})
            original_question = state["original_question"]
        else:
            metadata = state.metadata
            original_question = state.original_question

        queries = metadata.get("search_queries", [original_question])
        plan: SearchPlan = metadata.get("search_plan")
        query_label = "query" if len(queries) == 1 else "queries"
        self._emit_progress(state, f"Searching web sources ({len(queries)} {query_label})...")

        search_results = await self.search_agent.multi_query_search(queries, plan=plan)
        
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
        metadata["raw_images"] = all_images[:6]  # Limit to top 6 candidates
        
        return {"search_results": search_results, "metadata": metadata}
    
    async def extract_content_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Extract and clean content from sources"""
        logger.info("NODE: Extracting content...")
        self._emit_progress(state, "Extracting relevant content from sources...")
        
        if isinstance(state, dict):
            search_results = state.get("search_results", [])
            original_question = state["original_question"]
        else:
            search_results = state.search_results
            original_question = state.original_question
        
        max_sources = max(1, min(settings.max_search_results, settings.extraction_max_sources))

        extracted = await self.content_agent.process_multiple(
            search_results,
            original_question,
            max_sources=max_sources,
        )
        
        # Create Source objects
        sources = []
        for idx, result in enumerate(search_results[:max_sources]):
            snippet = extracted[idx][:200] if idx < len(extracted) else result.content[:200]
            source = Source(
                title=result.title,
                url=result.url,
                snippet=snippet,
                domain=self._extract_domain(result.url),
                relevance_score=result.score,
                source_type=SourceType.ARTICLE
            )
            sources.append(source)
        
        return {"extracted_content": extracted, "sources": sources}
    
    async def select_images_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Select top images from Tavily results (no VLM analysis needed)"""
        logger.info("NODE: Selecting images from search results...")
        self._emit_progress(state, "Selecting visual references...")
        
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

        # Extract a clean, short topic for image search
        clean_topic = original_question.strip().split('\n')[0][:120]
        for prefix in ["Teach me about '", "Teach me about "]:
            if clean_topic.startswith(prefix):
                clean_topic = clean_topic[len(prefix):].rstrip("'").split("'")[0]
                break
        for marker in [" CRITICAL ", " TEACHING INSTRUCTIONS", " PERSONALIZATION", " Rules:", " Generate "]:
            if marker in clean_topic:
                clean_topic = clean_topic[:clean_topic.index(marker)].strip()
        if not clean_topic:
            clean_topic = " ".join(concepts[:3]) if concepts else "topic"

        # Fallback: if no images from primary search, do dedicated image search
        if not raw_images:
            logger.info("No images from primary search — running dedicated image search...")
            try:
                image_query = f"{clean_topic} diagram illustration"
                from agents.search_router import SearchPlan, SearchComplexity
                img_plan = SearchPlan(
                    complexity=SearchComplexity.SIMPLE,
                    search_depth="basic",
                    max_results=3,
                    num_queries=1,
                    include_raw_content=False,
                    include_images=True,
                    include_answer=False,
                    context_budget_chars=2000,
                )
                image_results = await self.search_agent.search(
                    query=image_query,
                    plan=img_plan,
                )
                for r in image_results:
                    for img_url in r.images:
                        normalized = img_url.lower().split('?')[0]
                        if normalized not in set(u.lower().split('?')[0] for u in raw_images):
                            raw_images.append(img_url)
                logger.info(f"Dedicated image search found {len(raw_images)} images")
            except Exception as e:
                logger.warning(f"Dedicated image search failed: {e}")
        
        # Select top 2-3 unique images (Tavily already ranks by relevance)
        images = []
        if raw_images:
            seen_urls = set()
            for img_url in raw_images[:6]:  # Look at top 6 candidates
                normalized = img_url.lower().split('?')[0]
                if normalized not in seen_urls:
                    seen_urls.add(normalized)
                    images.append(ImageData(
                        url=img_url,
                        caption=f"Visual illustration related to {clean_topic}",
                        relevance_score=0.8  # Tavily pre-filters for relevance
                    ))
                    if len(images) >= 2:  # Limit to 2 images
                        break
            logger.info(f"Selected {len(images)} unique images from Tavily results")
        
        return {"images": images}
    
    async def pecar_reasoning_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Run PeCAR 6-stage reasoning pipeline on extracted content"""
        logger.info("NODE: Running PeCAR reasoning pipeline...")
        self._emit_progress(state, "Evaluating whether deep reasoning (PeCAR) is needed...")

        if isinstance(state, dict):
            original_question = state["original_question"]
            intent = state.get("intent")
            extracted_content = state.get("extracted_content", [])
            sources = state.get("sources", [])
            metadata = state.get("metadata", {})
            learner_profile = state.get("learner_profile")
            learning_mode = state.get("learning_mode", "research")
        else:
            original_question = state.original_question
            intent = state.intent
            extracted_content = state.extracted_content
            sources = state.sources
            metadata = state.metadata
            learner_profile = getattr(state, "learner_profile", None)
            learning_mode = getattr(state, "learning_mode", "research")

        if not settings.pecar_enabled:
            metadata["pecar_error"] = "PeCAR disabled by configuration"
            logger.info("PeCAR skipped: disabled by configuration")
            return {"metadata": metadata, "pecar_output": None}

        should_run_pecar, decision_reason, decision_meta = self._should_run_pecar(
            learning_mode=learning_mode,
            intent=intent,
            original_question=original_question,
            extracted_content=extracted_content,
        )
        decision_meta["run"] = should_run_pecar
        decision_meta["reason"] = decision_reason
        metadata["pecar_decision"] = decision_meta

        if not should_run_pecar:
            metadata["pecar_error"] = f"PeCAR skipped: {decision_reason}"
            logger.info(
                "PeCAR skipped: {} | mode={} complexity={} qtype={}",
                decision_reason,
                decision_meta["mode"],
                decision_meta["complexity"],
                decision_meta["question_type"],
            )
            return {"metadata": metadata, "pecar_output": None}

        self._emit_progress(state, "Running deep reasoning (PeCAR)...")
        budget = self._compute_pecar_budget(intent, decision_meta)
        decision_meta["budget"] = budget

        # Build PeCAR-compatible intent from Lumina's IntentAnalysis
        pecar_intent_data = {}
        if intent:
            pecar_intent_data = {
                "question_type": getattr(intent, "pecar_question_type", "conceptual"),
                "complexity": getattr(intent, "complexity_score", 0.5),
                "concepts": getattr(intent, "key_concepts", []),
                "difficulty": getattr(intent, "difficulty_level", {}).value
                    if hasattr(getattr(intent, "difficulty_level", None), "value")
                    else "intermediate",
                "requires_retrieval": True,
                "requires_visual": getattr(intent, "requires_visuals", False),
            }

        # Build retrieved context from extracted content (capped for latency)
        max_sources = max(1, int(budget["max_sources"]))
        retrieved_context = "\n\n".join(extracted_content[:max_sources])
        retrieved_context = retrieved_context[: int(budget["context_chars"])]

        # Build source URLs
        source_urls = [s.url for s in sources[:8]] if sources else []

        # Build PeCAR state dict
        pecar_state = {
            "query": original_question,
            "intent_analysis": pecar_intent_data,
            "mode": learning_mode,
            "learner_profile": learner_profile or {},
            "retrieved_context": retrieved_context,
            "sources": source_urls,
            "eval_scores": {},  # Will be populated on retry via QFPR
            "pecar_max_paths": int(budget["max_paths"]),
            "pecar_max_steps": int(budget["max_steps"]),
            "pecar_disable_retrieval": not settings.pecar_use_retrieval,
        }

        try:
            depth_cfg = DepthConfig(
                steps_low=(2, 3),
                steps_medium=(3, 5),
                steps_high=(4, 6),
            )
            pecar = PeCAR(call_llm_fn=self.teaching_agent._call_llm, depth_config=depth_cfg)
            pecar_timeout = int(budget["timeout_seconds"])
            result = await asyncio.wait_for(pecar.run(pecar_state), timeout=pecar_timeout)

            pecar_output = result.model_dump()
            metadata["pecar_output"] = pecar_output
            metadata["pecar_final_response"] = result.final_response

            logger.info(
                "PeCAR pipeline complete: mode=%s, depth=%.2f, steps=%d, paths=%d",
                result.mode.value,
                result.depth_score,
                result.num_reasoning_steps,
                len(result.paths_evaluated),
            )

            return {"metadata": metadata, "pecar_output": pecar_output}

        except asyncio.TimeoutError:
            logger.warning("PeCAR reasoning timed out; synthesis will continue without PeCAR")
            metadata["pecar_error"] = "PeCAR timeout"
            return {"metadata": metadata, "pecar_output": None}

        except Exception as e:
            logger.error(f"PeCAR reasoning failed: {e} — synthesis will proceed without PeCAR")
            metadata["pecar_error"] = str(e)
            return {"metadata": metadata, "pecar_output": None}

    async def synthesize_teaching_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Synthesize teaching content (uses PeCAR output when available)"""
        logger.info("NODE: Synthesizing teaching content...")
        self._emit_progress(state, "Synthesizing teaching response...")

        if isinstance(state, dict):
            original_question = state["original_question"]
            intent = state.get("intent")
            extracted_content = state.get("extracted_content", [])
            images = state.get("images", [])
            sources = state.get("sources", [])
            metadata = state.get("metadata", {})
            pecar_output = state.get("pecar_output")
        else:
            original_question = state.original_question
            intent = state.intent
            extracted_content = state.extracted_content
            images = state.images
            sources = state.sources
            metadata = state.metadata
            pecar_output = getattr(state, "pecar_output", None)

        # Also check metadata for pecar_output (populated by pecar_reasoning_node)
        if not pecar_output:
            pecar_output = metadata.get("pecar_output")

        teaching_response = await self.teaching_agent.synthesize(
            question=original_question,
            intent=intent,
            extracted_content=extracted_content,
            images=images,
            sources=sources,
            pecar_output=pecar_output,
        )

        metadata["teaching_response"] = teaching_response

        return {"metadata": metadata}
    
    async def assess_quality_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Assess quality of teaching response"""
        logger.info("NODE: Assessing quality...")
        self._emit_progress(state, "Assessing response quality...")
        
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
        
        # Retry only if the response is effectively broken.
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
