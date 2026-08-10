import sys
from pathlib import Path

import pandas as pd
import pytest

from skillpulse.extraction.cli import main
from skillpulse.extraction.review_batch import (
    append_audit_log,
    create_review_batch,
    import_human_review_batch,
    write_csv_atomic,
)


def _annotation(source_row: str = "7", status: str = "needs_review") -> dict[str, str]:
    return {
        "source_row": source_row,
        "text": "Need Python, SQL, Tableau, communication, S1, and 2 years. Hybrid.",
        "gold_technical_skills": "",
        "gold_tools": "",
        "gold_soft_skills": "",
        "gold_education": "",
        "gold_experience_years": "",
        "gold_seniority": "",
        "gold_work_arrangement": "",
        "review_status": status,
        "annotator": "",
        "notes": "",
    }


def test_review_batch_separates_prefilled_decisions_from_suggestions() -> None:
    batch = create_review_batch(pd.DataFrame([_annotation(), _annotation("8", "reviewed")]))

    assert len(batch) == 1
    assert batch.loc[0, "gold_technical_skills"] == "Python|SQL"
    assert batch.loc[0, "suggested_technical_skills"] == "Python|SQL"
    assert batch.loc[0, "gold_tools"] == "Tableau"
    assert batch.loc[0, "gold_seniority"] == "unknown"
    assert batch.loc[0, "review_status"] == "needs_review"
    assert len(batch.loc[0, "text_sha256"]) == 64


def test_review_import_only_applies_explicitly_reviewed_rows() -> None:
    annotations = pd.DataFrame([_annotation(), _annotation("8")])
    batch = create_review_batch(annotations)
    batch.loc[0, "review_status"] = "reviewed"
    batch.loc[0, "annotator"] = "human_02"
    batch.loc[0, "notes"] = "Checked complete text; suggestions accepted."
    batch.loc[0, "gold_soft_skills"] = ""

    result = import_human_review_batch(
        annotations,
        batch,
        human_review_confirmed=True,
        reviewed_at="2026-08-10",
    )

    reviewed = result.annotations[result.annotations["source_row"].eq("7")].iloc[0]
    pending = result.annotations[result.annotations["source_row"].eq("8")].iloc[0]
    assert result.rows_applied == 1
    assert reviewed["review_status"] == "reviewed"
    assert reviewed["annotator"] == "human_02"
    assert reviewed["gold_soft_skills"] == ""
    assert pending["review_status"] == "needs_review"
    assert result.quality_report["valid"] is True
    assert result.audit_log.loc[0, "prior_status"] == "needs_review"


def test_review_import_requires_explicit_human_confirmation() -> None:
    annotations = pd.DataFrame([_annotation()])
    batch = create_review_batch(annotations)

    with pytest.raises(ValueError, match="Human review confirmation"):
        import_human_review_batch(annotations, batch)


@pytest.mark.parametrize("mutation", ["text", "text_sha256"])
def test_review_import_rejects_source_identity_changes(mutation: str) -> None:
    annotations = pd.DataFrame([_annotation()])
    batch = create_review_batch(annotations)
    batch.loc[0, mutation] = "changed"

    with pytest.raises(ValueError, match="Source text or fingerprint changed"):
        import_human_review_batch(annotations, batch, human_review_confirmed=True)


def test_review_import_rejects_invalid_labels_and_missing_notes() -> None:
    annotations = pd.DataFrame([_annotation()])
    batch = create_review_batch(annotations)
    batch.loc[0, "review_status"] = "reviewed"
    batch.loc[0, "annotator"] = "human_02"

    with pytest.raises(ValueError, match="Review notes are required"):
        import_human_review_batch(annotations, batch, human_review_confirmed=True)

    batch.loc[0, "notes"] = "Checked."
    batch.loc[0, "gold_technical_skills"] = "Imaginary Skill"
    with pytest.raises(ValueError, match="unknown_gold_technical_skills"):
        import_human_review_batch(annotations, batch, human_review_confirmed=True)


def test_csv_writes_and_audit_append_are_atomic(tmp_path: Path) -> None:
    annotations = pd.DataFrame([_annotation()])
    batch = create_review_batch(annotations)
    batch.loc[0, "review_status"] = "reviewed"
    batch.loc[0, "annotator"] = "human_02"
    batch.loc[0, "notes"] = "Checked."
    result = import_human_review_batch(
        annotations, batch, human_review_confirmed=True, reviewed_at="2026-08-10"
    )
    annotation_path = tmp_path / "annotations.csv"
    audit_path = tmp_path / "audit.csv"

    write_csv_atomic(result.annotations, annotation_path)
    append_audit_log(audit_path, result.audit_log)
    append_audit_log(audit_path, result.audit_log)

    assert len(pd.read_csv(annotation_path)) == 1
    assert len(pd.read_csv(audit_path)) == 2
    assert not (tmp_path / "annotations.csv.tmp").exists()

def test_review_batch_cli_exports_pending_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    annotation_path = tmp_path / "annotations.csv"
    output_path = tmp_path / "review.csv"
    pd.DataFrame([_annotation(), _annotation("8", "reviewed")]).to_csv(
        annotation_path, index=False
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "skillpulse-extract",
            "review-batch",
            "--annotations",
            str(annotation_path),
            "--output",
            str(output_path),
        ],
    )

    main()

    assert len(pd.read_csv(output_path)) == 1
    assert '"rows_included": 1' in capsys.readouterr().out


def test_review_import_cli_writes_validated_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    annotation_path = tmp_path / "annotations.csv"
    batch_path = tmp_path / "review.csv"
    output_path = tmp_path / "reviewed.csv"
    audit_path = tmp_path / "audit.csv"
    annotations = pd.DataFrame([_annotation()])
    annotations.to_csv(annotation_path, index=False)
    batch = create_review_batch(annotations)
    batch.loc[0, "review_status"] = "reviewed"
    batch.loc[0, "annotator"] = "human_02"
    batch.loc[0, "notes"] = "Checked complete text."
    batch.to_csv(batch_path, index=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "skillpulse-extract",
            "review-import",
            "--annotations",
            str(annotation_path),
            "--batch",
            str(batch_path),
            "--output",
            str(output_path),
            "--audit-log",
            str(audit_path),
            "--confirm-human-review",
        ],
    )

    main()

    assert pd.read_csv(output_path).loc[0, "review_status"] == "reviewed"
    assert len(pd.read_csv(audit_path)) == 1
    assert '"rows_applied": 1' in capsys.readouterr().out
