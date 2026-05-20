# RESUME WRITER AGENT (`agents/resume_writer.py`)

## Purpose
Dynamically generate tailored resume LaTeX structures, weave target keywords into experience bullet points, and surgical rewrite items based on layout feedback.

## Execution Flow
1. **Initial Draft (Iteration 1):** Takes user profile details and the analyzer's gaps report. Drafts tailored LaTeX experience blocks and skills list, infusing the keywords selected in the UI.
2. **Shorten Corrections (If layout overflows):** When compiler tools or the `VisualAuditorAgent` detect layout overflow, the writer is given the specific offending bullet points and instructed to condense them.
3. **Lengthen Corrections (If page has empty bottom spacing):** When the `VisualAuditorAgent` reports `EMPTY_BOTTOM`, the writer expands selected bullet points or adds missing achievements from the user profile to fill the page perfectly.

## Key Logic & Prompts
- Inherits from `BaseAgent`.
- Outputs raw LaTeX content blocks inside a structured JSON structure:
  ```json
  {
    "latex_content": "...",
    "resume_json": { ... }
  }
  ```
- Strips markdown block wrapper backticks (e.g. ` ```latex `) automatically before returning to ensure compiler safety.
- Operates under strict guardrails to never modify the LaTeX template style parameters, adjusting spacing, margins or class definitions.
