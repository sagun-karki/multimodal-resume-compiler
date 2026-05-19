# STAGE 2: PROGRAMMATIC PYTHON SANITIZER

## Purpose
Ensure 100% stable document compilation and proactively catch line overflow/dangling orphan word issues before running the heavy XeLaTeX compiler subprocess.

## Task A: String Escaping
Use Python regular expressions to escape LaTeX special control characters embedded inside the raw text LLM output, preventing compiler syntax crashes:
- `(?<!\\)&` $\rightarrow$ `\\&`
- `(?<!\\)%` $\rightarrow$ `\\%`
- `(?<!\\)#` $\rightarrow$ `\\#`

## Task B: Horizontal Boundary & Orphan Pre-Checks
Because the document utilizes a proportional font (Source Sans Pro), characters differ in physical width. However, we can run a heuristic check to capture dangling single-word wraps (orphans):
- Calculate the string character count of every individual list/bullet point text.
- If a string's length falls within the risky zone of **90 to 112 characters**, it risks dropping a single word onto a new line (which wastes visual space and looks unprofessional).
- **Action:** If flagged, raise a typographic warning (`STATUS: TYPOGRAPHY_ERROR`), bypass document compilation, and route a prompt instruction directly back to Stage 1 to either shorten or lengthen the string.
