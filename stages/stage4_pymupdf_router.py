import os
import fitz  # PyMuPDF

def run_stage4(pdf_path: str, png_output_path: str) -> tuple[bool, str]:
    """
    Stage 4: PyMuPDF Page-Count Router & Rasterizer
    Validates page boundaries and exports a high-fidelity PNG of page 1 for visual review.
    
    Returns: (success_status, critique_message)
    """
    if not os.path.exists(pdf_path):
        return False, "STATUS: FILE_ERROR\nCRITIQUE: PDF resume file was not generated."

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return False, f"STATUS: FILE_ERROR\nCRITIQUE: Failed to open PDF file: {str(e)}"

    page_count = doc.page_count
    
    # Strictly enforce 1-page resume requirement
    if page_count != 1:
        doc.close()
        return False, (
            f"STATUS: OVERFLOW\n"
            f"CRITIQUE: Page count boundary violation! The generated resume is {page_count} pages long, "
            f"violating the strict single-page (1 page) layout constraint. The text generator must reduce "
            f"content length or bullet descriptions to fit the single-page layout."
        )

    # Rasterize page 1 into a high-resolution PNG (using zoom factor 2 for sharpness)
    try:
        page = doc[0]
        zoom = 2.0  # scale factor
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Ensure output folder exists
        os.makedirs(os.path.dirname(png_output_path), exist_ok=True)
        pix.save(png_output_path)
    except Exception as e:
        doc.close()
        return False, f"STATUS: RASTERIZE_ERROR\nCRITIQUE: Failed to rasterize PDF page: {str(e)}"

    doc.close()
    return True, ""
