import os
import re
import subprocess
import shutil
import fitz  # PyMuPDF
from PIL import Image, ImageChops

def run_stage2(main_tex_path: str, output_dir: str) -> tuple[bool, str, list[str]]:
    """
    Stage 2: Headless XeLaTeX Compiler & Page-Count Router/Rasterizer
    Compiles LaTeX source, checks logs for syntax errors or overflows, 
    verifies page counts, and rasterizes output to PNG.
    
    Returns: (success_status, critique_message, failing_bullets)
    """
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, "resume.pdf")
    png_path = os.path.join(output_dir, "resume.png")
    
    # 1. Read main_tex_path and dynamically inject the \validatedbullet macro definition
    with open(main_tex_path, "r", encoding="utf-8") as f:
        main_content = f.read()

    # Inline any \input{...} statements by copying the referenced file's contents inline
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

    # 2. Run xelatex compilation subprocess
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
    compile_log = os.path.join(output_dir, "resume_compile.log")
    log_path = os.path.join(output_dir, "resume.log")
    if os.path.exists(compile_log):
        shutil.copy(compile_log, log_path)
        
    compile_pdf = os.path.join(output_dir, "resume_compile.pdf")
    if os.path.exists(compile_pdf):
        shutil.copy(compile_pdf, pdf_path)
    
    # Parse logs if they exist
    if not os.path.exists(log_path):
        return False, f"STATUS: COMPILATION_FAILED\nCRITIQUE: Log file not found. System output: {result.stderr}", []
        
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        log_content = f.read()

    # Check for critical TeX error markers
    if result.returncode != 0 or "!" in log_content:
        error_lines = [line for line in log_content.splitlines() if line.startswith("!")]
        critique = "STATUS: COMPILATION_FAILED\nCRITIQUE: LaTeX compilation syntax error:\n"
        critique += "\n".join(error_lines[:3])
        return False, critique, []

    # 3. Parse geometric/typographic metric warnings from logs
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

    # 4. Rasterize compiled PDF using PyMuPDF (so UI is updated even if there are overflows)
    if os.path.exists(pdf_path):
        try:
            doc = fitz.open(pdf_path)
            page_count = doc.page_count
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            full_png_path = png_path.replace(".png", "_full.png")
            
            if page_count == 1:
                pix = doc[0].get_pixmap(matrix=mat)
                pix.save(full_png_path)
            else:
                rect = doc[0].rect
                tall_doc = fitz.open()
                tall_page = tall_doc.new_page(width=rect.width, height=rect.height * page_count)
                
                y_offset = 0
                for i in range(page_count):
                    target_rect = fitz.Rect(0, y_offset, rect.width, y_offset + rect.height)
                    tall_page.show_pdf_page(target_rect, doc, i)
                    y_offset += rect.height
                    
                pix = tall_page.get_pixmap(matrix=mat)
                pix.save(full_png_path)
                tall_doc.close()
                
            # Crop margins to fit content bounding box
            with Image.open(full_png_path) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                bg = Image.new("RGB", img.size, (255, 255, 255))
                diff = ImageChops.difference(img.convert("RGB"), bg)
                bbox = diff.getbbox()
                if bbox:
                    padding = 20
                    left = max(0, bbox[0] - padding)
                    top = max(0, bbox[1] - padding)
                    right = min(img.width, bbox[2] + padding)
                    bottom = min(img.height, bbox[3] + padding)
                    cropped_img = img.crop((left, top, right, bottom))
                    cropped_img.save(png_path)
                else:
                    img.save(png_path)
            
            doc.close()
            
            # Check strictly for single-page constraint violation
            if page_count != 1:
                critique = (
                    f"STATUS: OVERFLOW\n"
                    f"CRITIQUE: Page count boundary violation! The generated resume is {page_count} pages long, "
                    f"violating the strict single-page (1 page) layout constraint. The text generator must reduce "
                    f"content length or bullet descriptions to fit the single-page layout."
                )
                from utils.helpers import extract_bullets
                all_bullets = extract_bullets(main_content)
                all_bullets.sort(key=len, reverse=True)
                return False, critique, all_bullets[:3]
                
        except Exception as e:
            return False, f"STATUS: RASTERIZE_ERROR\nCRITIQUE: Failed to rasterize compiled PDF: {str(e)}", []
    else:
        return False, "STATUS: FILE_ERROR\nCRITIQUE: Compiled PDF file was not generated by XeLaTeX.", []

    # 5. Handle formatting metric issues
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
