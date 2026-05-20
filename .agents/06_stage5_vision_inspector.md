# STAGE 5: VISION GRID INSPECTOR

## Purpose
Perform a multimodal layout assessment to evaluate macro vertical margins, grid alignments, and density balances.

## Implementation
- Load the rasterized PNG bytes from Stage 4.
- Send the PNG to a Multimodal Vision model (e.g. `gpt-4o`).
- Prompt the model to evaluate bottom spacing, margin boundaries, and sections for visual aesthetics.

## Strict Status Returns
Enforce a clear status outcome to drive the state machine:
- `STATUS: PERFECT`
  The layout looks balanced. Text margins are professional, and content naturally reaches within 0.5 to 1.25 inches of the bottom page line.
- `STATUS: EMPTY_BOTTOM`
  The content is too sparse, leaving an empty white void greater than 1.5 inches at the bottom of the page.
- `STATUS: OVERFLOW`
  (Usually pre-empted by Stage 4, but used here to catch visual text collisions or overlapping section lines).
