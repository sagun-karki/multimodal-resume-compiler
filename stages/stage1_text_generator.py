import re
import os
import google.generativeai as genai
from utils.config import TEXT_MODEL
from utils.token_tracker import TokenTracker

def extract_bullets(latex_content: str) -> list[str]:
    """
    Parses out the exact content strings inside all \validatedbullet{...} macros.
    Handles nested curly braces up to arbitrary depths.
    """
    bullets = []
    pattern = r'\\validatedbullet\{'
    for match in re.finditer(pattern, latex_content):
        start = match.end()
        brace_count = 1
        i = start
        while i < len(latex_content) and brace_count > 0:
            if latex_content[i] == '{':
                brace_count += 1
            elif latex_content[i] == '}':
                brace_count -= 1
            i += 1
        if brace_count == 0:
            bullet_text = latex_content[start:i-1]
            if bullet_text not in bullets:
                bullets.append(bullet_text)
    return bullets

def optimize_single_bullet(bullet: str, direction: str, gap_report: dict, tracker: TokenTracker) -> str:
    """
    Surgically re-writes a single bullet point to be shorter or longer.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set in the environment.")
    genai.configure(api_key=api_key)

    system_prompt = (
        "You are an expert resume optimizer and copywriter.\n"
        "Your task is to take a single resume bullet point and rewrite it. Follow these constraints:\n"
        f"1. DIRECTION: You must {direction} the bullet point.\n"
        "   - If 'shorten': rewrite the bullet point to be more concise (ideally under 85 characters, and strictly under 90 characters) so that it fits on a single line, while keeping the core achievements and ATS keywords.\n"
        "   - If 'lengthen': expand and enrich the bullet point with more detail (making it longer) to occupy more space naturally.\n"
        "2. Keep the formatting standard: Do NOT include \\validatedbullet{...} or any LaTeX wrapper command. Only return the raw text content.\n"
        "3. Subtlety constraint: Make as little edit as possible. Ensure the output remains as close to the original as possible. Do not hyper-tailor or embellish facts to fit the ATS keywords.\n"
        "4. Do NOT bold any part of the sentence inside the bullet point (never use \\textbf or other bold formatting inside the bullet text).\n"
        "5. Do NOT wrap your output in markdown, quotes, or any formatting. Return ONLY the rewritten text of the bullet point."
    )

    user_message = (
        f"ORIGINAL BULLET POINT: {bullet}\n"
        f"ATS KEYWORDS CONTEXT: {gap_report.get('target_keywords', []) if isinstance(gap_report, dict) else []}"
    )

    model = genai.GenerativeModel(
        model_name=TEXT_MODEL,
        system_instruction=system_prompt
    )

    response = model.generate_content(
        user_message,
        generation_config={"temperature": 0.2}
    )

    new_bullet = response.text.strip()
    
    # Track tokens
    in_tokens = 0
    out_tokens = 0
    if response.usage_metadata:
        in_tokens = response.usage_metadata.prompt_token_count
        out_tokens = response.usage_metadata.candidates_token_count
    tracker.track("text", in_tokens, out_tokens)

    return new_bullet

def run_stage1(
    profile_path: str,
    jd_path: str,
    gap_report: dict,
    critique: str,
    tracker: TokenTracker,
    previous_latex: str = None,
    failing_bullets: list[str] = None,
    direction: str = "shorten"
) -> str:
    """
    Stage 1: Semantic Text Generator (with Surgical Bullet Optimization Support)
    If previous_latex and failing_bullets are provided, surgically rewrites only those bullets.
    Otherwise, generates the full resume dynamic body from scratch.
    """
    # CASE A: Surgical Optimization
    if previous_latex and failing_bullets:
        updated_latex = previous_latex
        for old_bullet in failing_bullets:
            # Re-write the single bullet
            new_bullet = optimize_single_bullet(old_bullet, direction, gap_report, tracker)
            # Find and replace in-place
            target_str = f"\\validatedbullet{{{old_bullet}}}"
            replacement_str = f"\\validatedbullet{{{new_bullet}}}"
            if target_str in updated_latex:
                updated_latex = updated_latex.replace(target_str, replacement_str)
        return updated_latex

    # CASE B: Full Initial Generation
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set in the environment.")
    genai.configure(api_key=api_key)

    with open(profile_path, "r", encoding="utf-8") as f:
        profile_content = f.read()
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_content = f.read()

    system_prompt = (
        "You are an expert resume optimizer and LaTeX typesetter.\n"
        "Your task is to take the user's master profile, the target job description, and the ATS gap analysis report, "
        "and generate a fully tailored set of resume content blocks in standard LaTeX.\n\n"
        "CORE MANDATES:\n"
        "1. Output ONLY the raw body LaTeX code starting from \\section*{SKILLS} to the end of the document. "
        "Do NOT write any header block, name, contact links, documentclass, packages, or \\begin{document}/\\end{document}.\n"
        "2. Do NOT wrap your output in markdown formatting (no ```latex wrappers). Only output raw LaTeX text.\n"
        "3. Incorporate target keywords from the gap analysis report to maximize ATS alignment.\n"
        "4. Enforce factuality: You are strictly FORBIDDEN from inventing metrics, company names, job titles, degrees, "
        "or projects. You must only use experiences and achievements verified in the master user profile.\n"
        "5. Formatting constraint: Use the \\validatedbullet{...} command for all bullet items inside experience, "
        "projects, and honors listings. Use standard \\item only for skills listing values.\n"
        "6. Spacing variables: You are FORBIDDEN from modifying margins or adding LaTeX spacing hacks like \\vspace or \\vfill. "
        "All space optimization must be solved via text length scaling.\n"
        "7. Subtlety constraint: Make as little edit as possible. Make the output as close as possible to the original user profile. Do not hyper-tailor or completely rewrite the resume just for the job description.\n"
        "8. Layout and Structural constraints:\n"
        "   - Do NOT use \\subsection or \\subsection* anywhere in the document.\n"
        "   - Do NOT bold any individual words or phrases inside the bullet points. Every bullet point text must be plain text without any \\textbf{...} wrapping inside the bullet content.\n"
        "   - The SKILLS section must use: \\begin{itemize}[leftmargin=0.7em, label={}, itemsep=0pt, parsep=0pt, topsep=0pt]\n"
        "   - EXPERIENCE section entries must be formatted exactly as:\n"
        "     \\textbf{<Job Title>} \\hfill <Date Range> \\\\\n"
        "     \\textit{<Company/Institution Name>} \\hfill \\textit{<Location>}\n"
        "     \\begin{itemize}\n"
        "       \\validatedbullet{...}\n"
        "     \\end{itemize}\n"
        "   - PROJECTS section entries must be formatted exactly as:\n"
        "     \\textbf{<Project Name> | <Technologies>} \\hfill <Date Range>\n"
        "     \\begin{itemize}\n"
        "       \\validatedbullet{...}\n"
        "     \\end{itemize}\n"
        "   - EDUCATION section must be formatted exactly as:\n"
        "     \\textbf{University of Nebraska-Lincoln} \\hfill Graduated May 2026 \\\\\n"
        "     B.S. Computer Science and Data Science; Minor in Mathematics \\hfill \\textit{Lincoln, NE}\n"
        "     (Do NOT wrap the education degree information in a bullet list)\n"
        "   - HONORS AND ACTIVITIES section must use \\begin{itemize} with \\validatedbullet{...}\n\n"
        "LAYOUT FEEDBACK HANDLING:\n"
        "If the layout feedback is OVERFLOW, you must make bullet descriptions more concise, shorten phrases, or remove "
        "lower-priority items while keeping core ATS keywords.\n"
        "If the layout feedback is EMPTY_BOTTOM, you must pull in unused achievements or projects from the profile to "
        "expand content volume and fill the page grid naturally."
    )

    user_message = (
        f"USER PROFILE:\n{profile_content}\n\n"
        f"JOB DESCRIPTION:\n{jd_content}\n\n"
        f"ATS GAP ANALYSIS REPORT:\n{gap_report}\n\n"
        f"CURRENT LAYOUT CRITIQUE (FEEDBACK LOOP):\n{critique if critique else 'No critique. This is the initial generation.'}"
    )

    # Call Gemini API
    model = genai.GenerativeModel(
        model_name=TEXT_MODEL,
        system_instruction=system_prompt
    )

    response = model.generate_content(
        user_message,
        generation_config={"temperature": 0.1}
    )

    latex_content = response.text.strip()

    # Track tokens
    in_tokens = 0
    out_tokens = 0
    if response.usage_metadata:
        in_tokens = response.usage_metadata.prompt_token_count
        out_tokens = response.usage_metadata.candidates_token_count
    tracker.track("text", in_tokens, out_tokens)

    return latex_content
