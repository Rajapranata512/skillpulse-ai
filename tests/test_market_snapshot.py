"""Tests for the deterministic, aggregate-only market snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from skillpulse.market.snapshot import build_market_snapshot, generate_market_snapshot
from skillpulse.ui.market import load_market_snapshot, top_skill_rows


@dataclass(frozen=True)
class Match:
    canonical: str


class StubExtractor:
    def extract(self, text: str) -> SimpleNamespace:
        return SimpleNamespace(
            technical_skills=[Match("SQL")] if "sql" in text.casefold() else [],
            tools=[Match("Tableau")] if "tableau" in text.casefold() else [],
            soft_skills=[Match("Communication")] if "communication" in text.casefold() else [],
        )


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "posisi": ["Data Analyst", "DATA ANALYST", "BI Analyst", "BI Analyst", "Engineer", "Scientist"],
            "provinsi": ["Jakarta", "Jakarta", "Banten", "Banten", pd.NA, "Jawa Barat"],
            "deskripsi_lengkap": [
                "SQL and Tableau",
                "SQL and Tableau",
                "SQL communication",
                "SQL",
                "Tableau communication",
                "No explicit taxonomy skill",
            ],
            "level": ["Entry", "Entry", "Mid", "Mid", pd.NA, "Senior"],
            "salary_disclosed": [True, False, False, True, False, False],
        }
    )


def _provenance() -> dict[str, object]:
    return {
        "sources": [
            {
                "id": "fixture",
                "title": "Fixture jobs",
                "creator": "Fixture author",
                "url": "https://example.test/dataset",
                "version": 1,
                "license": {"spdx": "CC-BY-4.0"},
                "observation_window": {"start": "2025-08-25", "end": "2025-09-24", "duration_days": 30},
                "scope": {"geography": "Indonesia", "unit": "one cleaned job posting per row"},
                "local_artifact": {"sha256": "abc123"},
            }
        ]
    }


def test_snapshot_reconciles_grains_normalizes_titles_and_suppresses_small_groups() -> None:
    snapshot = build_market_snapshot(
        _frame(),
        _provenance(),
        extractor=StubExtractor(),
        min_public_count=2,
        min_slice_count=2,
        processed_sha256="fixture-hash",
    )

    assert snapshot["summary"] == {
        "total_listings": 6,
        "unique_descriptions": 5,
        "reported_provinces": 3,
        "salary_disclosed_listings": 2,
        "salary_disclosure_rate": 0.3333,
        "unknown_province_listings": 1,
    }
    assert snapshot["title_counts"] == [
        {"label": "BI Analyst", "count": 2, "share": 0.3333},
        {"label": "Data Analyst", "count": 2, "share": 0.3333},
    ]
    assert snapshot["suppression"]["suppressed_title_listings"] == 2
    sql = next(row for row in snapshot["skill_counts"] if row["label"] == "SQL")
    assert sql == {"category": "technical_skill", "label": "SQL", "count": 3, "share": 0.6}
    assert snapshot["privacy"]["row_level_fields_included"] is False
    slice_labels = [slice_["label"] for slice_ in snapshot["skill_slices"]]
    assert "Location · Banten" in slice_labels
    assert "Role · BI Analyst" in slice_labels
    assert "Location · Jakarta" not in slice_labels  # only one unique description in this fixture
    assert "perusahaan" not in json.dumps(snapshot).casefold()


def test_snapshot_rejects_missing_schema_and_unsafe_threshold() -> None:
    with pytest.raises(ValueError, match="Missing required"):
        build_market_snapshot(_frame().drop(columns="level"), _provenance(), extractor=StubExtractor())
    with pytest.raises(ValueError, match="at least 2"):
        build_market_snapshot(_frame(), _provenance(), extractor=StubExtractor(), min_public_count=1)


def test_generate_snapshot_writes_deterministic_public_artifact_and_passing_qa(tmp_path: Path) -> None:
    input_path = tmp_path / "jobs.csv"
    provenance_path = tmp_path / "sources.yaml"
    output_path = tmp_path / "market.json"
    quality_path = tmp_path / "quality.json"
    _frame().to_csv(input_path, index=False)
    provenance_path.write_text(
        """sources:
  - id: fixture
    title: Fixture jobs
    creator: Fixture author
    url: https://example.test/dataset
    version: 1
    license: {spdx: CC-BY-4.0}
    observation_window: {start: '2025-08-25', end: '2025-09-24', duration_days: 30}
    scope: {geography: Indonesia, unit: one cleaned job posting per row}
    local_artifact: {sha256: abc123}
""",
        encoding="utf-8",
    )

    first, quality = generate_market_snapshot(
        input_path,
        provenance_path,
        output_path,
        quality_path,
        min_public_count=2,
        min_slice_count=2,
        extractor=StubExtractor(),
    )
    first_bytes = output_path.read_bytes()
    second, second_quality = generate_market_snapshot(
        input_path,
        provenance_path,
        output_path,
        quality_path,
        min_public_count=2,
        min_slice_count=2,
        extractor=StubExtractor(),
    )

    assert first == second
    assert first_bytes == output_path.read_bytes()
    assert quality == second_quality
    assert quality["verdict"] == "pass"
    assert all(quality["checks"].values())
    assert load_market_snapshot(output_path)["summary"]["total_listings"] == 6
    assert [row["label"] for row in top_skill_rows(first, "tool", 10)] == ["Tableau"]
