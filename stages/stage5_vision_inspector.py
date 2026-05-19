import base64
import os
from openai import OpenAI
from utils.config import VISION_MODEL
from utils.token_tracker import TokenTracker

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def run_stage5(png_image_path: str, tracker: TokenTracker) -> tuple[bool, str]:
    """
    Stage 5: Vision Feedback Loop & Inspector
    Evaluates the visual layouts, margins, and space utilisation of the compiled resume.
    Identifies empty voids at the bottom (EMPTY_BOTTOM) or visual overflows (OVERFLOW).
    
    Returns: (accepted_status, critique_message)
    """
    if not os.path.exists(png_image_path):
        return False, "STATUS: FILE_ERROR\nCRITIQUE: PNG rasterized resume was not found."

    client = OpenAI()
    base64_image = encode_image(png_image_path)

    system_prompt = (
        "You are an expert design QA inspector evaluating the layout balance of a compiled resume.\n"
        "Analyze the provided image of the resume and evaluate its spacing, margins, and white space utilization.\n\n"
        "EVALUATION CRITERIA:\n"
        "1. PAGE BALANCE: Verify if the content fills the page grid elegantly. There should be uniform top/bottom margins.\n"
        "2. EMPTY BOTTOM GAP (Underutilization): If there is a massive empty space at the bottom (more than 1.5 inches of "
        "empty white background at the bottom of the page), return status EMPTY_BOTTOM and ask the system to expand descriptions "
        "or add more relevant projects/details from the profile to balance the page.\n"
        "3. OVERFLOW: If the text is clipping, overlapping, or looks overly crowded and spills onto subsequent margins, "
        "return status OVERFLOW and request text compression.\n"
        "4. ACCEPTED: If the spacing looks clean, professional, and visually balanced on exactly one page, return status ACCEPTED.\n\n"
        "You MUST respond starting with one of these exact headers:\n"
        "- STATUS: ACCEPTED\n"
        "- STATUS: EMPTY_BOTTOM\n"
        "- STATUS: OVERFLOW\n\n"
        "Followed by a detailed visual critique explaining your assessment."
    )

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": system_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        temperature=0.0
    )

    critique = response.choices[0].message.content.strip()

    # Track tokens using vision pricing coefficient
    in_tokens = response.usage.prompt_tokens
    out_tokens = response.usage.completion_tokens
    tracker.track("vision", in_tokens, out_tokens)

    # Determine status
    accepted = critique.startswith("STATUS: ACCEPTED")
    return accepted, critique
