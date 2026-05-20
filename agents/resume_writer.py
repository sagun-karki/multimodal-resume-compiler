import json
import os
import jinja2
from agents.base import BaseAgent
from utils.config import TEXT_MODEL
from utils.context import PipelineContext
from utils.validation import validate_resume_json

def sanitize_latex_chars(latex_content: str) -> str:
    import re
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
        super().__init__(
            name="Resume Writer Agent",
            system_instruction=system_instruction,
            model_name=TEXT_MODEL,
            tracker=tracker
        )

    def optimize_single_bullet(self, bullet: str, direction: str, gap_report: dict) -> str:
        bullet_system_prompt = (
            "You are an expert resume optimizer and copywriter.\n"
            "Your task is to take a single resume bullet point and rewrite it. Follow these constraints:\n"
            f"1. DIRECTION: You must {direction} the bullet point.\n"
            "   - If 'shorten': rewrite the bullet point to be more concise (ideally under 85 characters, and strictly under 90 characters) so that it fits on a single line, while keeping the core achievements and ATS keywords.\n"
            "   - If 'lengthen': expand and enrich the bullet point with more detail (making it longer) to occupy more space naturally.\n"
            "2. Keep the formatting standard: Only return the raw text content.\n"
            "3. Subtlety constraint: Make as little edit as possible. Ensure the output remains as close to the original as possible. Do not hyper-tailor or embellish facts to fit the ATS keywords.\n"
            "4. Do NOT wrap your output in markdown, quotes, or any formatting. Return ONLY the rewritten text of the bullet point."
        )
        import google.generativeai as genai
        temp_model = genai.GenerativeModel(
            model_name=TEXT_MODEL,
            system_instruction=bullet_system_prompt
        )
        user_message = (
            f"ORIGINAL BULLET POINT: {bullet}\n"
            f"ATS KEYWORDS CONTEXT: {gap_report.get('target_keywords', []) if isinstance(gap_report, dict) else []}"
        )
        from utils.helpers import track_tokens
        response = temp_model.generate_content(
            user_message,
            generation_config={"temperature": 0.2}
        )
        track_tokens(response, self.tracker)
        return response.text.strip()

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
        # Case A: Surgical bullet rewrite
        if previous_json and failing_bullets:
            updated_json = previous_json
            for old_bullet in failing_bullets:
                if self._is_bullet_in_skipped_section(updated_json, old_bullet, skipped_sections):
                    continue
                new_bullet = self.optimize_single_bullet(old_bullet, direction, gap_report)
                self._replace_bullet_in_json(updated_json, old_bullet, new_bullet)
            
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
                "response_mime_type": "application/json"
            }
        )
        track_tokens(response, self.tracker)
        
        json_str = response.text.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
            
        resume_json = validate_resume_json(json.loads(json_str))
        latex_content = render_resume_template(resume_json)
        return sanitize_latex_chars(latex_content), resume_json

    def _replace_bullet_in_json(self, resume_json: dict, old_bullet: str, new_bullet: str):
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

    def _is_bullet_in_skipped_section(self, resume_json: dict, bullet: str, skipped_sections: list[str]) -> bool:
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
