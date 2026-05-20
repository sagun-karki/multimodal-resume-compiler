import json
from agents.base import BaseAgent
from utils.config import TEXT_MODEL
from utils.context import PipelineContext
from utils.validation import validate_gap_report

class ATSAnalyzerAgent(BaseAgent):
    def __init__(self, tracker: PipelineContext):
        system_prompt = (
            "You are an expert ATS optimization engine. Compare the user's master profile against the target job description. "
            "Perform a section-by-section analysis of the resume (e.g., Contact Info, Skills, Experience, Projects, Education) and "
            "identify what needs to be added, removed, or updated for each section to align it with the job description.\n\n"
            "CRITICAL SPEED & CONCISENESS RULES:\n"
            "1. Be extremely concise. Keep the overall recommendation/rationale to 1 short sentence max.\n"
            "2. Omit sections that do not require any changes. Only include sections under 'sections_analysis' that have at "
            "least one item to add, remove, or update. If a section is perfectly fine, DO NOT include its key in the output.\n\n"
            "You must respond with a valid JSON object matching this schema exactly without markdown formatting:\n"
            "{\n"
            "  \"closeness_score\": 75,\n"
            "  \"matching_strengths\": [\"list\", \"of\", \"skills\"],\n"
            "  \"critical_gaps\": [\"technologies\", \"missing\"],\n"
            "  \"target_keywords\": [\"keywords\", \"to\", \"inject\"],\n"
            "  \"sections_analysis\": {\n"
            "    \"SectionName\": {\n"
            "      \"add\": [\"item to add\"],\n"
            "      \"remove\": [\"item to remove\"],\n"
            "      \"update\": [\"item to update/revise\"],\n"
            "      \"recommendation\": \"A 1-sentence recommendation.\"\n"
            "    }\n"
            "  }\n"
            "}"
        )
        super().__init__(
            name="ATS Analyzer Agent",
            system_instruction=system_prompt,
            model_name=TEXT_MODEL,
            tracker=tracker
        )

    def analyze(self, profile_content: str, jd_content: str) -> dict:
        user_message = f"USER PROFILE:\n{profile_content}\n\nJOB DESCRIPTION:\n{jd_content}"
        response_text = self.generate_response(
            user_message,
            generation_config={"response_mime_type": "application/json"}
        )
        return validate_gap_report(json.loads(response_text))
