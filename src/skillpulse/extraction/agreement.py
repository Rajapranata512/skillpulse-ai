"""Blind second-annotation workflow and field-level agreement metrics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from .annotation_quality import REQUIRED_COLUMNS, validate_annotation_frame
from .review_batch import GOLD_COLUMNS, _source_key, _text_sha256, write_csv_atomic

SET_FIELDS = {
    "technical_skills": "gold_technical_skills",
    "tools": "gold_tools",
    "soft_skills": "gold_soft_skills",
    "education": "gold_education",
}
SCALAR_FIELDS = {
    "experience_years": "gold_experience_years",
    "seniority": "gold_seniority",
    "work_arrangement": "gold_work_arrangement",
}
BLIND_BATCH_COLUMNS = (
    "source_row",
    "text",
    "text_sha256",
    *GOLD_COLUMNS,
    "review_status",
    "annotator",
    "notes",
)


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _split_labels(value: Any) -> set[str]:
    return {label.strip() for label in _clean(value).split("|") if label.strip()}


def _normalized_scalar(value: Any, field: str) -> str:
    cleaned = _clean(value)
    if field != "experience_years" or not cleaned:
        return cleaned
    try:
        return f"{float(cleaned):g}"
    except ValueError:
        return cleaned


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Missing {name} columns: {', '.join(missing)}")


def _unique_key_map(frame: pd.DataFrame, name: str) -> dict[str, Any]:
    keys = [_source_key(value) for value in frame["source_row"]]
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate source_row values in {name}: {', '.join(duplicates)}")
    return dict(zip(keys, frame.index, strict=True))


def create_blind_second_annotation_batch(primary: pd.DataFrame) -> pd.DataFrame:
    """Export reviewed source texts with every label and model hint removed."""
    _require_columns(primary, REQUIRED_COLUMNS, "primary annotation")
    _unique_key_map(primary, "primary annotations")
    quality = validate_annotation_frame(primary)
    if not quality["valid"]:
        codes = ", ".join(issue["code"] for issue in quality["issues"])
        raise ValueError(f"Primary annotations failed validation: {codes}")

    reviewed = primary[primary["review_status"].fillna("").str.strip().eq("reviewed")]
    if reviewed.empty:
        raise ValueError("Primary annotations contain no reviewed rows.")

    records: list[dict[str, str]] = []
    for _, row in reviewed.iterrows():
        text = str(row["text"])
        record = {
            "source_row": _source_key(row["source_row"]),
            "text": text,
            "text_sha256": _text_sha256(text),
            "review_status": "needs_review",
            "annotator": "",
            "notes": "",
        }
        record.update({column: "" for column in GOLD_COLUMNS})
        records.append(record)
    return pd.DataFrame(records, columns=BLIND_BATCH_COLUMNS)


def cohen_kappa(first: Sequence[str], second: Sequence[str]) -> float | None:
    """Calculate unweighted Cohen's Kappa; return None when chance variance is zero."""
    if len(first) != len(second):
        raise ValueError("Cohen's Kappa inputs must have equal length.")
    if not first:
        return None
    total = len(first)
    observed = sum(left == right for left, right in zip(first, second, strict=True)) / total
    first_counts = Counter(first)
    second_counts = Counter(second)
    categories = set(first_counts) | set(second_counts)
    expected = sum(
        (first_counts[category] / total) * (second_counts[category] / total)
        for category in categories
    )
    denominator = 1 - expected
    if abs(denominator) < 1e-12:
        return None
    return round((observed - expected) / denominator, 4)


def _set_agreement(first: Sequence[set[str]], second: Sequence[set[str]]) -> dict[str, Any]:
    labels = sorted(set().union(*first, *second)) if first else []
    per_label: dict[str, dict[str, float | int | None]] = {}
    defined_kappas: list[float] = []
    intersections = unions = exact = 0

    for left, right in zip(first, second, strict=True):
        intersections += len(left & right)
        unions += len(left | right)
        exact += int(left == right)
    for label in labels:
        left_binary = ["present" if label in values else "absent" for values in first]
        right_binary = ["present" if label in values else "absent" for values in second]
        kappa = cohen_kappa(left_binary, right_binary)
        if kappa is not None:
            defined_kappas.append(kappa)
        per_label[label] = {
            "cohen_kappa": kappa,
            "primary_support": sum(label in values for values in first),
            "secondary_support": sum(label in values for values in second),
        }

    return {
        "documents": len(first),
        "document_exact_match": round(exact / len(first), 4) if first else None,
        "micro_jaccard": (
            None if not first else round(intersections / unions, 4) if unions else 1.0
        ),
        "macro_label_cohen_kappa": (
            round(sum(defined_kappas) / len(defined_kappas), 4) if defined_kappas else None
        ),
        "labels": per_label,
    }


def _scalar_agreement(first: Sequence[str], second: Sequence[str]) -> dict[str, Any]:
    exact = sum(left == right for left, right in zip(first, second, strict=True))
    return {
        "documents": len(first),
        "exact_match": round(exact / len(first), 4) if first else None,
        "cohen_kappa": cohen_kappa(first, second),
    }


def evaluate_annotation_agreement(
    primary: pd.DataFrame,
    secondary: pd.DataFrame,
    *,
    minimum_documents: int = 100,
) -> dict[str, Any]:
    """Compare completed blind annotations and report ML-QG-2 readiness honestly."""
    if minimum_documents < 1:
        raise ValueError("minimum_documents must be positive")
    _require_columns(primary, REQUIRED_COLUMNS, "primary annotation")
    _require_columns(secondary, REQUIRED_COLUMNS | {"text_sha256"}, "secondary annotation")
    primary_map = _unique_key_map(primary, "primary annotations")
    secondary_map = _unique_key_map(secondary, "secondary annotations")
    unknown = sorted(set(secondary_map) - set(primary_map))
    if unknown:
        raise ValueError(f"Unknown source_row values in secondary annotations: {', '.join(unknown)}")

    primary_quality = validate_annotation_frame(primary)
    secondary_quality = validate_annotation_frame(secondary)
    if not primary_quality["valid"]:
        codes = ", ".join(issue["code"] for issue in primary_quality["issues"])
        raise ValueError(f"Primary annotations failed validation: {codes}")
    if not secondary_quality["valid"]:
        codes = ", ".join(issue["code"] for issue in secondary_quality["issues"])
        raise ValueError(f"Secondary annotations failed validation: {codes}")

    for source_key, secondary_index in secondary_map.items():
        primary_row = primary.loc[primary_map[source_key]]
        secondary_row = secondary.loc[secondary_index]
        primary_text = str(primary_row["text"])
        if (
            str(secondary_row["text"]) != primary_text
            or _clean(secondary_row["text_sha256"]) != _text_sha256(primary_text)
        ):
            raise ValueError(f"Source text or fingerprint changed for source_row {source_key}.")

    completed_keys = [
        key
        for key, index in secondary_map.items()
        if _clean(secondary.loc[index, "review_status"]) == "reviewed"
    ]
    invalid_primary = [
        key
        for key in completed_keys
        if _clean(primary.loc[primary_map[key], "review_status"]) != "reviewed"
    ]
    if invalid_primary:
        raise ValueError("Secondary rows must map to reviewed primary rows.")

    primary_rows = [primary.loc[primary_map[key]] for key in completed_keys]
    secondary_rows = [secondary.loc[secondary_map[key]] for key in completed_keys]
    metrics: dict[str, Any] = {}
    for field, column in SET_FIELDS.items():
        first = [_split_labels(row[column]) for row in primary_rows]
        second = [_split_labels(row[column]) for row in secondary_rows]
        metrics[field] = _set_agreement(first, second)
    for field, column in SCALAR_FIELDS.items():
        first = [_normalized_scalar(row[column], field) for row in primary_rows]
        second = [_normalized_scalar(row[column], field) for row in secondary_rows]
        metrics[field] = _scalar_agreement(first, second)

    primary_annotators = sorted({_clean(row["annotator"]) for row in primary_rows if _clean(row["annotator"])})
    secondary_annotators = sorted(
        {_clean(row["annotator"]) for row in secondary_rows if _clean(row["annotator"])}
    )
    annotators_are_independent = bool(secondary_annotators) and not (
        set(primary_annotators) & set(secondary_annotators)
    )
    notes_complete = bool(secondary_rows) and all(
        _clean(row["notes"]) for row in secondary_rows
    )
    enough_documents = len(completed_keys) >= minimum_documents
    warnings: list[str] = []
    if not enough_documents:
        warnings.append(
            f"Only {len(completed_keys)} completed pairs; ML-QG-2 requires at least {minimum_documents}."
        )
    if not annotators_are_independent:
        warnings.append("Secondary annotator identity must be independent from primary annotators.")
    if not notes_complete:
        warnings.append("Every completed secondary row requires non-empty review notes.")
    warnings.append(
        "Primary gold is AI-assisted and human-confirmed; agreement measures annotation "
        "reproducibility, not model generalization."
    )

    return {
        "evaluation_type": "blind human annotation agreement",
        "minimum_documents": minimum_documents,
        "documents_available": len(secondary),
        "documents_compared": len(completed_keys),
        "primary_annotators": primary_annotators,
        "secondary_annotators": secondary_annotators,
        "annotators_are_independent": annotators_are_independent,
        "secondary_notes_complete": notes_complete,
        "ready_for_ml_qg_2": enough_documents and annotators_are_independent and notes_complete,
        "metrics": metrics,
        "warnings": warnings,
    }


def write_blind_second_annotation_batch(primary: pd.DataFrame, output: Path) -> int:
    """Write the blind batch atomically and return its document count."""
    batch = create_blind_second_annotation_batch(primary)
    write_csv_atomic(batch, output)
    return len(batch)
