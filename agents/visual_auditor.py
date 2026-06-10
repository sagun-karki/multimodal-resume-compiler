import os
from PIL import Image
from agents.base import BaseAgent
from utils.config import VISION_MODEL
from utils.context import PipelineContext

class VisualAuditorAgent(BaseAgent):
    def __init__(self, tracker: PipelineContext):
        system_instruction = (
            "You are an expert QA design inspector evaluating specialized cropped region-of-interest (ROI) frame segments of a typeset resume.\n\n"
            "INPUT CONFIGURATIONS:\n"
            "You will be provided with two targeted cropped image slices extracted from the rendered single-page layout document matrix:\n"
            "1. [BOTTOM_MARGIN_ROI]: A focused cut-out slice capturing precisely the bottom 2.5 inches of the page area background workspace boundary.\n"
            "2. [SKILLS_SECTION_ROI]: A focused close-up capture block bounding exclusively the SKILLS lists segments.\n\n"
            "CRITICAL REASONING & AUDIT RULES:\n"
            "- Analyze [BOTTOM_MARGIN_ROI] closely. Measure the ratio of white background pixels versus text ink density at the very bottom boundary. If there is a massive unutilized white patch trailing the final item block spanning deeper than 1.5 inches of blank whitespace, you MUST output status: EMPTY_BOTTOM.\n"
            "- Analyze [SKILLS_SECTION_ROI] closely. Inspect the physical right-hand margin boundaries. If any row of technical credentials features text wrapping to a second indented line row, you MUST immediately pinpoint the violating category header and output status: OVERFLOW.\n\n"
            "OUTPUT SPECIFICATIONS:\n"
            "You must strictly format the evaluation output block starting with one of these exact tokens headers:\n"
            "- STATUS: ACCEPTED\n"
            "- STATUS: EMPTY_BOTTOM\n"
            "- STATUS: OVERFLOW\n\n"
            "Followed by a detailed visual critique explaining your assessment of the cropped images."
        )
        super().__init__(
            name="Visual Auditor Agent",
            system_instruction=system_instruction,
            model_name=VISION_MODEL,
            tracker=tracker
        )

    def audit(self, png_image_path: str) -> tuple[bool, str]:
        if not os.path.exists(png_image_path):
            return False, "STATUS: FILE_ERROR\nCRITIQUE: PNG rasterized resume was not found."

        try:
            img = Image.open(png_image_path)
            W, H = img.size
            
            # Crop 1: BOTTOM_MARGIN_ROI (capturing bottom 2.5 inches of typeset page; basic approximation via bottom 25% height)
            bottom_crop_path = png_image_path.replace(".png", "_bottom_roi.png")
            bottom_crop = img.crop((0, int(H * 0.75), W, H))
            bottom_crop.save(bottom_crop_path)
            
            # Crop 2: SKILLS_SECTION_ROI (capturing top skills list segments close-up; approx. 12% to 45% height)
            skills_crop_path = png_image_path.replace(".png", "_skills_roi.png")
            skills_crop = img.crop((0, int(H * 0.12), W, int(H * 0.45)))
            skills_crop.save(skills_crop_path)
            
            bottom_roi_img = Image.open(bottom_crop_path)
            skills_roi_img = Image.open(skills_crop_path)
        except Exception as e:
            return False, f"STATUS: FILE_ERROR\nCRITIQUE: Failed to load cropped ROI images: {str(e)}"

        prompt_message = (
            "Analyze these two cropped ROI images from the Typeset Resume:\n"
            "1. [BOTTOM_MARGIN_ROI] captures the bottom page space layout.\n"
            "2. [SKILLS_SECTION_ROI] captures the technical skills block close-up."
        )

        critique = self.generate_response(
            [bottom_roi_img, skills_roi_img, prompt_message],
            generation_config={"temperature": 0.0},
            model_type="vision"
        )
        
        # Clean up ROI crop files to prevent disk clutter
        for temp_path in (bottom_crop_path, skills_crop_path):
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        accepted = critique.startswith("STATUS: ACCEPTED")
        return accepted, critique
