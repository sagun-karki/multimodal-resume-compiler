# STAGE 1: SEMANTIC TEXT GENERATOR

## Purpose
Write tailored resume content, dynamically scaling length based on visual layout feedback while maintaining alignment with target job requirements.

## Input Context
- Raw `user_profile.md`
- Target `job_description.txt`
- Gap Report from **Stage 0**
- Visual feedback critiques from **Stage 5** (if looping)

## Execution Logic
1. **Loop 1 (Initial Generation):** Synthesize profile data into customized LaTeX CV entries. Ensure all target keywords from Stage 0 are woven into experience descriptions and skills lists.
2. **Subsequent Loops (If Loop Feedback is `OVERFLOW`):**
   - Trim word count.
   - Condense bullet points into more concise phrasing.
   - Drop lower-priority details (keeping core keyword-rich strengths intact).
3. **Subsequent Loops (If Loop Feedback is `EMPTY_BOTTOM`):**
   - Pull in unused accomplishments or skills from `user_profile.md`.
   - Prioritize adding items that specifically address gaps flagged in Stage 0.

## Output Constraints
- Output **only** raw LaTeX structural blocks (e.g. `\cvsection`, `\cventry`, `\cvlistitem`).
- DO NOT wrap the output in Markdown code blocks (like ```latex...```). Output raw string markup.
