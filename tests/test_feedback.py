from __future__ import annotations

import json

import pytest

from skillpulse.feedback import (
    ExtractionFeedbackContext,
    build_extraction_feedback,
    extraction_feedback_context,
    feedback_json,
)


def _response() -> dict[str, object]:
    return {
        "contract_version": "1.0.0",
        "model_version": "taxonomy-rules-0.2.0",
        "taxonomy_version": "0.2.0",
        "technical_skills": [
            {"canonical": "SQL", "matched_text": "sensitive phrase", "start": 10, "end": 13},
            {"canonical": "Python", "matched_text": "raw source", "start": 20, "end": 26},
            {"canonical": "SQL", "matched_text": "duplicate source", "start": 30, "end": 33},
        ],
        "tools": [{"canonical": "Power BI", "matched_text": "power bi", "start": 40, "end": 48}],
        "soft_skills": [],
        "education": ["Bachelor"],
    }


def test_feedback_context_keeps_only_versions_and_canonical_labels() -> None:
    context = extraction_feedback_context(_response())

    assert [candidate.id for candidate in context.candidates] == [
        "technical_skills::SQL",
        "technical_skills::Python",
        "tools::Power BI",
        "education::Bachelor",
    ]
    assert "sensitive phrase" not in repr(context)
    assert "start" not in repr(context)


def test_feedback_export_is_deterministic_and_explicitly_privacy_safe() -> None:
    context = extraction_feedback_context(_response())
    record = build_extraction_feedback(
        context,
        incorrect_ids={"tools::Power BI"},
        review_confirmed=True,
    )
    serialized = feedback_json(record)

    assert json.loads(serialized) == record
    assert record["summary"] == {
        "reviewed_entities": 4,
        "correct_entities": 3,
        "incorrect_entities": 1,
    }
    assert [item["verdict"] for item in record["items"]] == ["correct", "correct", "incorrect", "correct"]
    assert all(value is False for value in record["privacy"].values())
    assert "raw source" not in serialized
    assert '"matched_text":' not in serialized


@pytest.mark.parametrize(
    ("incorrect_ids", "confirmed", "message"),
    [
        (set(), False, "confirmation"),
        ({"tools::Unknown"}, True, "Unknown feedback candidate"),
    ],
)
def test_feedback_export_fails_closed(
    incorrect_ids: set[str],
    confirmed: bool,
    message: str,
) -> None:
    context = extraction_feedback_context(_response())

    with pytest.raises(ValueError, match=message):
        build_extraction_feedback(
            context,
            incorrect_ids=incorrect_ids,
            review_confirmed=confirmed,
        )


def test_feedback_export_rejects_empty_extraction() -> None:
    context = ExtractionFeedbackContext(
        contract_version="1.0.0",
        model_version="taxonomy-rules-0.2.0",
        taxonomy_version="0.2.0",
        candidates=(),
    )

    with pytest.raises(ValueError, match="No extracted canonical entities"):
        build_extraction_feedback(context, incorrect_ids=set(), review_confirmed=True)
