"""
Teaching Synthesis Agent - Creates comprehensive, pedagogically sound explanations
"""
from typing import List
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
    TEACHING_SYNTHESIS_ADVANCED
)


class TeachingSynthesisAgent:
    """Synthesizes research into comprehensive teaching content"""
    
    def __init__(self):
        # Use OpenRouter Mistral Small (primary), then Mistral API Medium (backup)
        self.llm = None
        self.backup_llm = None
        
        if settings.openrouter_api_key:
            logger.info("Teaching Synthesis: Using Mistral Small via OpenRouter")
            self.llm = ChatOpenAI(
                model=settings.openrouter_model,
                temperature=0.7,
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                max_tokens=8000  # Large context for comprehensive teaching content
            )
            # Set backup to Mistral API if available
            if settings.mistral_api_key:
                self.backup_llm = ChatOpenAI(
                    model=settings.mistral_model,
                    temperature=0.7,
                    api_key=settings.mistral_api_key,
                    base_url="https://api.mistral.ai/v1",
                    max_tokens=8000
                )
        elif settings.mistral_api_key:
            logger.info("Teaching Synthesis: Using Mistral Medium via Mistral API")
            self.llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.7,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
                max_tokens=8000
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
                logger.warning(f"Primary LLM failed, using backup Mistral API")
                return await self.backup_llm.ainvoke(messages)
            raise

    async def _call_llm(self, prompt: str) -> str:
        """Direct LLM call for structured generation (roadmaps, quizzes, etc.)"""
        try:
            response = await self._call_llm_with_fallback([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"LLM call error: {str(e)}")
            raise

    async def synthesize(
        self,
        question: str,
        intent: IntentAnalysis,
        extracted_content: List[str],
        images: List[ImageData],
        sources: List[Source]
    ) -> TeachingResponse:
        """
        Create a comprehensive teaching response
        
        Args:
            question: Original student question
            intent: Intent analysis results
            extracted_content: Extracted research content
            images: Relevant images
            sources: Source citations
            
        Returns:
            Complete TeachingResponse
        """
        try:
            logger.info(f"Synthesizing teaching content for: {question[:50]}...")
            
            # Build research summary
            research_content = self._format_research(extracted_content, sources)
            
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
            
            # Generate practice questions if not present or ensure 3-5 unique questions
            if not parsed.get("practice_questions") or len(parsed.get("practice_questions", [])) < 3:
                parsed["practice_questions"] = await self._generate_practice_questions(
                    question, intent.difficulty_level.value
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
                follow_up_suggestions=[]  # Will be generated later
            )
            
            logger.info("Teaching synthesis complete")
            return teaching_response
            
        except Exception as e:
            logger.error(f"Teaching synthesis error: {str(e)}")
            raise
    
    def _format_research(self, content_list: List[str], sources: List[Source]) -> str:
        """Format research content with source references"""
        formatted = []
        for idx, (content, source) in enumerate(zip(content_list, sources[:len(content_list)])):
            formatted.append(f"[{idx + 1}] {source.domain}: {content[:2000]}")
        return "\n\n".join(formatted)
    
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
