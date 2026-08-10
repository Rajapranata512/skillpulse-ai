import pandas as pd
import pytest

from skillpulse.matching.relevance import (
    create_ai_relevance_labels,
    create_relevance_candidate_set,
    evaluate_ai_relevance_baseline,
    evaluate_relevance_baseline,
)


def _reviewed_candidates() -> pd.DataFrame:
    frame = create_relevance_candidate_set()
    frame["human_relevance_score"] = [str(index % 5) for index in range(len(frame))]
    frame["human_rationale"] = "Compared every explicit requirement using rubric v0.1."
    frame["review_status"] = "reviewed"
    frame["annotator"] = "human_relevance_01"
    frame["notes"] = "Synthetic pair reviewed."
    return frame


def test_candidate_set_is_public_safe_unlabeled_and_balanced_by_job() -> None:
    frame = create_relevance_candidate_set()

    assert len(frame) == 50
    assert frame["pair_id"].nunique() == 50
    assert frame["job_group_id"].nunique() == 10
    assert frame.groupby("job_group_id").size().eq(5).all()
    assert frame["human_relevance_score"].eq("").all()
    assert frame["review_status"].eq("needs_review").all()
    assert frame["cv_sha256"].str.len().eq(64).all()
    assert frame["job_sha256"].str.len().eq(64).all()


def test_reviewed_candidates_produce_baseline_metrics_but_not_ml_qg_3() -> None:
    report = evaluate_relevance_baseline(_reviewed_candidates())

    assert report["pairs_reviewed"] == 50
    assert report["job_groups_reviewed"] == 10
    assert report["ready_for_baseline_evaluation"] is True
    assert report["ready_for_ml_qg_3"] is False
    assert report["metrics"]["latency_ms_p50"] is not None
    assert report["metrics"]["explanation_completeness"] == 1.0


def test_pending_candidates_do_not_count_as_human_evidence() -> None:
    report = evaluate_relevance_baseline(create_relevance_candidate_set())

    assert report["pairs_reviewed"] == 0
    assert report["ready_for_baseline_evaluation"] is False
    assert report["metrics"]["spearman_global"] is None


def test_relevance_evaluation_rejects_tampering_and_invalid_scores() -> None:
    tampered = _reviewed_candidates()
    tampered.loc[0, "cv_text"] = "Changed CV"
    with pytest.raises(ValueError, match="CV text fingerprint changed"):
        evaluate_relevance_baseline(tampered)

    invalid = _reviewed_candidates()
    invalid.loc[0, "human_relevance_score"] = "5"
    with pytest.raises(ValueError, match="integer 0-4"):
        evaluate_relevance_baseline(invalid)

def test_ai_labels_are_separate_complete_and_not_human_evidence() -> None:
    candidates = create_relevance_candidate_set()
    labels = create_ai_relevance_labels()

    assert len(labels) == 50
    assert labels["pair_id"].nunique() == 50
    assert labels["review_status"].eq("ai_reviewed").all()
    assert set(labels["ai_relevance_score"]) == {0, 1, 2, 3, 4}
    assert candidates["human_relevance_score"].eq("").all()

    report = evaluate_ai_relevance_baseline(candidates, labels)
    assert report["pairs_reviewed"] == 50
    assert report["ready_for_experimental_comparison"] is True
    assert report["ready_for_baseline_evaluation"] is False
    assert report["ready_for_ml_qg_3"] is False
    assert report["claim_status"] == "ai_pseudo_labels_not_human_ml_qg_3"


def test_ai_label_evaluation_rejects_missing_pair() -> None:
    labels = create_ai_relevance_labels().iloc[:-1]
    with pytest.raises(ValueError, match="exactly match"):
        evaluate_ai_relevance_baseline(create_relevance_candidate_set(), labels)
