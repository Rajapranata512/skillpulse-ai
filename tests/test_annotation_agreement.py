import pandas as pd
import pytest

from skillpulse.extraction.agreement import (
    cohen_kappa,
    create_blind_second_annotation_batch,
    evaluate_annotation_agreement,
)


def _primary_row(source_row: str, text: str, technical: str, seniority: str) -> dict[str, str]:
    return {
        "source_row": source_row,
        "text": text,
        "gold_technical_skills": technical,
        "gold_tools": "",
        "gold_soft_skills": "Communication",
        "gold_education": "Bachelor",
        "gold_experience_years": "2",
        "gold_seniority": seniority,
        "gold_work_arrangement": "hybrid",
        "review_status": "reviewed",
        "annotator": "primary_human",
        "notes": "Primary review complete.",
    }


def _primary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _primary_row("1", "Python role, S1, 2 years, communication, hybrid.", "Python", "entry"),
            _primary_row("2", "SQL role, S1, 2 years, communication, hybrid.", "SQL", "mid"),
        ]
    )


def _completed_secondary() -> tuple[pd.DataFrame, pd.DataFrame]:
    primary = _primary()
    secondary = create_blind_second_annotation_batch(primary)
    for column in (
        "gold_technical_skills",
        "gold_tools",
        "gold_soft_skills",
        "gold_education",
        "gold_experience_years",
        "gold_seniority",
        "gold_work_arrangement",
    ):
        secondary[column] = primary[column]
    secondary["review_status"] = "reviewed"
    secondary["annotator"] = "independent_human"
    secondary["notes"] = "Blind review complete."
    return primary, secondary


def test_blind_batch_removes_primary_labels_and_model_hints() -> None:
    batch = create_blind_second_annotation_batch(_primary())

    assert len(batch) == 2
    assert batch["gold_technical_skills"].eq("").all()
    assert batch["gold_seniority"].eq("").all()
    assert batch["review_status"].eq("needs_review").all()
    assert not any(column.startswith("suggested_") for column in batch.columns)
    assert "weak_tools" not in batch.columns
    assert batch["text_sha256"].str.len().eq(64).all()


def test_perfect_independent_agreement_is_ready() -> None:
    primary, secondary = _completed_secondary()

    report = evaluate_annotation_agreement(primary, secondary, minimum_documents=2)

    assert report["ready_for_ml_qg_2"] is True
    assert report["documents_compared"] == 2
    assert report["metrics"]["technical_skills"]["document_exact_match"] == 1.0
    assert report["metrics"]["technical_skills"]["macro_label_cohen_kappa"] == 1.0
    assert report["metrics"]["seniority"]["cohen_kappa"] == 1.0


def test_disagreement_is_visible_and_same_annotator_is_not_independent() -> None:
    primary, secondary = _completed_secondary()
    secondary.loc[0, "gold_technical_skills"] = "SQL"
    secondary["annotator"] = "primary_human"

    report = evaluate_annotation_agreement(primary, secondary, minimum_documents=2)

    assert report["ready_for_ml_qg_2"] is False
    assert report["metrics"]["technical_skills"]["document_exact_match"] == 0.5
    assert report["annotators_are_independent"] is False


def test_pending_rows_do_not_count_toward_agreement() -> None:
    primary, secondary = _completed_secondary()
    secondary.loc[1, "review_status"] = "needs_review"

    report = evaluate_annotation_agreement(primary, secondary, minimum_documents=2)

    assert report["documents_compared"] == 1
    assert report["ready_for_ml_qg_2"] is False


def test_empty_secondary_progress_does_not_show_perfect_agreement() -> None:
    primary = _primary()
    secondary = create_blind_second_annotation_batch(primary)

    report = evaluate_annotation_agreement(primary, secondary, minimum_documents=2)

    assert report["documents_compared"] == 0
    assert report["secondary_notes_complete"] is False
    assert report["metrics"]["technical_skills"]["micro_jaccard"] is None


def test_agreement_rejects_changed_source_identity() -> None:
    primary, secondary = _completed_secondary()
    secondary.loc[0, "text"] = "Changed text"

    with pytest.raises(ValueError, match="Source text or fingerprint changed"):
        evaluate_annotation_agreement(primary, secondary, minimum_documents=2)


def test_cohen_kappa_rejects_different_lengths_and_handles_no_variance() -> None:
    with pytest.raises(ValueError, match="equal length"):
        cohen_kappa(["a"], ["a", "b"])

    assert cohen_kappa(["a", "a"], ["a", "a"]) is None
