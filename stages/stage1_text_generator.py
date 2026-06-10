import re
import os
import json
import jinja2
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from utils.config import TEXT_MODEL
from utils.context import PipelineContext
from utils.helpers import get_api_key, track_tokens, extract_bullets

# --- Pydantic Schemas for Structured Output ---

class JobExperience(BaseModel):
    path_id: str = Field(description="Deterministic array path key identifier matching array index, e.g., 'experience[0]' or 'experience[1]'")
    title: str = Field(description="Job Title")
    company: str = Field(description="Company Name")
    location: str = Field(description="City, ST")
    date: str = Field(description="Start - End date")
    bullets: List[str] = Field(description="List of achievement bullet points")

class Project(BaseModel):
    path_id: str = Field(description="Deterministic array path key identifier matching array index, e.g., 'projects[0]' or 'projects[1]'")
    name: str = Field(description="Project Name")
    technologies: str = Field(description="Comma-separated technologies list")
    bullets: List[str] = Field(description="List of project description bullet points")

class Education(BaseModel):
    school: str = Field(description="University Name")
    degree: str = Field(description="Degree details")
    location: str = Field(description="City, ST")
    date: str = Field(description="Graduation Date")

class FullResumeSchema(BaseModel):
    skills: Dict[str, List[str]] = Field(description="Skills categorized by type exactly tracking master names")
    experience: List[JobExperience] = Field(description="Work experience list matching structural tracking")
    projects: List[Project] = Field(description="Projects list matching structural tracking")
    education: List[Education] = Field(description="Education details")
    honors: List[str] = Field(description="List of honors and activities")
    exhaustion_metadata: Dict[str, bool] = Field(
        default_factory=dict,
        description="A dictionary map marking sections as true/false to signal if all source profile bullets from user_profile.md are fully exhausted. Prevents the model from hallucinating metrics when handling EMPTY_BOTTOM status instructions."
    )


def sanitize_latex_chars(latex_content: str) -> str:
    """Escape raw special characters like &, %, # if they are not already escaped."""
    # Escape & (match any & not preceded by a backslash)
    latex_content = re.sub(r'(?<!\\)&', r'\\&', latex_content)
    # Escape % (match any % not preceded by a backslash)
    latex_content = re.sub(r'(?<!\\)%', r'\\%', latex_content)
    # Escape # (match any # not preceded by a backslash)
    latex_content = re.sub(r'(?<!\\)#', r'\\#', latex_content)
    return latex_content


def render_resume_template(resume_json: dict) -> str:
    """Renders the LaTeX body using Jinja2."""
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    template = env.get_template("body.tex.j2")
    return template.render(**resume_json)


def optimize_single_bullet(bullet: str, direction: str, gap_report: dict, tracker: PipelineContext) -> str:
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


def _is_bullet_in_skipped_section(resume_json: dict, bullet: str, skipped_sections: list[str]) -> bool:
    if not skipped_sections:
        return False
    skipped_lower = [s.lower() for s in skipped_sections]
    
    # Check experience
    if "experience" in skipped_lower:
        if "experience" in resume_json:
            for job in resume_json["experience"]:
                if "bullets" in job:
                    if any(b.strip() == bullet.strip() for b in job["bullets"]):
                        return True
                        
    # Check projects
    if "projects" in skipped_lower:
        if "projects" in resume_json:
            for project in resume_json["projects"]:
                if "bullets" in project:
                    if any(b.strip() == bullet.strip() for b in project["bullets"]):
                        return True
                        
    # Check honors
    if "honors" in skipped_lower or "awards" in skipped_lower:
        if "honors" in resume_json:
            if any(h.strip() == bullet.strip() for h in resume_json["honors"]):
                return True
                
    return False


def run_stage1(
    profile_path: str,
    jd_path: str,
    gap_report: dict,
    critique: str,
    tracker: PipelineContext,
    previous_json: dict = None,
    failing_bullets: list[str] = None,
    direction: str = "shorten",
    skipped_sections: list[str] = None
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
            if _is_bullet_in_skipped_section(updated_json, old_bullet, skipped_sections):
                continue
            new_bullet = optimize_single_bullet(old_bullet, direction, gap_report, tracker)
            _replace_bullet_in_json(updated_json, old_bullet, new_bullet)
        
        latex_content = render_resume_template(updated_json)
        return sanitize_latex_chars(latex_content), updated_json

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
        "1. Output ONLY valid JSON matching the schema.\n"
        "2. Incorporate target keywords from the gap analysis report to maximize ATS alignment.\n"
        "3. Enforce factuality: You are strictly FORBIDDEN from inventing metrics, company names, job titles, degrees, "
        "or projects. You must only use experiences and achievements verified in the master user profile.\n"
        "4. Subtlety constraint: Make as little edit as possible. Make the output as close as possible to the original user profile. Do not hyper-tailor or completely rewrite the resume just for the job description.\n"
        "5. Constraints on Bullets:\n"
        "   - Do NOT bold any individual words or phrases inside the bullet points. Every bullet point text must be plain text without any formatting wrappers.\n"
        "6. Skill Category Constraints:\n"
        "   - Keep the list of skills concise so they can fit on a single line when rendered. If a list of skills is too long, strictly remove the least relevant or least likely skills.\n"
        "7. Header Constraints:\n"
        "   - Do NOT change or rename any section headers or skill category headers. You MUST use the exact same skill category headers and section headers as they appear in the original user profile.\n"
        "8. Array Path Tracking:\n"
        "   - You MUST output the correct path_id parameter for every JobExperience and Project item matching its 0-based array index (e.g. 'experience[0]' or 'projects[1]').\n"
        "9. Content Exhaustion Tracking:\n"
        "   - Fill in exhaustion_metadata map sections to true/false signaling if all candidate bullets/metrics from the master background user_profile.md are fully exhausted. This tells the model what unused metrics remain available to fill EMPTY_BOTTOM instructions without hallucinating data.\n\n"
        "LAYOUT FEEDBACK HANDLING:\n"
        "If the layout feedback is OVERFLOW, you must make bullet descriptions more concise, shorten phrases, or remove "
        "lower-priority items while keeping core ATS keywords.\n"
        "If the layout feedback is EMPTY_BOTTOM, you must pull in unused achievements or projects from the profile to "
        "expand content volume and fill the page grid naturally."
    )

    if skipped_sections:
        skipped_str = ", ".join(skipped_sections)
        system_prompt += (
            f"\n\nSTRICT PRESERVATION CONSTRAINT:\n"
            f"You are strictly FORBIDDEN from modifying, tailoring, adding, removing, or updating any content in the following sections: {skipped_str}.\n"
            f"For these sections, you MUST extract and copy the content and details from the USER PROFILE exactly as-is, "
            f"preserving all original bullet points, dates, descriptions, structure, and details without any changes."
        )

    user_message = (
        f"USER PROFILE:\n{profile_content}\n\n"
        f"JOB DESCRIPTION:\n{jd_content}\n\n"
        f"ATS GAP ANALYSIS REPORT:\n{gap_report}\n\n"
        f"CURRENT LAYOUT CRITIQUE (FEEDBACK LOOP):\n{critique if critique else 'No critique. This is the initial generation.'}"
    )

    # Call Gemini API with structured schema
    model = genai.GenerativeModel(
        model_name=TEXT_MODEL,
        system_instruction=system_prompt
    )

    response = model.generate_content(
        user_message,
        generation_config={
            "temperature": 0.1,
            "response_mime_type": "application/json",
            "response_schema": FullResumeSchema
        }
    )

    # Parse directly from response using JSON loads
    resume_json = json.loads(response.text.strip())
    
    # Render template
    latex_content = render_resume_template(resume_json)

    # Track tokens
    track_tokens(response, tracker)

    return sanitize_latex_chars(latex_content), resume_json
