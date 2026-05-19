import os
from openai import OpenAI
from utils.config import TEXT_MODEL
from utils.token_tracker import TokenTracker

def run_stage1(profile_path: str, jd_path: str, gap_report: dict, critique: str, tracker: TokenTracker) -> str:
    """
    Stage 1: Semantic Text Generator
    Writes tailored resume content, incorporating gap report findings. If visual critique feedback
    exists, it dynamically scales the content density (trimming or expanding bullet points).
    """
    client = OpenAI()

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
        "All space optimization must be solved via text length scaling.\n\n"
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

    response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.1
    )

    latex_content = response.choices[0].message.content.strip()

    # Track tokens
    in_tokens = response.usage.prompt_tokens
    out_tokens = response.usage.completion_tokens
    tracker.track("text", in_tokens, out_tokens)

    return latex_content
