import os
from PIL import Image
import google.generativeai as genai
from utils.config import VISION_MODEL
from utils.context import PipelineContext
from utils.helpers import get_api_key, track_tokens

def run_stage3(png_image_path: str, tracker: PipelineContext) -> tuple[bool, str]:
    """
    Stage 3: Vision Feedback Loop & Inspector
    Evaluates the visual layouts, margins, and space utilisation of the compiled resume.
    Identifies empty voids at the bottom (EMPTY_BOTTOM) or visual overflows (OVERFLOW).
    
    Returns: (accepted_status, critique_message)
    """
    if not os.path.exists(png_image_path):
        return False, "STATUS: FILE_ERROR\nCRITIQUE: PNG rasterized resume was not found."

    api_key = get_api_key()
    genai.configure(api_key=api_key)

    # Load image using PIL
    try:
        pil_image = Image.open(png_image_path)
    except Exception as e:
        return False, f"STATUS: FILE_ERROR\nCRITIQUE: Failed to open image: {str(e)}"

    system_prompt = (
        "You are an expert design QA inspector evaluating the layout balance of a compiled resume.\n"
        "Analyze the provided image of the resume and evaluate its spacing, margins, and white space utilization.\n\n"
        "EVALUATION CRITERIA:\n"
        "1. PAGE BALANCE: Verify if the content fills the page grid elegantly. There should be uniform top/bottom margins.\n"
        "2. EMPTY BOTTOM GAP (Underutilization): If there is a massive empty space at the bottom (more than 1.5 inches of "
        "empty white background at the bottom of the page), return status EMPTY_BOTTOM and ask the system to expand descriptions "
        "or add more relevant projects/details from the profile to balance the page.\n"
        "3. OVERFLOW & CLIPPING: If the text is clipping, overlapping, or looks overly crowded and spills onto subsequent margins, "
        "return status OVERFLOW and request text compression.\n"
        "4. SKILLS SECTION CHECK: Look closely at the SKILLS block. Every skill category MUST perfectly fit on 1 single line. If any skill category wraps to a second line, return status OVERFLOW and explicitly request the text generator to remove the least relevant skill from that list.\n"
        "5. BULLET POINT ORPHAN CHECK: Look closely at every bullet point. Bullet points MUST either fit entirely on 1 full line, or if they wrap to a second line, the second line MUST be at least half full (1.5+ lines total) but STRICTLY less than 2 full lines. If a bullet point leaves a single dangling word or just a few words on a new line (an orphan), return status OVERFLOW and instruct the system to shorten it.\n"
        "6. ACCEPTED: If the spacing looks clean, professional, and visually balanced on exactly one page, and adheres to all the strict line-wrapping rules above, return status ACCEPTED.\n\n"
        "You MUST respond starting with one of these exact headers:\n"
        "- STATUS: ACCEPTED\n"
        "- STATUS: EMPTY_BOTTOM\n"
        "- STATUS: OVERFLOW\n\n"
        "Followed by a detailed visual critique explaining your assessment."
    )

    # Call Gemini Vision Model
    model = genai.GenerativeModel(
        model_name=VISION_MODEL,
        system_instruction=system_prompt
    )

    response = model.generate_content(
        [pil_image, "Perform the resume visual layout analysis."],
        generation_config={"temperature": 0.0}
    )

    critique = response.text.strip()

    # Track tokens using vision pricing coefficient
    track_tokens(response, tracker, model_type="vision")

    # Determine status
    accepted = critique.startswith("STATUS: ACCEPTED")
    return accepted, critique
