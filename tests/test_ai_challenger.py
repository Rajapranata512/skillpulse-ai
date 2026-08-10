from pathlib import Path

import openpyxl
import pandas as pd

from skillpulse.extraction.ai_challenger import (
    evaluate_ai_challenger_agreement,
    read_annotation_workbook,
    repair_ai_annotations,
    write_repaired_workbook,
)
from skillpulse.extraction.review_batch import _text_sha256


def _primary_row(source_row: str, text: str, technical: str) -> dict[str, str]:
    return {
        "source_row": source_row,
        "text": text,
        "gold_technical_skills": technical,
        "gold_tools": "Excel",
        "gold_soft_skills": "Communication",
        "gold_education": "Bachelor",
        "gold_experience_years": "2",
        "gold_seniority": "mid",
        "gold_work_arrangement": "hybrid",
        "review_status": "reviewed",
        "annotator": "primary_human",
        "notes": "Primary review complete.",
    }


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    primary = pd.DataFrame(
        [
            _primary_row("1", "Python, Excel, communication, S1, 2 years, hybrid.", "Python"),
            _primary_row("2", "SQL, Excel, communication, S1, 2 years, hybrid.", "SQL"),
        ]
    )
    ai_rows = []
    for _, row in primary.iterrows():
        ai_rows.append(
            {
                "source_row": row["source_row"],
                "text": f"AI reformatted: {row['text']}",
                "text_sha256": _text_sha256(row["text"]),
                "gold_technical_skills": f"{row['gold_technical_skills']}|Requirements Analysis",
                "gold_tools": "Microsoft Excel|SAP",
                "gold_soft_skills": "communication|Adaptability",
                "gold_education": "Bachelor",
                "gold_experience_years": "2.0",
                "gold_seniority": "mid",
                "gold_work_arrangement": "hybrid",
                "review_status": "reviewed",
                "annotator": "chatgpt_ai_annotator_01",
                "notes": "AI checked.",
            }
        )
    return primary, pd.DataFrame(ai_rows)


def test_repair_restores_source_canonicalizes_and_drops_unknown_labels() -> None:
    primary, ai = _frames()

    result = repair_ai_annotations(ai, primary)

    assert result.annotations["text"].tolist() == primary["text"].tolist()
    assert result.annotations["text_sha256"].tolist() == [
        _text_sha256(text) for text in primary["text"]
    ]
    assert result.annotations["gold_tools"].eq("Excel").all()
    assert result.annotations["gold_soft_skills"].eq("Communication").all()
    assert result.annotations["review_status"].eq("ai_reviewed").all()
    assert result.report["field_summary"]["gold_technical_skills"]["dropped_labels"] == 2
    assert result.report["annotation_quality"]["valid"] is True


def test_ai_comparison_never_satisfies_human_agreement_gate() -> None:
    primary, ai = _frames()
    repaired = repair_ai_annotations(ai, primary).annotations

    report = evaluate_ai_challenger_agreement(primary, repaired)

    assert report["documents_compared"] == 2
    assert report["ready_for_ml_qg_2"] is False
    assert report["annotators_are_independent"] is False
    assert report["claim_status"] == "descriptive_only_not_human_agreement"


def test_repaired_workbook_is_readable_and_explicitly_ai_only(tmp_path: Path) -> None:
    primary, ai = _frames()
    result = repair_ai_annotations(ai, primary)
    output = tmp_path / "fixed.xlsx"

    write_repaired_workbook(result.annotations, result.report, output)
    workbook = openpyxl.load_workbook(output, read_only=True)
    loaded = read_annotation_workbook(output, "AI_Challenger_Annotations")

    assert workbook.sheetnames == [
        "AI_Challenger_Annotations",
        "Transformation_QA",
        "Dropped_Labels",
        "README",
    ]
    assert len(loaded) == 2
    assert loaded["review_status"].eq("ai_reviewed").all()
