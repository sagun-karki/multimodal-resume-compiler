# STAGE 4: PYMUPDF ROUTER

## Purpose
Inspect physical vertical constraints of the compiled PDF and execute routing decisions to optimize token consumption.

## Logic Flow
1. Load `output/resume.pdf` using PyMuPDF (`fitz`).
2. Verify total page count (`len(doc)`):
   - **Case A: `len(doc) > 1` (Overflow Detected)**
     If the document spills onto page 2, it violates the static 1-page layout rule. Set status immediately to `OVERFLOW`. Bypasses Stage 5 (Vision model) entirely to avoid wasting API tokens on a known layout failure. The critique is routed immediately back to Stage 1.
   - **Case B: `len(doc) == 1` (Fits on Single Page)**
     Render/Rasterize page 0 to PNG bytes at 150 DPI resolution:
     ```python
     pix = page.get_pixmap(dpi=150)
     png_bytes = pix.tobytes("png")
     ```
     Forward the PNG image data to **Stage 5 (Vision Grid Inspector)** for visual padding analysis.
