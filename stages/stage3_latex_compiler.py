import os
import subprocess

def run_stage3(main_tex_path: str, output_dir: str) -> tuple[bool, str, list[str]]:
    """
    Stage 3: Headless XeLaTeX Compiler
    Compiles the LaTeX source file and parses compile logs for errors or horizontal line overflows.
    
    Returns: (success_status, critique_message, overflowing_bullets)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Read main_tex_path and dynamically inject the \validatedbullet macro definition
    with open(main_tex_path, "r", encoding="utf-8") as f:
        main_content = f.read()

    # Inline any \input{...} statements by copying the referenced file's contents inline
    import re
    def replace_input_match(match):
        rel_path = match.group(1).strip()
        base_dir = os.path.dirname(main_tex_path)
        # Try relative to workspace root (parent of resources/) or directly
        abs_path = os.path.abspath(os.path.join(base_dir, "..", rel_path))
        if not os.path.exists(abs_path):
            abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f_in:
                return f_in.read()
        return match.group(0)

    main_content = re.sub(r'\\input\{([^}]+)\}', replace_input_match, main_content)
        
    macro_definition = """
% Custom wrapping helper to measure text width and output warning/orphan tags to the compile log
\\newsavebox{\\linebox}
\\newcommand{\\validatedbullet}[1]{%
  \\sbox{\\linebox}{#1}% Save the text to a geometric measurement box
  \\ifdim\\wd\\linebox>2\\linewidth% If the text box width is wider than two lines text width
    \\typeout{LATEX_METRIC: BULLET_OVERFLOW_DETECTED: #1}% Write directly to log!
  \\else
    \\ifdim\\wd\\linebox>\\linewidth% If it wraps to the second line
      \\ifdim\\wd\\linebox<1.5\\linewidth% But is less than 1.5 lines (underfilled/orphan)
        \\typeout{LATEX_METRIC: BULLET_ORPHAN_DETECTED: #1}%
      \\fi
    \\fi
  \\fi
  \\item #1% Render bullet
}

\\newcommand{\\validatedskill}[1]{%
  \\sbox{\\linebox}{#1}% Save the skill text to geometric measurement box
  \\ifdim\\wd\\linebox>\\linewidth% If it wraps to the second line at all (strictly > 1.0 lines)
    \\typeout{LATEX_METRIC: SKILL_OVERFLOW_DETECTED: #1}%
  \\fi
  \\item #1% Render skill
}
"""
    if "\\begin{document}" in main_content:
        compile_content = main_content.replace("\\begin{document}", macro_definition + "\n\\begin{document}")
    else:
        compile_content = macro_definition + "\n" + main_content
        
    compile_tex_path = os.path.join(output_dir, "resume_compile.tex")
    with open(compile_tex_path, "w", encoding="utf-8") as f:
        f.write(compile_content)

    # Run xelatex compilation subprocess
    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        f"-output-directory={output_dir}",
        compile_tex_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
    except subprocess.TimeoutExpired:
        return False, "STATUS: COMPILATION_FAILED\nCRITIQUE: XeLaTeX compilation timed out (exceeded 30 seconds).", []
    
    # Copy log and pdf outputs from resume_compile to resume
    import shutil
    compile_log = os.path.join(output_dir, "resume_compile.log")
    log_path = os.path.join(output_dir, "resume.log")
    if os.path.exists(compile_log):
        shutil.copy(compile_log, log_path)
        
    compile_pdf = os.path.join(output_dir, "resume_compile.pdf")
    pdf_path = os.path.join(output_dir, "resume.pdf")
    if os.path.exists(compile_pdf):
        shutil.copy(compile_pdf, pdf_path)
    
    # Parse logs if they exist
    if not os.path.exists(log_path):
        return False, f"STATUS: COMPILATION_FAILED\nCRITIQUE: Log file not found. System output: {result.stderr}", []
        
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        log_content = f.read()

    # Check for critical TeX error markers
    if result.returncode != 0 or "!" in log_content:
        # Extract the line containing the error
        error_lines = [line for line in log_content.splitlines() if line.startswith("!")]
        critique = "STATUS: COMPILATION_FAILED\nCRITIQUE: LaTeX compilation syntax error:\n"
        critique += "\n".join(error_lines[:3])
        return False, critique, []

    overflowing_bullets = []
    orphan_bullets = []
    skill_overflow_bullets = []
    
    prefix_overflow = "LATEX_METRIC: BULLET_OVERFLOW_DETECTED:"
    prefix_orphan = "LATEX_METRIC: BULLET_ORPHAN_DETECTED:"
    prefix_skill = "LATEX_METRIC: SKILL_OVERFLOW_DETECTED:"
    
    for line in log_content.splitlines():
        if line.startswith(prefix_overflow):
            bullet_text = line[len(prefix_overflow):].strip()
            if bullet_text and bullet_text not in overflowing_bullets:
                overflowing_bullets.append(bullet_text)
        elif line.startswith(prefix_orphan):
            bullet_text = line[len(prefix_orphan):].strip()
            if bullet_text and bullet_text not in orphan_bullets:
                orphan_bullets.append(bullet_text)
        elif line.startswith(prefix_skill):
            bullet_text = line[len(prefix_skill):].strip()
            if bullet_text and bullet_text not in skill_overflow_bullets:
                skill_overflow_bullets.append(bullet_text)

    failing_bullets = []
    critique_parts = []
    
    if overflowing_bullets:
        bullet_list_str = "\n- ".join([f'"{b[:40]}..."' for b in overflowing_bullets])
        critique_parts.append(
            f"Horizontal line overflow detected! The following bullet points exceed 2 full lines of text:\n- {bullet_list_str}"
        )
        failing_bullets.extend(overflowing_bullets)
        
    if orphan_bullets:
        bullet_list_str = "\n- ".join([f'"{b[:40]}..."' for b in orphan_bullets])
        critique_parts.append(
            f"Orphan line layout issue detected! The following bullet points wrap to a second line but fill less than 1.5 lines (leaving a dangling orphan on the new line):\n- {bullet_list_str}"
        )
        failing_bullets.extend(orphan_bullets)

    if skill_overflow_bullets:
        skill_list_str = "\n- ".join([f'"{b[:40]}..."' for b in skill_overflow_bullets])
        critique_parts.append(
            f"Skill category overflow detected! The following skill categories wrap to a second line (strictly > 1.0 lines). You MUST remove the least relevant skills to make them fit on a single line:\n- {skill_list_str}"
        )
        failing_bullets.extend(skill_overflow_bullets)

    if failing_bullets:
        err_msg = "STATUS: OVERFLOW\nCRITIQUE: " + "\n\n".join(critique_parts)
        return False, err_msg, failing_bullets

    return True, "", []
