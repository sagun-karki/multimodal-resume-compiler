import json
import os
import google.generativeai as genai
from utils.config import TEXT_MODEL
from utils.token_tracker import TokenTracker

def run_stage0(profile_path: str, jd_path: str, tracker: TokenTracker) -> dict:
    """
    Stage 0: Semantic Gap Analyzer
    Compares the master user profile with the target job description to compute a
    closeness score, match strengths, identify gaps, and select high-priority keywords.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set in the environment.")
    genai.configure(api_key=api_key)

    # Read input files
    with open(profile_path, "r", encoding="utf-8") as f:
        profile_content = f.read()
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_content = f.read()

    system_prompt = (
        "You are an expert ATS optimization engine. Compare the user's master profile against the target job description. "
        "Identify exactly what matches, what critical technologies or experiences are missing, and which high-impact "
        "keywords must be integrated to maximize resume alignment.\n\n"
        "You must respond with a valid JSON object matching this schema exactly without markdown formatting:\n"
        "{\n"
        "  \"closeness_score\": 75,\n"
        "  \"matching_strengths\": [\"list\", \"of\", \"skills\"],\n"
        "  \"critical_gaps\": [\"technologies\", \"missing\"],\n"
        "  \"target_keywords\": [\"keywords\", \"to\", \"inject\"]\n"
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
    in_tokens = 0
    out_tokens = 0
    if response.usage_metadata:
        in_tokens = response.usage_metadata.prompt_token_count
        out_tokens = response.usage_metadata.candidates_token_count
    tracker.track("text", in_tokens, out_tokens)

    return result_data
