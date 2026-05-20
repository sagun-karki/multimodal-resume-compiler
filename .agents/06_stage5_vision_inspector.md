# VISUAL AUDITOR AGENT (`agents/visual_auditor.py`)

## Purpose
Examine compiled resume page images using Multimodal Vision models to review bottom spacing margins, grid alignment, section padding, and balance.

## Audit Workflow
- Loads the rasterized resume page PNG image (`output/resume_full.png`).
- Sends the image to the Gemini vision model with a custom audit prompt.
- Instructs the model to return a structured visual review of the layout:
  - Is the bottom margin too empty? (Less than 0.5 inches of text from the page bottom is fine, but more than 1.5 inches of blank whitespace triggers a correction).
  - Are there overlapping text strings or section breaks?
  - Are there orphan headings?

## Feedback Outputs
- **`STATUS: ACCEPTED`**: The layout is visually balanced and fits the single-page expectation.
- **`STATUS: OVERFLOW`**: Page layout overflows boundaries. Triggers compression.
- **`STATUS: EMPTY_BOTTOM`**: Excessive blank whitespace at the bottom. Triggers expansion.
- **`STATUS: REJECTED`**: Layout issues detected. Triggers corrections.
- The returned textual critique is passed back to the `CoordinatorAgent` to guide the writer in the next loop iteration.
