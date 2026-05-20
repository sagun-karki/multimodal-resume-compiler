# PDF RASTERIZER & PAGE ROUTER (`stages/stage2_pdf_manager.py`)

## Purpose
Inspects physical pages, rasterizes the PDF output to high-resolution PNGs for display/audit, and executes programmatic routing optimization.

## Verification Logic
1. **Page Count Overflow Guard:**
   - Opens `output/resume.pdf` using PyMuPDF (`fitz`).
   - If the page count is greater than 1, it immediately stops and yields an `OVERFLOW` status with a shortening request. 
   - **Token Optimizer**: By checking the physical page count programmatically first, it avoids invoking the expensive Multimodal Vision model on obviously broken drafts, conserving API tokens.
2. **Page Conversion for Vision Auditing:**
   - If the page count is exactly 1, PyMuPDF renders page 0 to high-resolution PNG bytes (at 150 DPI) and saves it to `output/resume.png` (and `output/resume_full.png` for vision audits).
   - The rasterized image is then sent directly to the `VisualAuditorAgent` for visual layout inspection.
