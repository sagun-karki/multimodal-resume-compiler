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
        
    macro_definition = """
% Custom wrapping helper to measure text width and output warning tags to the compile log
\\newsavebox{\\linebox}
\\newcommand{\\validatedbullet}[1]{%
  \\sbox{\\linebox}{#1}% Save the text to a geometric measurement box
  \\ifdim\\wd\\linebox>2\\textwidth% If the text box width is wider than two lines text width
    \\typeout{LATEX_METRIC: BULLET_OVERFLOW_DETECTED: #1}% Write directly to log!
  \\fi
  \\item #1% Render bullet
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
    # Parse the custom bullet overflow metric
    prefix = "LATEX_METRIC: BULLET_OVERFLOW_DETECTED:"
    for line in log_content.splitlines():
        if line.startswith(prefix):
            bullet_text = line[len(prefix):].strip()
            if bullet_text and bullet_text not in overflowing_bullets:
                overflowing_bullets.append(bullet_text)

    if overflowing_bullets:
        bullet_list_str = "\n- ".join([f'"{b[:40]}..."' for b in overflowing_bullets])
        err_msg = (
            f"STATUS: OVERFLOW\n"
            f"CRITIQUE: Horizontal line overflow detected! The following bullet points "
            f"exceed the maximum geometric width boundaries (exceeding 2 full lines of text):\n"
            f"- {bullet_list_str}\n"
            f"Please shorten these experience descriptions."
        )
        return False, err_msg, overflowing_bullets

    return True, "", []
