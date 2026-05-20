# STAGE 3: HEADLESS XELATEX COMPILER

## Purpose
Run the physical document layout compilation using local engine subprocesses.

## Execution
- Invoke `subprocess.run()` to execute:
  `xelatex -interaction=nonstopmode -output-directory=output resources/resume.tex`
- The root layout document `resources/resume.tex` imports the agent-written `resources/generated_data.tex`.

## Log Sniffing & Compiler Analysis
- If compilation fails (non-zero return code or error logs), parse `output/resume.log` for compilation error logs.
- Extract syntax errors and pass them back to Stage 1 as a critique, avoiding infinite compilation loops.

## LaTeX Geometric Width Validation (The `\sbox` Check)
To achieve mathematical certainty on text wrapping without guessing, implement a custom validation macro in the LaTeX stylesheet/wrapper template:
```latex
\newsavebox{\linebox}
\newcommand{\validatedbullet}[1]{%
  \sbox{\linebox}{#1}% Save the text to a geometric measurement box
  \ifdim\wd\linebox>\textwidth% If the text box width is wider than the page text width
    \typeout{LATEX_METRIC: BULLET_OVERFLOW_DETECTED}% Write directly to the log file!
  \fi
  \cvlistitem{#1}% Render the bullet normally
}
```
If the Python engine reads `LATEX_METRIC: BULLET_OVERFLOW_DETECTED` inside `output/resume.log`, it automatically marks that round as an overflow layout failure and instructs Stage 1 to trim the offending text block.
