import json
import os
import re
import jinja2
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from agents.base import BaseAgent
from utils.config import TEXT_MODEL
from utils.context import PipelineContext
from utils.validation import validate_resume_json

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

class AtomicEdit(BaseModel):
    action: str = Field(description="The action to perform, e.g., 'modify_bullet' or 'modify_skill'")
    path: str = Field(description="The JSON path to the target field, e.g., 'experience[0].bullets[2]' or 'skills.Languages[1]'")
    original: str = Field(description="The original text to be replaced")
    replacement: str = Field(description="The updated text replacement")

class ResumeEditPayload(BaseModel):
    edits: List[AtomicEdit] = Field(description="List of atomic edits to apply to the resume JSON")


# --- Helper functions for atomic edits ---

def apply_atomic_edit(resume_json: dict, edit: dict) -> bool:
    path = edit.get("path", "")
    replacement = edit.get("replacement", "")
    
    # Parse the dot-notated path with bracket support
    tokens = []
    parts = path.split('.')
    for part in parts:
        match = re.match(r'^([^\[]+)(?:\[(\d+)\])?$', part)
        if match:
            key = match.group(1)
            index = match.group(2)
            tokens.append(key)
            if index is not None:
                tokens.append(int(index))
        else:
            tokens.append(part)
            
    # Walk the dictionary and apply replacement
    curr = resume_json
    for i, token in enumerate(tokens):
        if i == len(tokens) - 1:
            if isinstance(curr, list) and isinstance(token, int):
                if 0 <= token < len(curr):
                    curr[token] = replacement
                    return True
            elif isinstance(curr, dict) and isinstance(token, str):
                curr[token] = replacement
                return True
            return False
            
        if isinstance(curr, list) and isinstance(token, int):
            if 0 <= token < len(curr):
                curr = curr[token]
            else:
                return False
        elif isinstance(curr, dict) and isinstance(token, str):
            if token in curr:
                curr = curr[token]
            else:
                return False
        else:
            return False
    return False


def _is_path_in_skipped_sections(path: str, skipped_sections: list[str]) -> bool:
    if not skipped_sections:
        return False
    parts = path.lower().split('.')
    first_part = parts[0]
    base_sec = re.sub(r'\[\d+\]', '', first_part)
    for s in skipped_sections:
        if s.lower() == base_sec:
            return True
    return False


def sanitize_latex_chars(latex_content: str) -> str:
    # Escape & (match any & not preceded by a backslash)
    latex_content = re.sub(r'(?<!\\)&', r'\\&', latex_content)
    # Escape % (match any % not preceded by a backslash)
    latex_content = re.sub(r'(?<!\\)%', r'\\%', latex_content)
    # Escape # (match any # not preceded by a backslash)
    latex_content = re.sub(r'(?<!\\)#', r'\\#', latex_content)
    return latex_content


def render_resume_template(resume_json: dict) -> str:
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    template = env.get_template("body.tex.j2")
    return template.render(**resume_json)


class ResumeWriterAgent(BaseAgent):
    def __init__(self, tracker: PipelineContext):
        system_instruction = (
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
        super().__init__(
            name="Resume Writer Agent",
            system_instruction=system_instruction,
            model_name=TEXT_MODEL,
            tracker=tracker
        )

    def write_resume(
        self,
        profile_content: str,
        jd_content: str,
        gap_report: dict,
        critique: str,
        previous_json: dict = None,
        failing_bullets: list[str] = None,
        direction: str = "shorten",
        skipped_sections: list[str] = None
    ) -> tuple[str, dict]:
        # Case A: Surgical bullet rewrite (Atomic Edits)
        if previous_json and failing_bullets:
            edit_system_instruction = (
                "You are an expert resume optimizer and copywriter.\n"
                "Your task is to review the current resume JSON draft, the layout critique feedback, and the target job description, "
                "and output a targeted list of atomic edits to apply to the resume. Follow these constraints:\n\n"
                "1. Output ONLY valid JSON matching the schema.\n"
                "2. Identify the specific bullet points or skill fields that are failing visual audit (e.g. overflowing or orphan lines) "
                "using their deterministic JSON paths (e.g., 'experience[0].bullets[2]' or 'skills.Languages[1]') and suggest targeted atomic edits.\n"
                "3. Each edit must specify the JSON path, the original text, and the replacement text.\n"
                "4. Keep formatting standard, do not hyper-tailor or embellish facts, and ensure the edits are as minimal as possible to resolve the layout issue.\n"
                "5. If direction is 'shorten': make the replacement more concise (under 85 characters, strictly under 90 characters) so it fits on a single line.\n"
                "6. If direction is 'lengthen': expand the description to occupy more space naturally.\n"
                "7. Do NOT change or rename any keys, companies, dates, or titles unless instructed."
            )
            
            import google.generativeai as genai
            custom_model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=edit_system_instruction
            )
            
            user_message = (
                f"PREVIOUS_RESUME_JSON:\n{json.dumps(previous_json, indent=2)}\n\n"
                f"JOB DESCRIPTION:\n{jd_content}\n\n"
                f"ATS GAP ANALYSIS REPORT:\n{gap_report}\n\n"
                f"FAILING_BULLETS_TO_FIX (JSON PATHS):\n{json.dumps(failing_bullets, indent=2)}\n\n"
                f"REQUIRED_DIRECTION: {direction}\n\n"
                f"CURRENT LAYOUT CRITIQUE (FEEDBACK LOOP):\n{critique if critique else 'No critique.'}"
            )
            
            from utils.helpers import track_tokens
            response = custom_model.generate_content(
                user_message,
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                    "response_schema": ResumeEditPayload
                }
            )
            track_tokens(response, self.tracker)
            
            try:
                payload = json.loads(response.text.strip())
                edits = payload.get("edits", [])
            except Exception as e:
                self.tracker.add_warning(f"Failed to parse atomic edits JSON: {str(e)}")
                edits = []
                
            updated_json = json.loads(json.dumps(previous_json)) # Deep copy
            for edit in edits:
                path = edit.get("path", "")
                if _is_path_in_skipped_sections(path, skipped_sections):
                    continue
                apply_atomic_edit(updated_json, edit)
                
            latex_content = render_resume_template(updated_json)
            return sanitize_latex_chars(latex_content), updated_json

        # Case B: Full initial generation
        sys_instr = self.system_instruction
        if skipped_sections:
            skipped_str = ", ".join(skipped_sections)
            sys_instr += (
                f"\n\nSTRICT PRESERVATION CONSTRAINT:\n"
                f"You are strictly FORBIDDEN from modifying, tailoring, adding, removing, or updating any content in the following sections: {skipped_str}.\n"
                f"For these sections, you MUST extract and copy the content and details from the USER PROFILE exactly as-is, "
                f"preserving all original bullet points, dates, descriptions, structure, and details without any changes."
            )

        import google.generativeai as genai
        custom_model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=sys_instr
        )
        
        user_message = (
            f"USER PROFILE:\n{profile_content}\n\n"
            f"JOB DESCRIPTION:\n{jd_content}\n\n"
            f"ATS GAP ANALYSIS REPORT:\n{gap_report}\n\n"
            f"CURRENT LAYOUT CRITIQUE (FEEDBACK LOOP):\n{critique if critique else 'No critique. This is the initial generation.'}"
        )
        
        from utils.helpers import track_tokens
        response = custom_model.generate_content(
            user_message,
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json",
                "response_schema": FullResumeSchema
            }
        )
        track_tokens(response, self.tracker)
        
        resume_json = json.loads(response.text.strip())
        resume_json = validate_resume_json(resume_json)
        latex_content = render_resume_template(resume_json)
        return sanitize_latex_chars(latex_content), resume_json
