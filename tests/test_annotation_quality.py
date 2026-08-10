import pandas as pd

from skillpulse.extraction.annotation_quality import validate_annotation_frame


def _valid_row() -> dict[str, str]:
    return {
        "source_row": "1",
        "text": "Need Python, S1, and hybrid work.",
        "gold_technical_skills": "Python",
        "gold_tools": "",
        "gold_soft_skills": "",
        "gold_education": "Bachelor",
        "gold_experience_years": "",
        "gold_seniority": "unknown",
        "gold_work_arrangement": "hybrid",
        "review_status": "ai_reviewed",
        "annotator": "test_ai",
        "notes": "Checked.",
    }


def test_annotation_quality_accepts_canonical_ai_reviewed_row() -> None:
    report = validate_annotation_frame(pd.DataFrame([_valid_row()]))

    assert report["valid"] is True
    assert report["ready_for_provisional_evaluation"] is True
    assert report["ready_for_human_gold_evaluation"] is False


def test_annotation_quality_rejects_duplicate_and_unknown_labels() -> None:
    first = _valid_row()
    second = {**_valid_row(), "gold_technical_skills": "Imaginary Skill"}

    report = validate_annotation_frame(pd.DataFrame([first, second]))
    codes = {issue["code"] for issue in report["issues"]}

    assert report["valid"] is False
    assert "duplicate_source_row" in codes
    assert "unknown_gold_technical_skills" in codes
