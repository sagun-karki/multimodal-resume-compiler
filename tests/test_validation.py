import pytest
from utils.validation import validate_gap_report, validate_resume_json


def test_validate_gap_report_requires_fields():
    with pytest.raises(ValueError):
        validate_gap_report({"closeness_score": 80})


def test_validate_resume_json_requires_fields():
    with pytest.raises(ValueError):
        validate_resume_json({"skills": {}})
