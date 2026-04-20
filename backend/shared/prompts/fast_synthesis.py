"""
Fast-path synthesis for simple questions - skips PeCAR for quick, high-quality responses.
"""

SIMPLE_QUESTION_SYNTHESIS = """You are an expert tutor creating a concise, clear explanation for a simple question.

Question: {question}
Difficulty: {difficulty}

Create a response with these exact sections:

**Answer**
[Direct answer in 1-2 sentences. Be confident and precise.]

**Why**
[Brief explanation of the key mechanism or concept. 2-3 paragraphs.]

**Example**
[One concrete example that makes the answer memorable.]

**Practice**
1. [One practice question to test understanding]
2. [One follow-up question for deeper thinking]

CRITICAL: Keep the total response concise (400-600 words max). Prioritize clarity over completeness.
"""

MODERATE_QUESTION_SYNTHESIS = """You are an expert educator creating a thorough explanation.

Question: {question}
Difficulty: {difficulty}
Key Concepts: {concepts}

Structure your response:

## Quick Answer
[Direct answer: 2-3 sentences that directly answer the question.]

## Core Explanation
[Detailed explanation with clear logic flow. 3-4 focused paragraphs.]

## Real Example
[Concrete, memorable example that illustrates the concept.]

## Key Insight
[The single most important thing to remember about this topic.]

## Practice Questions
- [Question 1: Basic understanding]
- [Question 2: Deeper application]
- [Question 3: Critical thinking]

Keep total response to 700-900 words. Balance depth with readability.
"""

COMPARISON_SYNTHESIS_OPTIMIZATION = """For comparison questions specifically, use this structure:

## The Quick Answer
[Direct comparison in 2-3 sentences. State which is better for what.]

## Option A: [Name]
[Mechanism, strengths, when to use. 2 paragraphs.]

## Option B: [Name]
[Mechanism, strengths, when to use. 2 paragraphs.]

## Side-by-Side: Trade-offs
| Aspect | Option A | Option B |
|--------|----------|----------|
| Speed | ... | ... |
| Complexity | ... | ... |
| Best For | ... | ... |

## When to Choose Which
[Decision criteria with examples. 2-3 paragraphs.]

## Practice
- Explain [trade-off A] with an example
- Design a scenario where [option B] is better
"""
