# STAGE 0: SEMANTIC GAP ANALYZER

## Purpose
Run a pre-flight text analysis before compiling any layouts. It establishes the baseline semantic match and creates the structural plan for downstream modifications.

## Detailed Flow & Logic
- Compares the raw `user_profile.md` (comprehensive background) against the `job_description.txt` (target requirements).
- Calls a low-cost text model (e.g. `gpt-4o-mini`) requesting a strictly formatted JSON output.
- Identifies missing target keywords, domain terminology, and skills that need to be injected.
- Calculates an initial "closeness score" representing ATS alignment.

## Output Schema
The response must follow this schema exactly:
```json
{
  "closeness_score": 75,
  "matching_strengths": ["list", "of", "skills"],
  "critical_gaps": ["technologies", "missing"],
  "target_keywords": ["keywords", "to", "inject"]
}
```

## Downstream Application
The resulting report is packaged directly into the system prompt for **Stage 1 (Semantic Text Generator)** to inform whether content must be added (to cover gaps) or pruned (prioritizing matching strengths).
