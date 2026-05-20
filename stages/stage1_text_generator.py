import re
import os
import json
import jinja2
import google.generativeai as genai
from utils.config import TEXT_MODEL
from utils.token_tracker import TokenTracker
from utils.helpers import get_api_key, track_tokens, extract_bullets

def render_resume_template(resume_json: dict) -> str:
    """Renders the LaTeX body using Jinja2."""
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    template = env.get_template("body.tex.j2")
    return template.render(**resume_json)

def optimize_single_bullet(bullet: str, direction: str, gap_report: dict, tracker: TokenTracker) -> str:
    """
    Surgically re-writes a single bullet point to be shorter or longer.
    """
    api_key = get_api_key()
    genai.configure(api_key=api_key)

    system_prompt = (
        "You are an expert resume optimizer and copywriter.\n"
        "Your task is to take a single resume bullet point and rewrite it. Follow these constraints:\n"
        f"1. DIRECTION: You must {direction} the bullet point.\n"
        "   - If 'shorten': rewrite the bullet point to be more concise (ideally under 85 characters, and strictly under 90 characters) so that it fits on a single line, while keeping the core achievements and ATS keywords.\n"
        "   - If 'lengthen': expand and enrich the bullet point with more detail (making it longer) to occupy more space naturally.\n"
        "2. Keep the formatting standard: Only return the raw text content.\n"
        "3. Subtlety constraint: Make as little edit as possible. Ensure the output remains as close to the original as possible. Do not hyper-tailor or embellish facts to fit the ATS keywords.\n"
        "4. Do NOT wrap your output in markdown, quotes, or any formatting. Return ONLY the rewritten text of the bullet point."
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
    track_tokens(response, tracker)

    return new_bullet

def _replace_bullet_in_json(resume_json: dict, old_bullet: str, new_bullet: str):
    """Mutates the resume_json in-place by replacing old_bullet with new_bullet."""
    if "experience" in resume_json:
        for job in resume_json["experience"]:
            if "bullets" in job:
                for i, bullet in enumerate(job["bullets"]):
                    if bullet.strip() == old_bullet.strip():
                        job["bullets"][i] = new_bullet
    if "projects" in resume_json:
        for project in resume_json["projects"]:
            if "bullets" in project:
                for i, bullet in enumerate(project["bullets"]):
                    if bullet.strip() == old_bullet.strip():
                        project["bullets"][i] = new_bullet
    if "honors" in resume_json:
        for i, honor in enumerate(resume_json["honors"]):
            if honor.strip() == old_bullet.strip():
                resume_json["honors"][i] = new_bullet

def run_stage1(
    profile_path: str,
    jd_path: str,
    gap_report: dict,
    critique: str,
    tracker: TokenTracker,
    previous_json: dict = None,
    failing_bullets: list[str] = None,
    direction: str = "shorten"
) -> tuple[str, dict]:
    """
    Stage 1: Semantic Text Generator (with Surgical Bullet Optimization Support)
    If previous_json and failing_bullets are provided, surgically rewrites only those bullets.
    Otherwise, generates the full resume dynamic body from scratch as JSON, and renders it to LaTeX.
    
    Returns: (latex_content, resume_json)
    """
    # CASE A: Surgical Optimization
    if previous_json and failing_bullets:
        updated_json = previous_json
        for old_bullet in failing_bullets:
            new_bullet = optimize_single_bullet(old_bullet, direction, gap_report, tracker)
            _replace_bullet_in_json(updated_json, old_bullet, new_bullet)
        
        latex_content = render_resume_template(updated_json)
        return latex_content, updated_json

    # CASE B: Full Initial Generation
    api_key = get_api_key()
    genai.configure(api_key=api_key)

    with open(profile_path, "r", encoding="utf-8") as f:
        profile_content = f.read()
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_content = f.read()

    system_prompt = (
        "You are an expert resume optimizer and data structured output generator.\n"
        "Your task is to take the user's master profile, the target job description, and the ATS gap analysis report, "
        "and generate a fully tailored set of resume content blocks in JSON format.\n\n"
        "CORE MANDATES:\n"
        "1. Output ONLY valid JSON. Do not wrap in markdown (no ```json). The schema must match the following structure:\n"
        "   {\n"
        "     \"skills\": { \"Category1\": [\"Skill1\", \"Skill2\"], \"Category2\": [...] },\n"
        "     \"experience\": [\n"
        "       {\n"
        "         \"title\": \"Job Title\",\n"
        "         \"company\": \"Company Name\",\n"
        "         \"location\": \"City, ST\",\n"
        "         \"date\": \"Start - End\",\n"
        "         \"bullets\": [\"Bullet 1\", \"Bullet 2\"]\n"
        "       }\n"
        "     ],\n"
        "     \"projects\": [\n"
        "       {\n"
        "         \"name\": \"Project Name\",\n"
        "         \"technologies\": \"Tech1, Tech2\",\n"
        "         \"date\": \"Date\",\n"
        "         \"bullets\": [\"Bullet 1\"]\n"
        "       }\n"
        "     ],\n"
        "     \"education\": [\n"
        "       {\n"
        "         \"school\": \"University Name\",\n"
        "         \"degree\": \"Degree details\",\n"
        "         \"location\": \"City, ST\",\n"
        "         \"date\": \"Graduation Date\"\n"
        "       }\n"
        "     ],\n"
        "     \"honors\": [\"Honor 1\", \"Honor 2\"]\n"
        "   }\n"
        "2. Incorporate target keywords from the gap analysis report to maximize ATS alignment.\n"
        "3. Enforce factuality: You are strictly FORBIDDEN from inventing metrics, company names, job titles, degrees, "
        "or projects. You must only use experiences and achievements verified in the master user profile.\n"
        "4. Subtlety constraint: Make as little edit as possible. Make the output as close as possible to the original user profile. Do not hyper-tailor or completely rewrite the resume just for the job description.\n"
        "5. Constraints on Bullets:\n"
        "   - Do NOT bold any individual words or phrases inside the bullet points. Every bullet point text must be plain text without any formatting wrappers.\n"
        "6. Skill Category Constraints:\n"
        "   - Keep the list of skills concise so they can fit on a single line when rendered. If a list of skills is too long, strictly remove the least relevant or least likely skills.\n"
        "7. Header Constraints:\n"
        "   - Do NOT change or rename any section headers or skill category headers. You MUST use the exact same skill category headers and section headers as they appear in the original user profile.\n\n"
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
        generation_config={
            "temperature": 0.1,
            "response_mime_type": "application/json"
        }
    )

    json_str = response.text.strip()
    
    # Remove markdown code blocks if any (just in case the model ignores instructions)
    if json_str.startswith("```json"):
        json_str = json_str[7:]
    if json_str.startswith("```"):
        json_str = json_str[3:]
    if json_str.endswith("```"):
        json_str = json_str[:-3]
        
    try:
        resume_json = json.loads(json_str)
    except json.JSONDecodeError as e:
        # Fallback if json is corrupted
        raise RuntimeError(f"Failed to decode LLM response as JSON: {e}\nResponse: {json_str}")

    # Render template
    latex_content = render_resume_template(resume_json)

    # Track tokens
    track_tokens(response, tracker)

    return latex_content, resume_json
