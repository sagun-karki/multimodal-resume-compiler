import json
import os
import google.generativeai as genai
from utils.config import TEXT_MODEL
from utils.token_tracker import TokenTracker
from utils.helpers import get_api_key, track_tokens

def run_stage0(profile_path: str, jd_path: str, tracker: TokenTracker) -> dict:
    """
    Stage 0: Semantic Gap Analyzer
    Compares the master user profile with the target job description to compute a
    closeness score, match strengths, identify gaps, and select high-priority keywords.
    """
    api_key = get_api_key()
    genai.configure(api_key=api_key)

    # Read input files
    with open(profile_path, "r", encoding="utf-8") as f:
        profile_content = f.read()
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_content = f.read()

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

    user_message = f"USER PROFILE:\n{profile_content}\n\nJOB DESCRIPTION:\n{jd_content}"

    # Call Gemini API
    model = genai.GenerativeModel(
        model_name=TEXT_MODEL,
        system_instruction=system_prompt
    )

    response = model.generate_content(
        user_message,
        generation_config={"response_mime_type": "application/json"}
    )

    result_text = response.text
    result_data = json.loads(result_text)

    # Track tokens
    track_tokens(response, tracker)

    return result_data
