"""
Slide Generator Agent - Creates comprehensive presentation slides with speaker notes
for video lecture-style content delivery.
"""
import json
import re
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from loguru import logger

from config.settings import settings


# ── Slide content templates for fallback generation ──
_SLIDE_TEMPLATES = {
    "introduction": {
        "title_template": "What is {topic}?",
        "bullets_template": [
            "Definition and overview of {topic}",
            "Why {topic} matters in today's world",
            "Historical background and evolution",
            "Key areas we will cover",
        ],
        "notes_template": (
            "Let's begin by understanding what {topic} actually is. "
            "At its core, {topic} is a fascinating subject that has shaped many aspects "
            "of our world. Understanding the basics will help us appreciate the more "
            "advanced concepts we'll explore later in this presentation."
        ),
        "layout": "default",
        "image_suffix": "introduction overview",
    },
    "fundamentals": {
        "title_template": "Core Fundamentals of {topic}",
        "bullets_template": [
            "Fundamental principles and building blocks",
            "Key terminology you need to know",
            "The underlying mechanisms at work",
            "How these fundamentals connect together",
        ],
        "notes_template": (
            "Now let's dive into the core fundamentals. Think of these as the building "
            "blocks — without understanding these basics, the more advanced concepts "
            "won't make much sense. I like to use an analogy here: just like learning "
            "an alphabet before writing essays, mastering these fundamentals is essential."
        ),
        "layout": "default",
        "image_suffix": "fundamentals diagram",
    },
    "how_it_works": {
        "title_template": "How {topic} Works",
        "bullets_template": [
            "Step-by-step process explained",
            "Key components and their roles",
            "The flow from input to output",
            "Critical interactions between elements",
        ],
        "notes_template": (
            "So how does {topic} actually work? Let me walk you through the process "
            "step by step. Each component plays a specific role, and understanding these "
            "roles helps us see the bigger picture. Imagine it as a well-orchestrated "
            "system where every part contributes to the final result."
        ),
        "layout": "default",
        "image_suffix": "process diagram",
    },
    "key_concepts": {
        "title_template": "Key Concepts in {topic}",
        "bullets_template": [
            "Essential theories and frameworks",
            "Important models and approaches",
            "Relationships between concepts",
            "Common misconceptions clarified",
        ],
        "notes_template": (
            "These key concepts form the intellectual backbone of {topic}. "
            "Many students find it helpful to create mental models linking these ideas "
            "together. Don't worry if some seem abstract at first — we'll ground them "
            "with concrete examples shortly."
        ),
        "layout": "default",
        "image_suffix": "concepts mind map",
    },
    "examples": {
        "title_template": "Real-World Examples",
        "bullets_template": [
            "Practical example: everyday applications",
            "Case study: industry implementation",
            "How experts apply these concepts",
            "Lessons learned from real scenarios",
        ],
        "notes_template": (
            "Let's bring {topic} to life with real-world examples. Theory is important, "
            "but seeing how it applies in practice makes everything click. These examples "
            "come from various fields and show just how versatile and impactful {topic} "
            "can be when applied correctly."
        ),
        "layout": "image-focus",
        "image_suffix": "real world example",
    },
    "advantages": {
        "title_template": "Benefits & Advantages",
        "bullets_template": [
            "Key benefits of understanding {topic}",
            "Competitive advantages it provides",
            "Long-term impact and value creation",
            "How it improves existing systems",
        ],
        "notes_template": (
            "Understanding {topic} unlocks several significant advantages. Whether "
            "you're a student, professional, or enthusiast, these benefits translate "
            "directly into real value. Let me highlight the most impactful ones that "
            "you'll encounter in your journey."
        ),
        "layout": "default",
        "image_suffix": "benefits advantages",
    },
    "challenges": {
        "title_template": "Challenges & Considerations",
        "bullets_template": [
            "Common challenges and obstacles",
            "Potential pitfalls to avoid",
            "Strategies to overcome difficulties",
            "Important trade-offs to consider",
        ],
        "notes_template": (
            "No topic is without its challenges, and {topic} is no exception. "
            "Being aware of these challenges upfront helps you prepare and navigate "
            "them successfully. Think of these not as roadblocks but as opportunities "
            "to deepen your understanding."
        ),
        "layout": "comparison",
        "image_suffix": "challenges solutions",
    },
    "applications": {
        "title_template": "Applications of {topic}",
        "bullets_template": [
            "Applications in science and technology",
            "Industrial and commercial use cases",
            "Educational and research applications",
            "Emerging and future applications",
        ],
        "notes_template": (
            "The applications of {topic} span across multiple domains and industries. "
            "From cutting-edge research to everyday tools, the impact is far-reaching. "
            "Let's explore some of the most exciting and practical ways {topic} is "
            "being used right now."
        ),
        "layout": "default",
        "image_suffix": "applications technology",
    },
    "deep_dive": {
        "title_template": "Deep Dive: Advanced Aspects",
        "bullets_template": [
            "Advanced techniques and methodologies",
            "Expert-level insights and patterns",
            "Cutting-edge research frontiers",
            "Complex interactions and nuances",
        ],
        "notes_template": (
            "For those ready to go deeper, let's explore some advanced aspects of "
            "{topic}. These concepts build on everything we've covered so far and "
            "represent the frontier of current understanding. Don't worry if these "
            "take a bit more time to digest — that's perfectly normal."
        ),
        "layout": "default",
        "image_suffix": "advanced concepts",
    },
    "comparison": {
        "title_template": "Comparing Approaches",
        "bullets_template": [
            "Different schools of thought",
            "Traditional vs modern approaches",
            "Strengths and weaknesses of each",
            "When to use which approach",
        ],
        "notes_template": (
            "An important skill is knowing the different approaches and when to use "
            "each one. Let's compare the major methods side by side. Understanding "
            "these trade-offs will help you make better decisions when working with "
            "{topic} in practice."
        ),
        "layout": "comparison",
        "image_suffix": "comparison chart",
    },
    "future": {
        "title_template": "Future of {topic}",
        "bullets_template": [
            "Emerging trends and directions",
            "Predicted developments and innovations",
            "How the field is evolving",
            "Skills needed for the future",
        ],
        "notes_template": (
            "Where is {topic} heading? The future is exciting, with new developments "
            "emerging rapidly. Understanding these trends helps you stay ahead and "
            "prepares you for what's coming next. Let me share some of the most "
            "promising directions researchers and practitioners are exploring."
        ),
        "layout": "default",
        "image_suffix": "future trends innovation",
    },
    "best_practices": {
        "title_template": "Best Practices & Tips",
        "bullets_template": [
            "Industry-proven best practices",
            "Tips from experienced practitioners",
            "Common mistakes to avoid",
            "Quick-win strategies for success",
        ],
        "notes_template": (
            "Before we wrap up, let me share some battle-tested best practices. "
            "These tips come from years of experience and can save you significant "
            "time and effort. Think of these as your personal cheat sheet for "
            "mastering {topic}."
        ),
        "layout": "default",
        "image_suffix": "best practices tips",
    },
}

# Order in which templates are used for fallback slides
_TEMPLATE_ORDER = [
    "introduction", "fundamentals", "how_it_works", "key_concepts",
    "examples", "advantages", "challenges", "applications",
    "deep_dive", "comparison", "future", "best_practices",
]


class SlideContent:
    """Represents a single slide"""
    def __init__(self, slide_number: int, title: str, bullet_points: List[str],
                 speaker_notes: str, image_query: str, layout: str = "default",
                 background_style: str = "gradient"):
        self.slide_number = slide_number
        self.title = title
        self.bullet_points = bullet_points
        self.speaker_notes = speaker_notes
        self.image_query = image_query
        self.layout = layout  # "title", "default", "image-focus", "comparison", "summary"
        self.background_style = background_style

    def to_dict(self):
        return {
            "slide_number": self.slide_number,
            "title": self.title,
            "bullet_points": self.bullet_points,
            "speaker_notes": self.speaker_notes,
            "image_query": self.image_query,
            "layout": self.layout,
            "background_style": self.background_style,
        }


class SlideGeneratorAgent:
    """Generates structured presentation slides with narration scripts"""

    def __init__(self):
        # Use OpenRouter Mistral Small (primary), then Mistral API Medium (backup)
        self.llm = None
        self.backup_llm = None
        
        if settings.openrouter_api_key:
            logger.info("Slide Generator: Using Mistral Small via OpenRouter")
            self.llm = ChatOpenAI(
                model=settings.openrouter_model,
                temperature=0.7,
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                max_tokens=6000  # Slides with narration
            )
            # Set backup to Mistral API if available
            if settings.mistral_api_key:
                self.backup_llm = ChatOpenAI(
                    model=settings.mistral_model,
                    temperature=0.7,
                    api_key=settings.mistral_api_key,
                    base_url="https://api.mistral.ai/v1",
                    max_tokens=6000
                )
        elif settings.mistral_api_key:
            logger.info("Slide Generator: Using Mistral Medium via Mistral API")
            self.llm = ChatOpenAI(
                model=settings.mistral_model,
                temperature=0.7,
                api_key=settings.mistral_api_key,
                base_url="https://api.mistral.ai/v1",
                max_tokens=6000
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

    @staticmethod
    def _clean_llm_json(raw: str) -> str:
        """Aggressively clean LLM output to extract valid JSON."""
        text = raw.strip()
        # Remove markdown fences
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()
        # If there's text before the first {, strip it
        brace = text.find('{')
        if brace > 0:
            text = text[brace:]
        # Find the last }
        last_brace = text.rfind('}')
        if last_brace != -1:
            text = text[:last_brace + 1]
        return text

    @staticmethod
    def _normalize_bullets(raw_bullets) -> list:
        """
        Flatten any nested / object-shaped bullet_points into a flat list of plain strings.
        Handles common LLM output shapes:
          - {"left_column": [...], "right_column": [...]}
          - {"column": "...", "points": [...]}
          - {"text": "..."}
          - {"header": "...", "items": [...]}
          - nested lists [[...], [...]]
        Also strips markdown formatting (**, *, #, `) from each bullet.
        """
        if raw_bullets is None:
            return []

        result: list[str] = []

        def _extract(item):
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    # Strip markdown bold / italic / heading / code markers
                    cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', cleaned)
                    cleaned = cleaned.replace('*', '').replace('#', '').replace('`', '')
                    cleaned = re.sub(r'^[-•–—]\s*', '', cleaned).strip()
                    if cleaned:
                        result.append(cleaned)
            elif isinstance(item, dict):
                # Try known column/object patterns
                for key in ("left_column", "right_column", "column_1", "column_2",
                            "points", "items", "bullets", "content"):
                    val = item.get(key)
                    if isinstance(val, list):
                        for sub in val:
                            _extract(sub)
                    elif isinstance(val, str):
                        _extract(val)
                # Handle {"column": "Title", "points": [...]}
                col_title = item.get("column") or item.get("header") or item.get("title")
                if isinstance(col_title, str) and col_title.strip():
                    _extract(col_title)
                # Handle {"text": "..."}
                text_val = item.get("text")
                if isinstance(text_val, str):
                    _extract(text_val)
            elif isinstance(item, list):
                for sub in item:
                    _extract(sub)

        if isinstance(raw_bullets, dict):
            _extract(raw_bullets)
        elif isinstance(raw_bullets, list):
            for bullet in raw_bullets:
                _extract(bullet)
        else:
            _extract(raw_bullets)

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for b in result:
            if b not in seen:
                seen.add(b)
                deduped.append(b)
        return deduped

    async def generate_slides(self, topic: str, num_slides: int = 10,
                              difficulty: str = "intermediate") -> dict:
        """
        Generate a complete slide deck with speaker notes for a topic.
        Includes retry logic and comprehensive fallback.
        """
        num_slides = max(6, min(num_slides, 18))

        prompt = f"""You are an expert educator creating a whiteboard-style presentation that a teacher draws on a board while explaining.

Topic: {topic}
Target slides: {num_slides}
Difficulty level: {difficulty}

Create a compelling, educational slide deck. Return ONLY valid JSON (no markdown, no extra text).

JSON format:
{{
  "title": "Presentation Title",
  "subtitle": "A concise tagline",
  "total_slides": {num_slides},
  "estimated_duration_minutes": <number>,
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slide Title",
      "layout": "title",
      "bullet_points": ["Point 1", "Point 2"],
      "speaker_notes": "Natural spoken narration explaining the concepts, as if a teacher is talking at a whiteboard...",
      "image_query": "specific descriptive query for a relevant educational diagram or illustration",
      "background_style": "gradient"
    }}
  ]
}}

Layout options: "title" (first slide only), "default" (bullets + side image), "image-focus" (big image with caption), "comparison" (two-column grid), "summary" (final recap).

CRITICAL RULES:
1. You MUST generate exactly {num_slides} slides.
2. First slide: layout "title". Last slide: layout "summary".
3. bullet_points MUST be a flat array of plain strings. NO objects, NO nested structures, NO markdown.
   - WRONG: [{{"left_column": [...], "right_column": [...]}}]  
   - WRONG: ["**Bold**: description"]
   - RIGHT: ["Goal Definition: Aligns with user intent", "Planning: Breaks goals into sub-tasks"]
4. Do NOT use markdown formatting (**, *, #, `) anywhere in bullet_points or speaker_notes.
5. Each bullet point should be a clean, concise statement (8-20 words).
6. For comparison slides, list items as alternating points, NOT as column objects.
   Example for comparison: ["Reactive AI: Single-turn responses only", "Agentic AI: Multi-step autonomous tasks", "Reactive AI: No memory between interactions", "Agentic AI: Persistent memory and goals"]
7. Speaker notes are the TEACHER'S SPOKEN WORDS during the presentation. Write them as a real teacher would talk:
   - NEVER say "this slide", "on this slide", "in this slide", "the slide shows", "let's look at this slide" or any slide reference.
   - Speak DIRECTLY about the concepts, as if you're standing at a whiteboard explaining to students.
   - Use natural transitions like "Now, let's talk about...", "So here's the key idea...", "Think of it this way...", "Moving on to...", "What's really interesting is...".
   - Explain each point with real examples, analogies, or context.
   - Sound conversational and engaging, like a passionate teacher, NOT like reading a textbook.
   - Example WRONG: "This slide covers the three types of machine learning."
   - Example RIGHT: "So there are three main types of machine learning, and each works in a fundamentally different way. Let me walk you through them."
8. Speaker notes should be 80-150 words per slide for good pacing.
9. image_query MUST be highly specific and directly relevant to THAT particular slide's content.
   - Include the subject matter + type of visual (diagram, illustration, photo, chart, etc.)
   - WRONG: "machine learning" (too generic, same for every slide)
   - WRONG: "AI technology" (vague, could be anything)
   - RIGHT: "supervised learning training data labeled examples diagram"
   - RIGHT: "decision tree classifier flowchart with branches"
   - RIGHT: "gradient descent optimization 3D surface plot"
   - Each slide MUST have a DIFFERENT, UNIQUE image_query that matches its specific content.
10. Cover the topic with a logical flow: introduction → core concepts → how it works → examples → applications → challenges → summary.
11. Use a variety of layouts: mostly "default", with 1-2 "comparison", 1-2 "image-focus".
12. Ensure each slide has 3-5 bullet points (except title which has 1-2, and summary which has 4-5 takeaways).
"""

        last_error = None
        for attempt in range(3):
            try:
                logger.info(f"Generating {num_slides} slides for topic: {topic} (attempt {attempt + 1})")
                response = await self._call_llm_with_fallback([HumanMessage(content=prompt)])
                raw = response.content.strip()
                cleaned = self._clean_llm_json(raw)

                data = json.loads(cleaned)

                # Validate structure
                if "slides" not in data:
                    raise ValueError("Missing 'slides' key in response")

                if len(data["slides"]) < 2:
                    raise ValueError(f"Too few slides: {len(data['slides'])}")

                slides = []
                for s in data["slides"]:
                    raw_bullets = s.get("bullet_points", [])
                    clean_bullets = self._normalize_bullets(raw_bullets)
                    clean_notes = s.get("speaker_notes", "").replace("**", "").replace("*", "").replace("#", "").replace("`", "")
                    slides.append(SlideContent(
                        slide_number=s.get("slide_number", len(slides) + 1),
                        title=s.get("title", "").replace("**", ""),
                        bullet_points=clean_bullets,
                        speaker_notes=clean_notes,
                        image_query=s.get("image_query", topic),
                        layout=s.get("layout", "default"),
                        background_style=s.get("background_style", "gradient"),
                    ).to_dict())

                result = {
                    "title": data.get("title", topic),
                    "subtitle": data.get("subtitle", ""),
                    "total_slides": len(slides),
                    "estimated_duration_minutes": data.get("estimated_duration_minutes", len(slides) * 2),
                    "slides": slides,
                }

                logger.info(f"Generated {len(slides)} slides successfully")
                return result

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
            except Exception as e:
                last_error = e
                logger.warning(f"Slide generation error on attempt {attempt + 1}: {e}")

        # All retries failed — use comprehensive fallback
        logger.error(f"All 3 attempts failed for '{topic}': {last_error}. Using fallback.")
        return self._fallback_slides(topic, num_slides)

    def _fallback_slides(self, topic: str, num_slides: int = 10) -> dict:
        """Generate a comprehensive fallback slide deck when LLM fails."""
        slides = []

        # Slide 1: Title
        slides.append({
            "slide_number": 1,
            "title": topic.title() if topic == topic.lower() else topic,
            "bullet_points": [
                f"A comprehensive guide to {topic}",
                f"From fundamentals to advanced concepts",
            ],
            "speaker_notes": (
                f"Welcome everyone! Today we're going to explore {topic} in depth. "
                f"We'll go from the basics all the way to advanced concepts, and by "
                f"the end you'll have a solid understanding of {topic} and how it "
                f"applies in the real world. So let's get started!"
            ),
            "image_query": f"{topic} educational overview",
            "layout": "title",
            "background_style": "gradient",
        })

        # Middle slides from templates
        content_count = num_slides - 2  # exclude title + summary
        for idx in range(content_count):
            template_key = _TEMPLATE_ORDER[idx % len(_TEMPLATE_ORDER)]
            tmpl = _SLIDE_TEMPLATES[template_key]
            slides.append({
                "slide_number": idx + 2,
                "title": tmpl["title_template"].format(topic=topic),
                "bullet_points": [b.format(topic=topic) for b in tmpl["bullets_template"]],
                "speaker_notes": tmpl["notes_template"].format(topic=topic),
                "image_query": f"{topic} {tmpl['image_suffix']}",
                "layout": tmpl["layout"],
                "background_style": "gradient",
            })

        # Last slide: Summary
        slides.append({
            "slide_number": num_slides,
            "title": "Summary & Key Takeaways",
            "bullet_points": [
                f"We explored the core fundamentals of {topic}",
                "Examined real-world examples and applications",
                "Discussed challenges, best practices, and future trends",
                "Continue learning — practice and curiosity are your best tools",
            ],
            "speaker_notes": (
                f"Alright, let's wrap up everything we've covered about {topic}. We started with "
                f"the fundamentals, explored how it all works, looked at real-world examples, "
                f"and discussed both the benefits and challenges. Remember, mastering "
                f"{topic} is a journey. Keep practicing, stay curious, and don't hesitate "
                f"to dive deeper into the areas that interest you most. Thank you!"
            ),
            "image_query": f"{topic} summary conclusion",
            "layout": "summary",
            "background_style": "gradient",
        })

        return {
            "title": topic.title() if topic == topic.lower() else topic,
            "subtitle": "A comprehensive educational overview",
            "total_slides": len(slides),
            "estimated_duration_minutes": len(slides) * 2,
            "slides": slides,
        }

    async def generate_narration_script(self, slides: List[dict]) -> List[dict]:
        """
        Given slides, produce a polished narration script per slide
        suitable for TTS. Returns list of {slide_number, narration}.
        """
        notes = []
        for s in slides:
            text = s.get("speaker_notes", "")
            if not text:
                # Build natural narration from bullet points
                title = s.get('title', 'the next topic')
                bullets = s.get("bullet_points", [])
                text = f"So let's talk about {title}. "
                if bullets:
                    text += "Here are the key points. " + ". ".join(bullets[:5]) + "."
            # Clean for TTS: remove markdown artifacts and slide references
            text = text.replace("*", "").replace("#", "").replace("`", "")
            # Remove any leftover "this slide" / "on this slide" phrasing
            import re as _re
            text = _re.sub(r'(?i)\b(this|the current|the following)\s+slide\b', 'this topic', text)
            text = _re.sub(r'(?i)\bon this slide\b', 'here', text)
            text = _re.sub(r'(?i)\bthe slide (shows|covers|presents|illustrates|displays)\b', r'we see', text)
            notes.append({
                "slide_number": s["slide_number"],
                "narration": text.strip(),
            })
        return notes
