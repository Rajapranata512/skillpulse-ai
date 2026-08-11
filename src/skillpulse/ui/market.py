"""Read and shape the aggregate-only market snapshot for the Streamlit page."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_SNAPSHOT_PATH = Path(__file__).resolve().parents[3] / "configs" / "market_snapshot.json"

CATEGORY_LABELS = {
    "all": "All extracted requirements",
    "technical_skill": "Technical skills",
    "tool": "Tools",
    "soft_skill": "Soft skills",
}


def load_market_snapshot(path: Path = DEFAULT_SNAPSHOT_PATH) -> dict[str, Any]:
    """Load a validated public aggregate, never a row-level dataset."""
    if not path.exists():
        raise FileNotFoundError(f"Market snapshot not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "source",
        "summary",
        "metric_contract",
        "province_counts",
        "seniority_counts",
        "title_counts",
        "skill_counts",
        "skill_slices",
        "privacy",
        "caveats",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Market snapshot is missing fields: {', '.join(missing)}")
    if not payload["privacy"].get("aggregate_only") or payload["privacy"].get("row_level_fields_included"):
        raise ValueError("Market snapshot violates the aggregate-only privacy contract.")
    return payload


def market_slice_options(snapshot: dict[str, Any]) -> dict[str, str]:
    """Map safe public segment labels to their stable identifiers."""
    return {slice_["label"]: slice_["id"] for slice_ in snapshot["skill_slices"]}


def market_slice(snapshot: dict[str, Any], slice_id: str) -> dict[str, Any]:
    """Resolve one pre-aggregated segment without touching private rows."""
    for slice_ in snapshot["skill_slices"]:
        if slice_["id"] == slice_id:
            return slice_
    raise ValueError(f"Unknown market slice: {slice_id}")


def top_skill_rows(
    snapshot: dict[str, Any], category: str, limit: int, *, slice_id: str = "overall"
) -> list[dict[str, Any]]:
    """Return ranked chart rows for one safe segment and requirement category."""
    if category not in CATEGORY_LABELS:
        raise ValueError(f"Unknown skill category: {category}")
    selected = market_slice(snapshot, slice_id)
    rows = [row for row in selected["skill_counts"] if category == "all" or row["category"] == category]
    rows.sort(key=lambda row: (-row["count"], row["label"].casefold()))
    return rows[:limit]


def top_rows(snapshot: dict[str, Any], field: str, limit: int) -> list[dict[str, Any]]:
    """Return a bounded ranked aggregate for a known public dimension."""
    if field not in {"province_counts", "seniority_counts", "title_counts"}:
        raise ValueError(f"Unsupported market snapshot field: {field}")
    return list(snapshot[field][:limit])
