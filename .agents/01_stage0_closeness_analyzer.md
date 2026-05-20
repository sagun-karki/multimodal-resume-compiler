# ATS ANALYZER AGENT (`agents/ats_analyzer.py`)

## Purpose
Run pre-flight text analysis to establish baseline semantic match alignment, identify missing keywords, and produce a gaps report to target.

## Implementation Details
- Declares the `ATSAnalyzerAgent` class inheriting from `BaseAgent`.
- Compares the `user_profile.md` (comprehensive background) against the `job_description.txt` (target requirements).
- Leverages the Gemini text model with custom system prompts instructing it to yield a structured JSON analysis.
- Extracts target keywords, matching strengths, critical gaps, and computes a baseline "closeness score" (from 0% to 100%).

## Output Schema
The response matches this schema:
```json
{
  "closeness_score": 75,
  "matching_strengths": ["list", "of", "skills"],
  "critical_gaps": ["technologies", "missing"],
  "target_keywords": ["keywords", "to", "inject"],
  "sections_analysis": {
    "section_name": {
      "recommendation": "recommendation text",
      "add": ["items", "to", "add"],
      "remove": ["items", "to", "remove"],
      "update": ["items", "to", "update"]
    }
  }
}
```

## Downstream Application
The resulting report is parsed by the `CoordinatorAgent` and loaded into the `ResumeWriterAgent` prompt context, which weaves the keyword recommendations directly into tailored resume sections.
