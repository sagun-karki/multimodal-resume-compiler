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
        
        full_png_path = png_output_path.replace(".png", "_full.png")
        
        if page_count == 1:
            pix = doc[0].get_pixmap(matrix=mat)
            pix.save(full_png_path)
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
            pix.save(full_png_path)
            tall_doc.close()
            
        # Crop the saved image to content and save to png_output_path
        from PIL import Image, ImageChops
        with Image.open(full_png_path) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            diff = ImageChops.difference(img.convert("RGB"), bg)
            bbox = diff.getbbox()
            if bbox:
                # Add 20px padding to avoid clipping fonts/accents
                padding = 20
                left = max(0, bbox[0] - padding)
                top = max(0, bbox[1] - padding)
                right = min(img.width, bbox[2] + padding)
                bottom = min(img.height, bbox[3] + padding)
                cropped_img = img.crop((left, top, right, bottom))
                cropped_img.save(png_output_path)
            else:
                img.save(png_output_path)
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
