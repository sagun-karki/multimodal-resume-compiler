# COMPILER TOOL (`stages/stage2_pdf_manager.py`)

## Purpose
Invokes local XeLaTeX engines to compile the draft source files, checks compiler error outputs, and translates page height metrics into structured feedback.

## Compilation Process
1. Writes the current active LaTeX markup content to a temporary workspace target (`resources/generated_data.tex`).
2. Runs the compilation subprocess:
   ```bash
   xelatex -interaction=nonstopmode -output-directory=output resources/resume.tex
   ```
3. Parses log files (`output/resume.log`) to search for syntax issues, warning signs, and layout warnings.

## Log Analysis & Overfull Box Checks
- Parses the logs to identify warning indicators like:
  - `Overfull \vbox` (vertical overflow indicator).
  - `Overfull \hbox` (horizontal overflow indicator).
- If it detects line wraps exceeding geometric margins (using text box checking macro tags), it flags the exact bullet points and reports them to the supervisor as layout constraints violations.
