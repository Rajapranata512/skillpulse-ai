import pandas as pd

from skillpulse.extraction import EntityExtractor
from skillpulse.extraction.evaluation import (
    evaluate_ai_assisted_annotations,
    evaluate_gold_annotations,
)


def _annotation_row(status: str, source_row: str = "1") -> dict[str, str]:
    return {
        "source_row": source_row,
        "text": "Bachelor degree, 3 years experience, Excel, placement across Java Indonesia.",
        "gold_technical_skills": "",
        "gold_tools": "Excel",
        "gold_soft_skills": "",
        "gold_education": "Bachelor",
        "gold_experience_years": "3",
        "gold_seniority": "unknown",
        "gold_work_arrangement": "unknown",
        "review_status": status,
    }


def test_ai_assisted_report_is_separate_from_human_gold() -> None:
    frame = pd.DataFrame(
        [
            _annotation_row("ai_reviewed"),
            {
                **_annotation_row("reviewed", "2"),
                "text": "Python",
                "gold_technical_skills": "Python",
                "gold_tools": "",
                "gold_education": "",
                "gold_experience_years": "",
            },
        ]
    )

    report = evaluate_ai_assisted_annotations(frame, EntityExtractor())

    assert report["documents_evaluated"] == 1
    assert report["claim_status"] == "not_human_gold"
    assert report["review_status_included"] == "ai_reviewed"


def test_provisional_error_analysis_reflects_contextual_guards() -> None:
    frame = pd.DataFrame([_annotation_row("ai_reviewed")])

    report = evaluate_ai_assisted_annotations(frame, EntityExtractor())
    technical_errors = report["error_analysis"]["entity_errors"]["technical_skills"]
    seniority_errors = report["error_analysis"]["scalar_errors"]["seniority"]

    assert technical_errors["false_positives"] == []
    assert seniority_errors["mismatches"] == 0


def test_human_gold_evaluation_ignores_ai_reviewed_rows() -> None:
    report = evaluate_gold_annotations(pd.DataFrame([_annotation_row("ai_reviewed")]), EntityExtractor())

    assert report["documents_reviewed"] == 0


def test_experience_evaluation_normalizes_csv_float_values() -> None:
    row = _annotation_row("reviewed")
    row["gold_experience_years"] = 3.0  # type: ignore[assignment]

    report = evaluate_gold_annotations(pd.DataFrame([row]), EntityExtractor())

    assert report["metrics"]["experience_years"]["exact_match"] == 1.0
