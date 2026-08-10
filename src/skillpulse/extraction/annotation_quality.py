"""Quality checks for SkillPulse annotation tables."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from .engine import EntityExtractor

REQUIRED_COLUMNS = {
    "source_row",
    "text",
    "gold_technical_skills",
    "gold_tools",
    "gold_soft_skills",
    "gold_education",
    "gold_experience_years",
    "gold_seniority",
    "gold_work_arrangement",
    "review_status",
    "annotator",
    "notes",
}
ALLOWED_STATUSES = {"needs_review", "ai_reviewed", "reviewed"}
ALLOWED_EDUCATION = {"High School", "Diploma", "Bachelor", "Master", "Doctorate"}
ALLOWED_SENIORITY = {"entry", "mid", "senior", "unknown"}
ALLOWED_ARRANGEMENT = {"remote", "hybrid", "onsite", "unknown"}


def _labels(value: Any) -> set[str]:
    if pd.isna(value):
        return set()
    return {item.strip() for item in str(value).split("|") if item.strip()}


def _issue(
    code: str, severity: str, count: int, examples: list[str], message: str
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "count": int(count),
        "examples": examples[:10],
        "message": message,
    }


def validate_annotation_frame(
    frame: pd.DataFrame, extractor: EntityExtractor | None = None
) -> dict[str, Any]:
    """Return inspectable schema and domain checks without mutating annotations."""
    missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing_columns:
        return {
            "valid": False,
            "rows": int(len(frame)),
            "issues": [
                _issue(
                    "missing_columns",
                    "critical",
                    len(missing_columns),
                    missing_columns,
                    "Required annotation columns are missing.",
                )
            ],
        }

    extractor = extractor or EntityExtractor()
    statuses = frame["review_status"].fillna("").str.strip()
    status_counts = {key: int(value) for key, value in Counter(statuses).items()}
    reviewed_mask = statuses.isin({"ai_reviewed", "reviewed"})
    reviewed = frame[reviewed_mask]
    issues: list[dict[str, Any]] = []

    duplicate_mask = frame["source_row"].astype(str).duplicated(keep=False)
    if duplicate_mask.any():
        duplicate_values = sorted(frame.loc[duplicate_mask, "source_row"].astype(str).unique())
        issues.append(
            _issue(
                "duplicate_source_row",
                "high",
                int(duplicate_mask.sum()),
                duplicate_values,
                "Annotation grain must be one row per source document.",
            )
        )

    empty_text_mask = frame["text"].fillna("").str.strip().eq("")
    if empty_text_mask.any():
        issues.append(
            _issue(
                "empty_text",
                "critical",
                int(empty_text_mask.sum()),
                frame.loc[empty_text_mask, "source_row"].astype(str).tolist(),
                "Every annotation row must contain the complete source text.",
            )
        )

    invalid_status_mask = ~statuses.isin(ALLOWED_STATUSES)
    if invalid_status_mask.any():
        issues.append(
            _issue(
                "invalid_review_status",
                "high",
                int(invalid_status_mask.sum()),
                sorted(statuses[invalid_status_mask].unique().tolist()),
                "Review status must use the controlled workflow values.",
            )
        )

    missing_annotator = reviewed["annotator"].fillna("").str.strip().eq("")
    if missing_annotator.any():
        issues.append(
            _issue(
                "missing_annotator",
                "high",
                int(missing_annotator.sum()),
                reviewed.loc[missing_annotator, "source_row"].astype(str).tolist(),
                "Every reviewed or AI-reviewed row requires an annotator identifier.",
            )
        )

    scalar_rules = {
        "gold_seniority": ALLOWED_SENIORITY,
        "gold_work_arrangement": ALLOWED_ARRANGEMENT,
    }
    for column, allowed in scalar_rules.items():
        values = reviewed[column].fillna("").str.strip()
        invalid = ~values.isin(allowed)
        if invalid.any():
            issues.append(
                _issue(
                    f"invalid_{column}",
                    "high",
                    int(invalid.sum()),
                    sorted(values[invalid].unique().tolist()),
                    f"{column} contains blank or unsupported values in completed rows.",
                )
            )

    invalid_experience: list[str] = []
    for _, row in reviewed.iterrows():
        value = row["gold_experience_years"]
        if pd.isna(value) or str(value).strip() == "":
            continue
        try:
            if float(value) < 0:
                invalid_experience.append(str(row["source_row"]))
        except (TypeError, ValueError):
            invalid_experience.append(str(row["source_row"]))
    if invalid_experience:
        issues.append(
            _issue(
                "invalid_experience_years",
                "high",
                len(invalid_experience),
                invalid_experience,
                "Experience must be blank or a non-negative number.",
            )
        )

    skill_types = {entity["canonical"]: entity["type"] for entity in extractor.skills}
    canonical_rules = {
        "gold_technical_skills": {
            name for name, entity_type in skill_types.items() if entity_type == "technical_skill"
        },
        "gold_tools": {
            name for name, entity_type in skill_types.items() if entity_type == "tool"
        },
        "gold_soft_skills": {entity["canonical"] for entity in extractor.soft_skills},
        "gold_education": ALLOWED_EDUCATION,
    }
    for column, allowed in canonical_rules.items():
        unknown: Counter[str] = Counter()
        for value in reviewed[column]:
            unknown.update(_labels(value) - allowed)
        if unknown:
            issues.append(
                _issue(
                    f"unknown_{column}",
                    "high",
                    sum(unknown.values()),
                    [f"{label} ({count})" for label, count in unknown.most_common()],
                    f"{column} contains labels outside the versioned canonical schema.",
                )
            )

    blocking = [issue for issue in issues if issue["severity"] in {"critical", "high"}]
    human_rows = status_counts.get("reviewed", 0)
    ai_rows = status_counts.get("ai_reviewed", 0)
    return {
        "valid": not blocking,
        "rows": int(len(frame)),
        "unique_source_rows": int(frame["source_row"].astype(str).nunique()),
        "status_counts": status_counts,
        "completed_rows": int(reviewed_mask.sum()),
        "notes_completion_rate": round(
            reviewed["notes"].fillna("").str.strip().ne("").mean(), 4
        )
        if len(reviewed)
        else 0.0,
        "ready_for_provisional_evaluation": bool(ai_rows and not blocking),
        "ready_for_human_gold_evaluation": bool(human_rows and not blocking),
        "issues": issues,
    }
