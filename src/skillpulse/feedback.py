"""Privacy-safe, deterministic extraction-feedback export."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

FEEDBACK_SCHEMA_VERSION = "1.0.0"
ENTITY_CATEGORIES = ("technical_skills", "tools", "soft_skills", "education")
FeedbackVerdict = Literal["correct", "incorrect"]


@dataclass(frozen=True)
class FeedbackCandidate:
    """One canonical extraction result that can be reviewed without source text."""

    id: str
    category: str
    canonical: str

    @property
    def label(self) -> str:
        return f"{self.category.replace('_', ' ').title()} - {self.canonical}"


@dataclass(frozen=True)
class ExtractionFeedbackContext:
    """Versioned redacted context retained only in the current UI session."""

    contract_version: str
    model_version: str
    taxonomy_version: str
    candidates: tuple[FeedbackCandidate, ...]


def _required_version(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Extraction response is missing {field}.")
    return value


def extraction_feedback_context(payload: dict[str, Any]) -> ExtractionFeedbackContext:
    """Reduce an extraction response to versions and canonical labels only."""

    candidates: list[FeedbackCandidate] = []
    seen: set[str] = set()
    for category in ENTITY_CATEGORIES:
        values = payload.get(category, [])
        if not isinstance(values, list):
            raise ValueError(f"Extraction response field {category} must be a list.")
        for value in values:
            canonical = value.get("canonical") if isinstance(value, dict) else value
            if not isinstance(canonical, str) or not canonical.strip():
                raise ValueError(f"Extraction response field {category} contains an invalid canonical value.")
            canonical = canonical.strip()
            candidate_id = f"{category}::{canonical}"
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            candidates.append(FeedbackCandidate(id=candidate_id, category=category, canonical=canonical))

    return ExtractionFeedbackContext(
        contract_version=_required_version(payload, "contract_version"),
        model_version=_required_version(payload, "model_version"),
        taxonomy_version=_required_version(payload, "taxonomy_version"),
        candidates=tuple(candidates),
    )


def build_extraction_feedback(
    context: ExtractionFeedbackContext,
    *,
    incorrect_ids: set[str],
    review_confirmed: bool,
) -> dict[str, Any]:
    """Build a download-only review record with no raw or matched text."""

    if not review_confirmed:
        raise ValueError("Human review confirmation is required before feedback export.")
    if not context.candidates:
        raise ValueError("No extracted canonical entities are available for review.")

    known_ids = {candidate.id for candidate in context.candidates}
    unknown_ids = incorrect_ids - known_ids
    if unknown_ids:
        raise ValueError(f"Unknown feedback candidate: {sorted(unknown_ids)[0]}")

    items = [
        {
            "category": candidate.category,
            "canonical": candidate.canonical,
            "verdict": "incorrect" if candidate.id in incorrect_ids else "correct",
        }
        for candidate in context.candidates
    ]
    return {
        "schema_version": FEEDBACK_SCHEMA_VERSION,
        "feedback_type": "extraction_review",
        "subject": "job_description",
        "source_versions": {
            "contract": context.contract_version,
            "model": context.model_version,
            "taxonomy": context.taxonomy_version,
        },
        "items": items,
        "summary": {
            "reviewed_entities": len(items),
            "correct_entities": len(items) - len(incorrect_ids),
            "incorrect_entities": len(incorrect_ids),
        },
        "privacy": {
            "contains_raw_text": False,
            "contains_matched_text": False,
            "contains_source_spans": False,
            "contains_user_identity": False,
            "server_persisted": False,
        },
    }


def feedback_json(record: dict[str, Any]) -> str:
    """Return stable UTF-8 JSON suitable for a browser download."""

    return json.dumps(record, ensure_ascii=False, indent=2) + "\n"
