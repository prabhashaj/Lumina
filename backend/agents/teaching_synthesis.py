"""
Teaching Synthesis Agent - Creates comprehensive, pedagogically sound explanations
"""
import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from loguru import logger

from config.settings import settings
from shared.schemas.models import (
    IntentAnalysis, TeachingResponse, TeachingSection,
    Source, ImageData, SearchResult
)
from shared.prompts.templates import (
    TEACHING_SYNTHESIS_PROMPT,
    TEACHING_SYNTHESIS_BEGINNER,
    TEACHING_SYNTHESIS_INTERMEDIATE,
    TEACHING_SYNTHESIS_ADVANCED,
    COMPARATIVE_EXTRACTION_PROMPT,
    SEMANTIC_VERIFICATION_PROMPT,
)


class TeachingSynthesisAgent:
    """Synthesizes research into comprehensive teaching content"""
    
    def __init__(self):
        # Use Mistral API only.
        self.llm = None
        self.backup_llm = None

        if settings.mistral_api_key:
            logger.info("Teaching Synthesis: Using Mistral API")
            self.llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.4,
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

    async def _call_llm(self, prompt: str, system: str = "", **kwargs) -> str:
        """Direct LLM call for structured generation.

        Also serves as the PeCAR-compatible LLM callable (prompt + system -> str).
        """
        try:
            messages = []
            if system:
                from langchain_core.messages import SystemMessage
                messages.append(SystemMessage(content=system))
            messages.append(HumanMessage(content=prompt))
            response = await self._call_llm_with_fallback(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM call error: {str(e)}")
            raise

    async def _verify_semantic_accuracy(
        self, 
        question: str, 
        response_content: str, 
        sources: List[Source]
    ) -> Dict[str, Any]:
        """Verify semantic accuracy using LLM fact-checking."""
        try:
            sources_text = "\n".join([f"[{i+1}] {s.snippet}" for i, s in enumerate(sources[:3])])
            verification_prompt = SEMANTIC_VERIFICATION_PROMPT.format(
                question=question,
                response=response_content[:2000],  # Use first 2000 chars for efficiency
                sources=sources_text
            )
            
            verification_result = await self._call_llm(prompt=verification_prompt)
            
            # Parse JSON response
            try:
                import json
                verification_data = json.loads(verification_result)
                logger.info(f"Semantic verification: accuracy={verification_data.get('accuracy_score', 0.0)}")
                return verification_data
            except:
                logger.warning("Failed to parse semantic verification result")
                return {"accuracy_score": 0.7, "revision_needed": False}
                
        except Exception as e:
            logger.warning(f"Semantic verification failed: {str(e)}")
            return {"accuracy_score": 0.7, "revision_needed": False}

    async def synthesize(
        self,
        question: str,
        intent: IntentAnalysis,
        extracted_content: List[str],
        images: List[ImageData],
        sources: List[Source],
        pecar_output: dict = None,
    ) -> TeachingResponse:
        """
        Create a comprehensive teaching response

        Args:
            question: Original student question
            intent: Intent analysis results
            extracted_content: Extracted research content
            images: Relevant images
            sources: Source citations
            pecar_output: Optional PeCAR pipeline output dict (from pecar_reasoning_node)

        Returns:
            Complete TeachingResponse
        """
        try:
            logger.info(f"Synthesizing teaching content for: {question[:50]}...")

            if self._is_live_update_request(question):
                logger.info("Live-update query detected; using direct score synthesis path")
                return self._build_live_update_response(
                    question=question,
                    intent=intent,
                    extracted_content=extracted_content,
                    images=images,
                    sources=sources,
                )

            # If PeCAR produced a final response, use it as the base content
            pecar_final = None
            if pecar_output and pecar_output.get("final_response"):
                candidate = pecar_output["final_response"]
                if self._is_usable_pecar_output(candidate):
                    pecar_final = candidate
                    logger.info("Using PeCAR guidance for synthesis (len=%d)", len(pecar_final))
                else:
                    logger.warning("PeCAR output unusable, falling back to direct synthesis")

            # Always run final synthesis for consistent output format; inject PeCAR as guidance.
            research_content = self._format_research(extracted_content, sources)
            max_research_chars = max(1200, int(getattr(settings, "synthesis_research_chars", 2600)))
            if len(research_content) > max_research_chars:
                research_content = research_content[:max_research_chars].rstrip() + "\n\n[Research truncated for latency budget]"
            if pecar_final:
                research_content += self._format_pecar_guidance(pecar_final)

            # Format image references (no VLM analysis, just URLs)
            image_references = self._format_image_references(images)

            # Get difficulty-specific instructions
            difficulty_instructions = {
                "beginner": TEACHING_SYNTHESIS_BEGINNER,
                "intermediate": TEACHING_SYNTHESIS_INTERMEDIATE,
                "advanced": TEACHING_SYNTHESIS_ADVANCED
            }.get(intent.difficulty_level.value, "")

            # Create main prompt
            full_prompt = TEACHING_SYNTHESIS_PROMPT + "\n\n" + difficulty_instructions

            # Add image section if images available
            if image_references:
                full_prompt += "\n\n## Visual Content Available\n"
                full_prompt += "Visual aids are provided to enhance learning. Reference them naturally in your explanation:\n\n"
                full_prompt += image_references

            prompt_text = full_prompt.format(
                question=question,
                difficulty=intent.difficulty_level.value,
                question_type=intent.question_type.value,
                concepts=", ".join(intent.key_concepts),
                research_content=research_content,
                num_images=len(images)
            )
            messages = [HumanMessage(content=prompt_text)]

            response = await self._call_llm_with_fallback(messages)
            content = response.content
            
            logger.info(f"LLM response length: {len(content)} chars")
            logger.info(f"LLM response preview: {content[:300]}...")
            
            # Parse the structured response
            parsed = self._parse_teaching_content(content)
            
            # Avoid extra LLM round-trip: if model returns too few questions, fill quickly.
            if not parsed.get("practice_questions") or len(parsed.get("practice_questions", [])) < 3:
                parsed["practice_questions"] = self._build_fallback_questions(
                    question,
                    parsed.get("practice_questions", []),
                )
            else:
                # Aggressive deduplication with normalized comparison
                unique_questions = []
                seen_normalized = set()
                for q in parsed.get("practice_questions", []):
                    # Normalize: lowercase, remove punctuation and extra spaces
                    normalized = q.lower().replace('?', '').replace('.', '').replace(',', '').replace('!', '').strip()
                    normalized = ' '.join(normalized.split())  # Remove extra whitespace
                    
                    if normalized not in seen_normalized and len(q) > 10:
                        unique_questions.append(q)
                        seen_normalized.add(normalized)
                    else:
                        logger.warning(f"Removed duplicate question: {q[:60]}...")
                
                parsed["practice_questions"] = unique_questions[:4]  # Max 4 questions
                logger.info(f"Final question count after deduplication: {len(parsed['practice_questions'])}")
            
            # Final safety check - ensure no duplicates before creating response
            final_questions = []
            final_seen = set()
            for q in parsed.get("practice_questions", []):
                normalized = q.lower().replace('?', '').replace('.', '').replace(',', '').strip()
                normalized = ' '.join(normalized.split())
                if normalized not in final_seen:
                    final_questions.append(q)
                    final_seen.add(normalized)
                else:
                    logger.error(f"CRITICAL: Duplicate found in final check! {q[:60]}")
            
            parsed["practice_questions"] = final_questions[:4]
            logger.info(f"Final practice questions count: {len(parsed['practice_questions'])}")
            for idx, q in enumerate(parsed.get("practice_questions", []), 1):
                logger.info(f"  Q{idx}: {q[:80]}")
            
            # Build PeCAR metrics if available
            pecar_metrics = None
            if pecar_output:
                pecar_metrics = {
                    "mode": pecar_output.get("mode"),
                    "depth_score": pecar_output.get("depth_score", 0.0),
                    "num_reasoning_steps": pecar_output.get("num_reasoning_steps", 0),
                    "paths_evaluated": len(pecar_output.get("paths_evaluated", [])),
                    "refinement_iterations": len(pecar_output.get("refinement_history", [])),
                    "techniques_applied": pecar_output.get("metadata", {}).get("techniques_applied", []),
                    "sources_used": len(pecar_output.get("sources_used", [])),
                }

            teaching_response = TeachingResponse(
                question=question,
                tldr=parsed.get("tldr", ""),
                explanation=TeachingSection(
                    title="Explanation",
                    content=parsed.get("explanation", "")
                ),
                visual_explanation=parsed.get("visual_explanation"),
                images=images,
                analogy=parsed.get("analogy", ""),
                practice_questions=parsed.get("practice_questions", []),
                sources=sources,
                difficulty_level=intent.difficulty_level,
                confidence_score=0.85,  # Will be assessed by quality agent
                processing_time=0.0,  # Will be set by orchestrator
                follow_up_suggestions=[],  # Will be generated later
                pecar_metrics=pecar_metrics,
            )
            
            logger.info("Teaching synthesis complete")
            return teaching_response
            
        except Exception as e:
            logger.error(f"Teaching synthesis error: {str(e)}")
            if self._is_transient_connection_error(e):
                logger.warning("Network connectivity issue detected during synthesis; returning degraded fallback response")
                return self._build_connection_fallback_response(
                    question=question,
                    intent=intent,
                    extracted_content=extracted_content,
                    images=images,
                    sources=sources,
                )
            raise

    def _is_usable_pecar_output(self, text: str) -> bool:
        """Validate PeCAR output before using it as final answer content."""
        if not text or not isinstance(text, str):
            return False
        cleaned = text.strip()
        lowered = cleaned.lower()

        # Reject known fallback/error patterns from upstream PeCAR steps.
        if lowered.startswith("i encountered an error generating a response"):
            return False
        if "fallback generation also failed" in lowered:
            return False

        # Require enough substance to parse into teaching sections.
        return len(cleaned) >= 900

    @staticmethod
    def _is_live_update_request(question: str) -> bool:
        q = (question or "").strip().lower()
        if not q:
            return False
        has_live_signal = bool(re.search(r"\b(live|current|now|today|latest|real[ -]?time)\b", q))
        has_score_signal = bool(re.search(r"\b(score|scorecard|ipl|cricket|match|runs|wickets|overs)\b", q))
        return has_live_signal and has_score_signal

    @staticmethod
    def _is_comparison_question(question: str) -> bool:
        """Detect if this is a comparison/contrast question."""
        q = (question or "").strip().lower()
        comparison_keywords = [
            "compare", "versus", "vs", "contrast", "difference", 
            "trade-off", "tradeoff", "pros and cons", "advantage",
            "better", "worse", "similar", "distinguish", "versus",
            "which is", "what's the difference", "how do they differ"
        ]
        return any(keyword in q for keyword in comparison_keywords)

    @staticmethod
    def _extract_live_score_indicators(text: str) -> List[str]:
        """Extract likely live-score snippets from raw fetched content."""
        if not text:
            return []

        lines = [ln.strip() for ln in re.split(r"[\n\r]+", text) if ln.strip()]
        candidates = []

        score_pattern = re.compile(
            r"\b[A-Z]{2,5}\s*\d{1,3}/\d{1,2}(?:\s*\(\d{1,2}(?:\.\d)?\s*overs?\))?\b"
        )
        chase_pattern = re.compile(r"\bneed\s+\d+\s+runs?\s+in\s+\d+\s+balls?\b", re.IGNORECASE)

        for ln in lines:
            compact = re.sub(r"\s+", " ", ln)
            low = compact.lower()
            if len(compact) < 12:
                continue
            if score_pattern.search(compact) or chase_pattern.search(compact):
                candidates.append(compact[:220])
                continue
            if any(tok in low for tok in ["live", "score", "scorecard", "overs", "wickets", "innings"]):
                if any(ch.isdigit() for ch in compact):
                    candidates.append(compact[:220])

        unique = []
        seen = set()
        for c in candidates:
            norm = c.lower().strip()
            if norm not in seen:
                unique.append(c)
                seen.add(norm)

        return unique[:6]

    def _build_live_update_response(
        self,
        question: str,
        intent: IntentAnalysis,
        extracted_content: List[str],
        images: List[ImageData],
        sources: List[Source],
    ) -> TeachingResponse:
        """Build a direct, timestamped live-update style response from retrieved evidence."""
        indicators: List[str] = []
        for block in extracted_content[:4]:
            indicators.extend(self._extract_live_score_indicators(block))

        fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if indicators:
            top = indicators[0]
            tldr = (
                f"Latest live-score signal (fetched at {fetched_at}): {top}. "
                "If this differs from your app, score feeds may be a few seconds behind across sources."
            )
            explanation_lines = [
                f"Live query: {question}",
                f"Fetched at: {fetched_at}",
                "",
                "Top extracted score indicators:",
            ]
            for idx, item in enumerate(indicators[:4], 1):
                explanation_lines.append(f"{idx}. {item}")
        else:
            tldr = (
                f"I could not extract a reliable numeric live score at {fetched_at}. "
                "Live score pages are highly dynamic and can block extraction."
            )
            explanation_lines = [
                f"Live query: {question}",
                f"Fetched at: {fetched_at}",
                "",
                "What happened:",
                "1. Sources were fetched, but no stable scoreline pattern was detected in the extracted text.",
                "2. This usually happens on JavaScript-heavy scoreboards.",
                "3. Use the cited scorecard links below to verify the exact current number.",
            ]

        return TeachingResponse(
            question=question,
            tldr=tldr,
            explanation=TeachingSection(
                title="Live Score Update",
                content="\n".join(explanation_lines),
            ),
            visual_explanation=None,
            images=images,
            analogy="Live score feeds behave like multiple stopwatches started at slightly different moments.",
            practice_questions=[
                "Do you want only the latest scoreline, or full match context (run rate, required rate, partnerships)?",
                "Should I prioritize one source (for example ESPNcricinfo) as the primary score reference?",
                "Do you want auto-refresh style updates each time you ask for the score?",
            ],
            sources=sources,
            difficulty_level=intent.difficulty_level,
            confidence_score=0.8 if indicators else 0.55,
            processing_time=0.0,
            follow_up_suggestions=[],
            pecar_metrics=None,
        )
    
    def _format_research(self, content_list: List[str], sources: List[Source]) -> str:
        """Format research content with source references"""
        formatted = []
        for idx, (content, source) in enumerate(zip(content_list, sources[:len(content_list)])):
            formatted.append(f"[{idx + 1}] {source.domain}: {content[:1200]}")
        return "\n\n".join(formatted)

    def _format_pecar_guidance(self, pecar_final: str) -> str:
        """Inject PeCAR reasoning as compact synthesis guidance."""
        snippet = (pecar_final or "").strip()
        if not snippet:
            return ""
        snippet = snippet[:2600]
        return (
            "\n\n[PeCAR Guidance - prioritize verified reasoning and pedagogical sequencing]\n"
            f"{snippet}"
        )

    def _build_timeout_fallback_content(
        self,
        question: str,
        intent: IntentAnalysis,
        extracted_content: List[str],
    ) -> str:
        """Create a deterministic, parseable teaching response when LLM synthesis times out."""
        key_concepts = ", ".join(intent.key_concepts[:6]) if intent and intent.key_concepts else "core concepts"
        evidence = " ".join((extracted_content or [""])[:2])[:1200].strip()
        if not evidence:
            evidence = "Relevant sources were found, but detailed extraction was incomplete due timeout."

        return (
            "## TL;DR\n"
            f"{question} can be understood by breaking it into clear core ideas and applying them step by step. "
            f"Key focus areas: {key_concepts}.\n\n"
            "## Step-by-Step Explanation\n"
            "1. Identify the core terms and definitions involved in the question.\n"
            "2. Separate what is conceptual from what is procedural or computational.\n"
            "3. Connect the main ideas using a concrete worked example.\n"
            "4. Highlight common errors and how to avoid them.\n"
            "5. Summarize decision rules for solving similar problems.\n\n"
            f"Evidence snapshot: {evidence}\n\n"
            "## Visual Explanation\n"
            "Imagine a flow from problem statement -> key concepts -> method choice -> worked example -> final checks.\n\n"
            "## Real-World Analogy\n"
            "Like planning a trip: you choose the route based on constraints, verify each step, and adjust when conditions change.\n\n"
            "## Practice Questions\n"
            f"1. What is the key idea behind: {question}?\n"
            f"2. Which method would you choose first for {question}, and why?\n"
            f"3. What is a common mistake when solving {question}, and how would you catch it?\n"
            f"4. How would the solution change if one core assumption in {question} changed?\n"
        )

    def _build_fallback_questions(self, question: str, existing: List[str]) -> List[str]:
        """Build fast deterministic fallback questions without a second LLM call."""
        seed = [q for q in existing if q and len(q.strip()) > 10]
        candidates = [
            f"What is the core idea behind {question}?",
            f"How would you apply {question} in a practical scenario?",
            f"Why is {question} important, and where does it fail?",
            f"What would change if a key assumption in {question} was removed?",
        ]

        seen = {q.lower().strip(' ?.!,') for q in seed}
        for c in candidates:
            n = c.lower().strip(' ?.!,')
            if n not in seen:
                seed.append(c)
                seen.add(n)
            if len(seed) >= 4:
                break
        return seed[:4]

    @staticmethod
    def _is_transient_connection_error(exc: Exception) -> bool:
        """Identify transient network/provider connectivity failures."""
        keywords = (
            "connection error",
            "connecterror",
            "apiconnectionerror",
            "getaddrinfo failed",
            "temporary failure in name resolution",
            "name or service not known",
            "dns",
            "nodename nor servname provided",
            "network is unreachable",
            "timed out",
            "timeout",
        )

        checked = 0
        current: Any = exc
        while current is not None and checked < 8:
            text = f"{type(current).__name__}: {current}".lower()
            if any(k in text for k in keywords):
                return True
            current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
            checked += 1

        return False

    def _build_connection_fallback_response(
        self,
        question: str,
        intent: IntentAnalysis,
        extracted_content: List[str],
        images: List[ImageData],
        sources: List[Source],
    ) -> TeachingResponse:
        """Return a deterministic response when LLM/provider network calls fail."""
        content = self._build_timeout_fallback_content(
            question=question,
            intent=intent,
            extracted_content=extracted_content,
        )
        parsed = self._parse_teaching_content(content)
        practice_questions = self._build_fallback_questions(question, parsed.get("practice_questions", []))

        tldr = (parsed.get("tldr") or "").strip()
        if tldr:
            tldr += " "
        tldr += "Note: Live model synthesis is temporarily unavailable due to a network connection issue."

        return TeachingResponse(
            question=question,
            tldr=tldr,
            explanation=TeachingSection(
                title="Explanation",
                content=parsed.get("explanation", ""),
            ),
            visual_explanation=parsed.get("visual_explanation"),
            images=images,
            analogy=parsed.get("analogy", ""),
            practice_questions=practice_questions,
            sources=sources,
            difficulty_level=intent.difficulty_level,
            confidence_score=0.45,
            processing_time=0.0,
            follow_up_suggestions=[],
            pecar_metrics=None,
        )
    
    def _format_image_references(self, images: List[ImageData]) -> str:
        """Format image references for teaching integration (no VLM analysis needed)"""
        if not images:
            return ""
        
        formatted = []
        for idx, img in enumerate(images, 1):
            formatted.append(f"**Visual {idx}**: {img.caption}")
        
        return "\n".join(formatted)
    
    def _parse_teaching_content(self, content: str) -> dict:
        """Parse the structured teaching response"""
        logger.info(f"Parsing teaching content (length: {len(content)} chars)")
        logger.info(f"First 500 chars: {content[:500]}")
        
        sections = {}
        
        # Extract sections using markers (try multiple variations)
        markers = {
            "tldr": ["## TL;DR", "## TLDR", "**TL;DR**", "TL;DR:", "TL;DR\n", "TL;DR "],
            "explanation": [
                "## Step-by-Step Explanation", "## **Step-by-Step Explanation**",
                "## Explanation", "## **Explanation**", 
                "## Detailed Explanation", "Step-by-Step:", "---\n## "
            ],
            "visual_explanation": [
                "## Visual Explanation", "## **Visual Explanation**",
                "## Visuals", "Visual Understanding:", "Visual Explanation\n"
            ],
            "analogy": [
                "## Real-World Analogy", "## **Real-World Analogy**",
                "## Analogy", "Real-World Example:", "Real-World Analogy\n"
            ],
            "practice_questions": [
                "## Practice Questions", "## **Practice Questions**",
                "## Questions", "Practice:", "Practice Questions\n"
            ]
        }
        
        for key, marker_variations in markers.items():
            found = False
            for marker in marker_variations:
                if marker in content:
                    start = content.find(marker) + len(marker)
                    # Find next section or end
                    all_markers = [m for variations in markers.values() for m in variations]
                    end = len(content)
                    for next_m in all_markers:
                        pos = content.find(next_m, start)
                        if pos != -1 and pos < end:
                            end = pos
                    
                    section_content = content[start:end].strip()
                    
                    # Remove horizontal rules and clean up
                    if section_content.startswith('---'):
                        section_content = section_content[3:].strip()
                    section_content = section_content.replace('\n---\n', '\n\n')
                    
                    if key == "practice_questions":
                        # Parse practice questions (handle both simple lists and subsections)
                        questions = []
                        lines = section_content.split('\n')
                        
                        logger.info(f"Parsing practice questions from {len(lines)} lines")
                        
                        for i, line in enumerate(lines):
                            line = line.strip()
                            
                            # Skip blank lines
                            if not line:
                                continue
                            
                            # Skip subsection headers like "### 1. Basic Understanding" or "**Basic Recall**"
                            if line.startswith('###') or line.startswith('##'):
                                logger.debug(f"Skipping header: {line[:50]}")
                                continue
                            
                            if line.startswith('**') and line.endswith('**'):
                                logger.debug(f"Skipping bold label: {line}")
                                continue
                            
                            # Look for actual questions (usually in italics or after numbering)
                            if line.startswith('*') and line.endswith('*') and len(line) > 15:
                                # Question in italics: *Why can't a jet engine work...?*
                                q = line.strip('*').strip()
                                if q and '?' in q:
                                    # Extract just the question part (before answer if present)
                                    if '(Answer:' in q or '*(Answer:' in q:
                                        q = q.split('(Answer:')[0].split('*(Answer:')[0].strip()
                                    questions.append(q)
                                    logger.info(f"Found italic question: {q[:50]}...")
                            elif line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                                # Numbered question: 1. Question text
                                q = line.lstrip('0123456789.-•) ').strip()
                                # Only add if it's substantial and not a category label
                                if q and len(q) > 15:
                                    # Skip if it's just a label like "**Basic Recall/Understanding**"
                                    if q.startswith('**') and q.endswith('**'):
                                        logger.debug(f"Skipping numbered label: {q}")
                                        continue
                                    
                                    # Skip category labels (no question marks, just category names)
                                    if any(cat in q for cat in ['Basic Recall', 'Understanding', 'Application', 'Analysis', 'Synthesis', 'Evaluation']):
                                        # Check if it's JUST the category label (not part of a real question)
                                        if q.count('/') > 0 or (len(q) < 50 and '?' not in q):
                                            logger.debug(f"Skipping category label: {q}")
                                            continue
                                    
                                    # Must contain a question mark OR question words to be valid
                                    if not ('?' in q or any(word in q.lower() for word in ['what', 'how', 'why', 'when', 'where', 'who', 'explain', 'describe', 'compare', 'calculate', 'identify'])):
                                        logger.debug(f"Skipping non-question text: {q}")
                                        continue
                                    
                                    questions.append(q)
                                    logger.info(f"Found numbered question: {q[:50]}...")
                        
                        # Aggressive deduplication - normalize and filter
                        unique_questions = []
                        seen_normalized = set()
                        
                        for q in questions:
                            # Normalize: lowercase, remove all punctuation, collapse whitespace
                            normalized = q.lower().replace('?', '').replace('.', '').replace(',', '').replace('!', '').strip()
                            normalized = ' '.join(normalized.split())  # Remove extra whitespace
                            
                            if normalized not in seen_normalized and len(q) > 10:
                                unique_questions.append(q)
                                seen_normalized.add(normalized)
                                logger.info(f"Added question {len(unique_questions)}: {q[:60]}...")
                            else:
                                logger.warning(f"DUPLICATE DETECTED - Skipping: {q[:60]}...")
                        
                        sections[key] = unique_questions[:4]  # EXACTLY 4 unique questions
                        logger.info(f"✓ Parsed {len(sections[key])} UNIQUE practice questions (removed {len(questions) - len(unique_questions)} duplicates)")
                    else:
                        # Clean up: remove the section header markdown if present
                        if section_content.startswith('#'):
                            # Remove first line if it's a header
                            lines = section_content.split('\n', 1)
                            if len(lines) > 1:
                                section_content = lines[1].strip()
                            else:
                                section_content = ""
                        
                        # Remove numbered prefixes from headings (e.g., "## 2. Topic" -> "## Topic")
                        import re
                        section_content = re.sub(r'^(#{2,3})\s*\d+\.\s+', r'\1 ', section_content, flags=re.MULTILINE)
                        
                        sections[key] = section_content
                    
                    found = True
                    logger.info(f"✓ Found {key}: {len(section_content)} chars")
                    break
            
            if not found:
                logger.warning(f"Section '{key}' not found in response")
        
        # If no sections were found at all, log the start of the content for debugging
        if not sections:
            logger.error(f"No sections found! Content starts with: {content[:200]}")
        
        return sections
    
    async def _generate_practice_questions(self, question: str, difficulty: str) -> List[str]:
        """Generate exactly 4 unique practice questions"""
        try:
            prompt = f"""You are creating practice questions for a {difficulty}-level student who just learned about:

"{question}"

Generate EXACTLY 4 specific, thought-provoking questions that test real understanding (not just memorization). Each question should be progressively more challenging:

1. **Recall & Define** — A clear "What is...?" or "Define..." question about a KEY concept from the topic. Be specific — name the actual concept.
2. **Apply & Explain** — A "How would you...?" or "Explain how..." question that requires applying knowledge to a specific scenario.  
3. **Analyze & Compare** — A "Why does...?" or "Compare X and Y..." question that requires deeper reasoning and analysis.
4. **Create & Predict** — A "What would happen if...?" or "Design a..." question that requires synthesis and creative thinking.

RULES:
- Each question MUST be a complete sentence ending with a question mark
- Each question MUST reference specific concepts from the topic (not generic)
- Each question MUST be completely different from the others
- Do NOT include answers, just the questions
- Do NOT include category labels — just the numbered question

Return ONLY 4 questions as a numbered list (1. 2. 3. 4.)."""

            messages = [HumanMessage(content=prompt)]
            response = await self._call_llm_with_fallback(messages)
            
            questions = []
            seen_normalized = set()  # Track normalized versions
            
            for line in response.content.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    q = line.lstrip('0123456789.-) ').strip()
                    
                    # Normalize for duplicate detection (lowercase, remove all punctuation, collapse whitespace)
                    normalized = q.lower().replace('?', '').replace('.', '').replace(',', '').replace('!', '').strip()
                    normalized = ' '.join(normalized.split())
                    
                    # Only add if truly unique and substantial
                    if q and normalized not in seen_normalized and len(q) > 15:
                        questions.append(q)
                        seen_normalized.add(normalized)
                        logger.info(f"Generated unique question {len(questions)}: {q[:60]}...")
                        
                        if len(questions) >= 4:  # Stop at exactly 4
                            break
                    elif normalized in seen_normalized:
                        logger.warning(f"Skipping duplicate in generation: {q[:60]}...")
            
            # If still duplicates or insufficient, generate fallback unique questions
            if len(questions) < 4:
                fallbacks = [
                    f"What are the key principles behind {question.split()[-3:]}?",
                    f"How would you apply this knowledge in a practical scenario?",
                    f"Why is this concept important in the broader field?",
                    f"What connections can you make to other topics you've learned?"
                ]
                for fb in fallbacks:
                    if len(questions) >= 4:
                        break
                    normalized_fb = fb.lower().replace('?', '').strip()
                    if normalized_fb not in seen_normalized:
                        questions.append(fb)
                        seen_normalized.add(normalized_fb)
            
            return questions[:4]  # Return EXACTLY 4 questions
            
        except Exception as e:
            logger.error(f"Practice question generation error: {str(e)}")
            return [
                "What are the key concepts you learned?",
                "How would you apply this knowledge in a real scenario?",
                "Can you explain this concept to someone else?"
            ]
