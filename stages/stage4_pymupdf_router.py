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
    
    # Rasterize to PNG FIRST, so UI can display overflows
    try:
        os.makedirs(os.path.dirname(png_output_path), exist_ok=True)
        zoom = 2.0  # scale factor
        mat = fitz.Matrix(zoom, zoom)
        
        if page_count == 1:
            pix = doc[0].get_pixmap(matrix=mat)
            pix.save(png_output_path)
        else:
            # Multi-page stitch: Create a tall virtual page and draw all pages onto it
            rect = doc[0].rect
            tall_doc = fitz.open()
            tall_page = tall_doc.new_page(width=rect.width, height=rect.height * page_count)
            
            y_offset = 0
            for i in range(page_count):
                target_rect = fitz.Rect(0, y_offset, rect.width, y_offset + rect.height)
                tall_page.show_pdf_page(target_rect, doc, i)
                y_offset += rect.height
                
            pix = tall_page.get_pixmap(matrix=mat)
            pix.save(png_output_path)
            tall_doc.close()
    except Exception as e:
        doc.close()
        return False, f"STATUS: RASTERIZE_ERROR\nCRITIQUE: Failed to rasterize PDF page: {str(e)}"

    # Strictly enforce 1-page resume requirement AFTER generating the image
    if page_count != 1:
        doc.close()
        return False, (
            f"STATUS: OVERFLOW\n"
            f"CRITIQUE: Page count boundary violation! The generated resume is {page_count} pages long, "
            f"violating the strict single-page (1 page) layout constraint. The text generator must reduce "
            f"content length or bullet descriptions to fit the single-page layout."
        )

    doc.close()
    return True, ""
