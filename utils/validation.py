from typing import Any


def validate_gap_report(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Gap report must be a JSON object")
    required = ["closeness_score", "matching_strengths", "critical_gaps", "target_keywords", "sections_analysis"]
    for key in required:
        if key not in data:
            raise ValueError(f"Gap report missing required field: {key}")
    return data


def validate_resume_json(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Resume payload must be a JSON object")
    required = ["skills", "experience", "projects", "education", "honors"]
    for key in required:
        if key not in data:
            raise ValueError(f"Resume payload missing required field: {key}")
    return data
