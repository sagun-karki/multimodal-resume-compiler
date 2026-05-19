import os
import subprocess

def run_stage3(main_tex_path: str, output_dir: str) -> tuple[bool, str, list[str]]:
    """
    Stage 3: Headless XeLaTeX Compiler
    Compiles the LaTeX source file and parses compile logs for errors or horizontal line overflows.
    
    Returns: (success_status, critique_message, overflowing_bullets)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Run xelatex compilation subprocess
    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        f"-output-directory={output_dir}",
        main_tex_path
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
    
    log_path = os.path.join(output_dir, "resume.log")
    
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
