"""Spreadsheet-friendly, human-gated annotation review workflow."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from .annotation_quality import REQUIRED_COLUMNS, validate_annotation_frame
from .engine import EntityExtractor
from .review import FIELD_SPECS, REVIEW_STATUSES, _prediction

HUMAN_REVIEW_STATUSES = {"needs_review", "reviewed"}
GOLD_COLUMNS = tuple(gold_column for _, gold_column, _ in FIELD_SPECS)
SUGGESTION_COLUMNS = tuple(
    f"suggested_{result_field}" for _, _, result_field in FIELD_SPECS
)
REVIEW_BATCH_COLUMNS = (
    "source_row",
    "text",
    "text_sha256",
    "review_status",
    "annotator",
    "notes",
    *(
        column
        for _, gold_column, result_field in FIELD_SPECS
        for column in (gold_column, f"suggested_{result_field}")
    ),
)
AUDIT_COLUMNS = (
    "reviewed_at",
    "source_row",
    "prior_status",
    "new_status",
    "prior_annotator",
    "human_annotator",
    "label_changes_reported",
    "attestation_basis",
)


@dataclass(frozen=True)
class ReviewImportResult:
    """Validated canonical annotations plus a publication-safe audit trail."""

    annotations: pd.DataFrame
    audit_log: pd.DataFrame
    quality_report: dict[str, Any]
    rows_applied: int


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _source_key(value: Any) -> str:
    if value is None or pd.isna(value) or not str(value).strip():
        raise ValueError("source_row must not be blank")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_columns(frame: pd.DataFrame, required: set[str], table_name: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Missing {table_name} columns: {', '.join(missing)}")


def _require_unique_source_rows(frame: pd.DataFrame, table_name: str) -> list[str]:
    keys = [_source_key(value) for value in frame["source_row"]]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise ValueError(f"Duplicate source_row values in {table_name}: {', '.join(duplicates)}")
    return keys


def create_review_batch(
    annotations: pd.DataFrame,
    extractor: EntityExtractor | None = None,
    status: str = "needs_review",
) -> pd.DataFrame:
    """Create an editable batch while keeping model suggestions visibly separate."""
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Unsupported review status: {status}")
    _require_columns(annotations, REQUIRED_COLUMNS, "annotation")
    _require_unique_source_rows(annotations, "annotations")

    selected = annotations[
        annotations["review_status"].fillna("").str.strip().eq(status)
    ]
    engine = extractor or EntityExtractor()
    records: list[dict[str, str]] = []

    for _, source in selected.iterrows():
        text = str(source["text"])
        result = engine.extract(text)
        record = {
            "source_row": _source_key(source["source_row"]),
            "text": text,
            "text_sha256": _text_sha256(text),
            "review_status": _clean(source["review_status"]),
            "annotator": _clean(source["annotator"]),
            "notes": _clean(source["notes"]),
        }
        for _, gold_column, result_field in FIELD_SPECS:
            suggestion = _prediction(result, result_field)
            current = _clean(source[gold_column])
            record[gold_column] = current or suggestion
            record[f"suggested_{result_field}"] = suggestion
        records.append(record)

    return pd.DataFrame(records, columns=REVIEW_BATCH_COLUMNS)


def import_human_review_batch(
    annotations: pd.DataFrame,
    review_batch: pd.DataFrame,
    *,
    human_review_confirmed: bool = False,
    reviewed_at: str | None = None,
) -> ReviewImportResult:
    """Merge explicitly completed human decisions without promoting pending rows."""
    if not human_review_confirmed:
        raise ValueError(
            "Human review confirmation is required; an agent must not promote AI suggestions."
        )
    _require_columns(annotations, REQUIRED_COLUMNS, "annotation")
    _require_columns(review_batch, set(REVIEW_BATCH_COLUMNS), "review batch")
    annotation_keys = _require_unique_source_rows(annotations, "annotations")
    batch_keys = _require_unique_source_rows(review_batch, "review batch")

    statuses = review_batch["review_status"].fillna("").str.strip()
    invalid_statuses = sorted(set(statuses) - HUMAN_REVIEW_STATUSES)
    if invalid_statuses:
        raise ValueError(
            "Review batch status must be needs_review or reviewed; invalid values: "
            + ", ".join(invalid_statuses)
        )

    target_by_key = dict(zip(annotation_keys, annotations.index, strict=True))
    unknown_keys = sorted(set(batch_keys) - set(target_by_key))
    if unknown_keys:
        raise ValueError(f"Unknown source_row values in review batch: {', '.join(unknown_keys)}")

    merged = annotations.copy()
    audit_rows: list[dict[str, str]] = []
    review_date = reviewed_at or date.today().isoformat()

    for batch_index, source_key in zip(review_batch.index, batch_keys, strict=True):
        submitted = review_batch.loc[batch_index]
        target_index = target_by_key[source_key]
        canonical = merged.loc[target_index]
        submitted_text = str(submitted["text"])
        canonical_text = str(canonical["text"])
        expected_hash = _text_sha256(canonical_text)
        submitted_hash = _clean(submitted["text_sha256"])
        if submitted_text != canonical_text or submitted_hash != expected_hash:
            raise ValueError(
                f"Source text or fingerprint changed for source_row {source_key}; export a fresh batch."
            )

        if _clean(submitted["review_status"]) != "reviewed":
            continue
        prior_status = _clean(canonical["review_status"])
        if prior_status != "needs_review":
            raise ValueError(
                f"source_row {source_key} is {prior_status!r}, not needs_review; refusing repeat promotion."
            )
        annotator = _clean(submitted["annotator"])
        notes = _clean(submitted["notes"])
        if not annotator:
            raise ValueError(f"Human annotator is required for source_row {source_key}.")
        if not notes:
            raise ValueError(f"Review notes are required for source_row {source_key}.")

        changed_fields: list[str] = []
        for gold_column in GOLD_COLUMNS:
            new_value = _clean(submitted[gold_column])
            if _clean(canonical[gold_column]) != new_value:
                changed_fields.append(gold_column)
            merged.at[target_index, gold_column] = new_value
        merged.at[target_index, "review_status"] = "reviewed"
        merged.at[target_index, "annotator"] = annotator
        merged.at[target_index, "notes"] = notes
        audit_rows.append(
            {
                "reviewed_at": review_date,
                "source_row": source_key,
                "prior_status": prior_status,
                "new_status": "reviewed",
                "prior_annotator": _clean(canonical["annotator"]),
                "human_annotator": annotator,
                "label_changes_reported": "|".join(changed_fields) or "none",
                "attestation_basis": (
                    "Human reviewer completed the exported batch; import required explicit confirmation."
                ),
            }
        )

    quality_report = validate_annotation_frame(merged)
    if not quality_report["valid"]:
        codes = ", ".join(issue["code"] for issue in quality_report["issues"])
        raise ValueError(f"Imported annotations failed validation: {codes}")

    audit_log = pd.DataFrame(audit_rows, columns=AUDIT_COLUMNS)
    return ReviewImportResult(
        annotations=merged,
        audit_log=audit_log,
        quality_report=quality_report,
        rows_applied=len(audit_rows),
    )


def write_csv_atomic(frame: pd.DataFrame, output: Path) -> None:
    """Write a CSV through a sibling temporary file to avoid partial canonical data."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(output)


def append_audit_log(current_path: Path, new_rows: pd.DataFrame) -> None:
    """Append compatible audit rows atomically; do nothing when no row was applied."""
    if new_rows.empty:
        return
    if current_path.exists():
        current = pd.read_csv(current_path, dtype=str, keep_default_na=False)
        _require_columns(current, set(AUDIT_COLUMNS), "audit log")
        combined = pd.concat([current.loc[:, AUDIT_COLUMNS], new_rows], ignore_index=True)
    else:
        combined = new_rows
    write_csv_atomic(combined, current_path)
