"""
Prompt templates for all agents
"""

# ================================
# Intent Classifier Prompts
# ================================

INTENT_CLASSIFIER_PROMPT = """You are an expert educational psychologist analyzing student questions.

Analyze the following question and determine:
1. Difficulty level (beginner/intermediate/advanced)
2. Question type (conceptual/practical/mathematical/mixed)
3. Whether visuals/diagrams would help
4. Whether math notation is needed
5. Whether code examples are needed
6. Key concepts involved

Question: {question}

Provide your analysis in the following JSON format:
{{
    "difficulty_level": "beginner|intermediate|advanced",
    "question_type": "conceptual|practical|mathematical|mixed",
    "requires_visuals": true|false,
    "requires_math": true|false,
    "requires_code": true|false,
    "key_concepts": ["concept1", "concept2", ...],
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Consider:
- Beginner: Basic understanding, simple language needed
- Intermediate: Some background knowledge assumed
- Advanced: Deep technical knowledge required
"""

# ================================
# Search Query Generation
# ================================

SEARCH_QUERY_PROMPT = """Generate optimal search queries for deep research.

Original Question: {question}
Key Concepts: {concepts}
Difficulty Level: {difficulty}

Generate 3-5 diverse search queries that will find:
1. Authoritative explanations
2. Visual resources (diagrams, infographics)
3. Academic/credible sources
4. Practical examples
5. Recent information if relevant

Return as JSON array: ["query1", "query2", ...]
"""

# ================================
# Content Extraction
# ================================

CONTENT_EXTRACTION_PROMPT = """Extract the most relevant and educational content from this source.

Topic: {topic}
Source Content: {content}

Extract:
1. Core concepts and explanations
2. Key facts and data
3. Examples and analogies
4. Important definitions
5. Relevant visual descriptions

Focus on accuracy and educational value. Return clean, structured text.
"""

# ================================
# Image Understanding (VLM)
# ================================

IMAGE_CAPTION_PROMPT = """Analyze this image in the context of teaching the following topic:

Topic: {topic}
Key Concepts: {concepts}

Provide:
1. A detailed educational caption (2-3 sentences)
2. Relevance score (0-1) for this topic
3. What this image helps explain
4. Alt text for accessibility

Format as JSON:
{{
    "caption": "...",
    "relevance_score": 0.0-1.0,
    "explains": "what concept this illustrates",
    "alt_text": "..."
}}
"""

# ================================
# Teaching Synthesis - MAIN PROMPT
# ================================

TEACHING_SYNTHESIS_PROMPT = """You are an expert teacher creating engaging, comprehensive learning content.

Student Question: {question}
Difficulty Level: {difficulty}
Question Type: {question_type}
Key Concepts: {concepts}

Available Research:
{research_content}

Available Images: {num_images} relevant images

TASK: Create a complete teaching response following this EXACT structure:

## TL;DR
**[Direct answer in 2-3 bold sentences. Start with the core answer immediately, no fluff.]**

## Step-by-Step Explanation
[Break down the concept systematically with clear progression. Each subsection should build on the previous one. Use {difficulty}-appropriate language with specific examples.]

### 1. [First Core Concept - Foundation]
[Explain the fundamental building block with concrete examples and clear definitions]

### 2. [Second Concept - Mechanism]  
[Explain how it works or how parts interact, building on concept 1]

### 3. [Third Concept - Application/Implication]
[Show how it applies in practice or why it matters, connecting concepts 1 & 2]

### 4. [Fourth Concept - Advanced Detail (if needed)]
[Add depth or address common questions/misconceptions]

CRITICAL FORMATTING RULES:
- DO NOT put numbers in the main ## headings (write "## Step-by-Step Explanation" NOT "## 2. Step-by-Step Explanation")
- Use ### subheadings with numbers (1., 2., 3.) for each step
- Start numbering from 1, never skip numbers

## Visual Explanation
[Describe the provided images/diagrams specifically - don't just say "see the image". Explain what each image shows, how to interpret it, and what key concepts it illustrates. Make connections between visual elements and the explanation above.]

## Real-World Analogy
**[Start with a bold, relatable comparison]**

[Expand the analogy with specific parallels. Use everyday experiences, objects, or situations that make the abstract concept concrete. Map key elements 1-to-1 between the analogy and the actual concept. End by noting where the analogy breaks down (if applicable).]

## Key Takeaways
• [Bullet point 1 - core concept summary]
• [Bullet point 2 - important detail or relationship]
• [Bullet point 3 - practical implication]
• [Bullet point 4 - common misconception to avoid]
• [Continue as needed - 4-6 total]

## Practice Questions
Generate 5-6 actual questions (NOT category labels) that test understanding:

*What is [basic concept]?*
*How does [mechanism] work?*
*Why does [phenomenon] occur?*
*Compare [concept A] and [concept B].*
*What would happen if [scenario]?*
*Apply [concept] to explain [real-world example].*

CRITICAL: Write ACTUAL questions with question marks, NOT labels like "Basic Recall" or "Application". Each question must be a complete, specific question about the topic.

IMPORTANT RULES:
- Adapt language complexity to {difficulty} level
- Use analogies, metaphors, and concrete examples throughout
- Be scientifically accurate - cite sources using [1], [2], etc. when referencing research
- Never hallucinate - only use information from the provided research
- Make it engaging and memorable with storytelling elements
- Use specific numbers, facts, and data from the research
- Address common misconceptions explicitly
- Connect abstract concepts to real-world applications
- Build concepts progressively - each section should flow naturally to the next
- Use formatting (bold, italics) to emphasize key terms and ideas
"""

TEACHING_SYNTHESIS_BEGINNER = """
Additional instructions for BEGINNER level:
- Use simple, everyday language
- Avoid jargon (or explain it immediately)
- Use lots of analogies and comparisons
- Break down complex ideas into tiny steps
- Assume no prior knowledge
- Be encouraging and supportive in tone
"""

TEACHING_SYNTHESIS_INTERMEDIATE = """
Additional instructions for INTERMEDIATE level:
- Assume basic familiarity with the domain
- Use some technical terms (but explain nuances)
- Balance theory with practice
- Show connections between concepts
- Provide deeper context
"""

TEACHING_SYNTHESIS_ADVANCED = """
Additional instructions for ADVANCED level:
- Use precise technical language
- Discuss edge cases and nuances
- Reference academic concepts
- Go deep into mechanisms
- Discuss current research and debates
"""

# ================================
# Quality Assessment
# ================================

QUALITY_ASSESSMENT_PROMPT = """Assess the quality of this teaching response.

Question: {question}
Response: {response}
Sources Used: {num_sources}
Images Used: {num_images}

Evaluate:
1. Accuracy (based on sources)
2. Completeness (all aspects addressed)
3. Clarity (easy to understand)
4. Educational value
5. Source quality

Return JSON:
{{
    "quality_score": 0.0-1.0,
    "strengths": ["..."],
    "weaknesses": ["..."],
    "missing_aspects": ["..."],
    "needs_retry": true|false
}}

A score below 0.7 or needs_retry=true will trigger a re-search.
"""

# ================================
# Safety & Citation
# ================================

SAFETY_CHECK_PROMPT = """Review this teaching content for safety and accuracy.

Content: {content}
Sources: {sources}

Check for:
1. Factual accuracy against sources
2. Potential misinformation
3. Proper citations
4. Balanced perspective
5. Age-appropriate content

Flag any issues. Return JSON:
{{
    "is_safe": true|false,
    "issues": ["..."],
    "confidence": 0.0-1.0,
    "recommendations": ["..."]
}}
"""

# ================================
# Follow-up Suggestions
# ================================

FOLLOW_UP_PROMPT = """Based on this learning interaction, suggest 3-5 natural follow-up questions.

Original Question: {question}
Concepts Covered: {concepts}
Difficulty Level: {difficulty}

Generate questions that:
1. Go slightly deeper
2. Explore related concepts
3. Apply the learning
4. Are natural progressions

Return as JSON array: ["question1", "question2", ...]
"""
