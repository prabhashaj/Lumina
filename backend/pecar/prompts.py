"""
PeCAR prompt templates — all mode-specific and stage-specific prompts
used throughout the 6-stage pipeline.
"""

from __future__ import annotations

import textwrap
from typing import Dict, List

from pecar.models import LearningMode


# ---------------------------------------------------------------------------
# Stage 1: Strategy-aware system preambles (per learning mode)
# ---------------------------------------------------------------------------

SYSTEM_RESEARCH = textwrap.dedent("""\
    You are a rigorous academic research assistant. Your role is to provide
    deeply sourced, analytically rich explanations grounded in retrieved evidence.
    Always cite your sources, present multiple perspectives where they exist, and
    reason step-by-step before delivering conclusions.\
""")

SYSTEM_EXAM_PREP = textwrap.dedent("""\
    You are an expert examiner and tutor preparing a student for high-stakes assessment.
    Structure your response to highlight what examiners look for: key definitions,
    mark-scheme logic, common mistakes to avoid, and worked examples. Be thorough
    and exam-focused.\
""")

SYSTEM_PERSONALIZED = textwrap.dedent("""\
    You are a personalised learning coach who deeply understands this learner.
    Adapt your vocabulary, analogies, and scaffolding to the learner's current
    knowledge level. Build on what they already know. Use relatable examples
    and check for understanding throughout.\
""")

SYSTEM_VIDEO_LECTURE = textwrap.dedent("""\
    You are an engaging, expert lecturer preparing structured content for a video lesson.
    Your response should feel like a well-paced lecture: begin with an overview,
    explain concepts progressively, use vivid examples, and close with a summary
    and takeaways. Write in a clear, spoken-word style.\
""")

SYSTEM_DOUBT_SOLVER = textwrap.dedent("""\
    You are a patient, Socratic tutor who specialises in resolving misconceptions.
    Identify the root of the learner's confusion, then guide them to the correct
    understanding step by step using hints before revealing full explanations.
    Validate their thinking where correct and gently correct where wrong.\
""")

SYSTEM_TEMPLATES: Dict[LearningMode, str] = {
    LearningMode.RESEARCH: SYSTEM_RESEARCH,
    LearningMode.EXAM_PREP: SYSTEM_EXAM_PREP,
    LearningMode.PERSONALIZED: SYSTEM_PERSONALIZED,
    LearningMode.VIDEO_LECTURE: SYSTEM_VIDEO_LECTURE,
    LearningMode.DOUBT_SOLVER: SYSTEM_DOUBT_SOLVER,
}


# ---------------------------------------------------------------------------
# Stage 3: RG-CoT prompts
# ---------------------------------------------------------------------------

RG_COT_STEP = textwrap.dedent("""\
    You are reasoning through a problem step by step.
    Previous steps completed:
    {previous_steps}

    Retrieved context:
    {retrieved_context}

    Now produce ONLY the next single reasoning step (Step {step_num}).
    Be precise. Ground your reasoning in the retrieved context where relevant.
    Step {step_num}:\
""")

RG_COT_VERIFY = textwrap.dedent("""\
    Evaluate whether the following reasoning step is supported, contradicted,
    or unverifiable based on the retrieved source excerpts.

    Reasoning Step:
    {step_content}

    Retrieved Sources:
    {sources}

    Respond in JSON with keys:
      "status": one of "verified" | "contradicted" | "unverifiable"
      "supporting_excerpt": (if verified) the most relevant excerpt
      "contradicting_source": (if contradicted) the source that contradicts it
      "corrective_context": (if contradicted) a corrective fact from the sources
      "confidence_delta": float in [-0.3, 0.0] representing confidence adjustment\
""")

RG_COT_REGENERATE = textwrap.dedent("""\
    The previous reasoning step was found to be contradicted by retrieved sources.

    Original step: {original_step}
    Corrective context: {corrective_context}

    Please regenerate this reasoning step so it is consistent with the
    corrective context. Maintain the same step purpose but fix the factual error.
    Corrected Step {step_num}:\
""")


# ---------------------------------------------------------------------------
# Stage 4: PMPS prompts
# ---------------------------------------------------------------------------

PMPS_GENERATE_PATH = textwrap.dedent("""\
    {system_prompt}

    Query: {query}

    Retrieved context:
    {retrieved_context}

    Learner profile: knowledge_level={knowledge_level}, style={style}

    Reasoning approach for this path (Path {path_index}/{total_paths}):
    {path_instruction}

    Produce a complete, well-structured response with {num_steps} reasoning steps
    followed by a final synthesised answer. Label steps as "Step 1:", "Step 2:", etc.
    End with "Final Answer:"\
""")

PATH_INSTRUCTIONS: List[str] = [
    "Prioritise factual precision and source citation. Be concise and accurate.",
    "Prioritise explanation clarity: use simple language, analogies, and concrete examples.",
    "Prioritise scaffolding: include worked examples, analogies, and practice questions.",
    "Balance factual depth with engaging narrative suitable for the learner level.",
    "Focus on common misconceptions and contrast correct vs incorrect understanding.",
]

PMPS_MERGE = textwrap.dedent("""\
    You are synthesising the best elements from multiple reasoning paths into
    a single, optimal educational response.

    Top-scored paths (with their pedagogical strengths):
    {top_paths_summary}

    Merge instructions:
    - Use factually accurate content from the highest-accuracy path
    - Adopt the clearest explanations and analogies from the highest-clarity path
    - Include scaffolding elements (examples, questions) from the best-scaffolded path
    - Ensure the merged response flows naturally and is not repetitive
    - Adapt language to: knowledge_level={knowledge_level}, style={style}

    Produce the merged, optimal response:\
""")


# ---------------------------------------------------------------------------
# Stage 5: QFPR prompts
# ---------------------------------------------------------------------------

QFPR_GRADIENT = textwrap.dedent("""\
    An educational AI response has been evaluated and received low scores on
    specific quality dimensions. Generate a textual gradient — a precise,
    actionable description of the weaknesses and how to fix them.

    Response excerpt:
    {response_excerpt}

    Evaluation scores:
    {eval_scores}

    Dimension requiring improvement: {weak_dimension}
    Score: {score:.2f} (threshold: {threshold:.2f})

    Textual gradient (be specific about what is missing or wrong and
    exactly what should be added or changed):\
""")

QFPR_REFINE = textwrap.dedent("""\
    Refine the following educational response to address the identified weakness.

    Original response:
    {original_response}

    Identified weakness (textual gradient):
    {textual_gradient}

    Dimension to fix: {weak_dimension}

    Constraints:
    - Keep all correct content from the original
    - Only add or modify what is needed to address the weakness
    - Maintain the original mode and learner level
    - Do NOT introduce factual errors

    Refined response:\
""")


# ---------------------------------------------------------------------------
# Stage 6: MSOA output templates
# ---------------------------------------------------------------------------

OUTPUT_RESEARCH = textwrap.dedent("""\
    ## {title}

    **TL;DR:** {tldr}

    ### Detailed Explanation
    {explanation}

    ### Key Concepts
    {key_concepts}

    ### Sources
    {sources}\
""")

OUTPUT_EXAM_PREP = textwrap.dedent("""\
    ## Exam Preparation: {title}

    **Key Definition:** {key_definition}

    ### Step-by-Step Breakdown
    {explanation}

    ### Worked Example
    {worked_example}

    ### Common Mistakes to Avoid
    {common_mistakes}

    ### Practice Questions
    {practice_questions}\
""")

OUTPUT_PERSONALIZED = textwrap.dedent("""\
    ## {title}

    {personalised_intro}

    ### Explanation
    {explanation}

    ### Analogy for You
    {analogy}

    ### Try It Yourself
    {practice_question}

    ### What to Explore Next
    {next_steps}\
""")

OUTPUT_VIDEO_LECTURE = textwrap.dedent("""\
    ## Lecture: {title}

    **Overview:** {overview}

    ---

    ### Introduction
    {introduction}

    ### Core Concepts
    {core_concepts}

    ### Examples & Demonstrations
    {examples}

    ### Summary & Takeaways
    {summary}

    ### Further Reading
    {further_reading}\
""")

OUTPUT_DOUBT_SOLVER = textwrap.dedent("""\
    ## Clearing Up Your Doubt: {title}

    **Root of the Confusion:** {root_confusion}

    ### Let's Work Through It Together
    {guided_steps}

    ### The Correct Understanding
    {correct_understanding}

    ### Quick Check
    {quick_check}\
""")

OUTPUT_TEMPLATES: Dict[LearningMode, str] = {
    LearningMode.RESEARCH: OUTPUT_RESEARCH,
    LearningMode.EXAM_PREP: OUTPUT_EXAM_PREP,
    LearningMode.PERSONALIZED: OUTPUT_PERSONALIZED,
    LearningMode.VIDEO_LECTURE: OUTPUT_VIDEO_LECTURE,
    LearningMode.DOUBT_SOLVER: OUTPUT_DOUBT_SOLVER,
}
