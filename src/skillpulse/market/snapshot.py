"""Build a deterministic, public-safe snapshot from the private cleaned job rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
import yaml

from skillpulse.extraction.engine import EntityExtractor, ExtractionResult

DEFAULT_INPUT = Path("data/processed/jobs_clean.csv")
DEFAULT_PROVENANCE = Path("data/provenance/sources.yaml")
DEFAULT_OUTPUT = Path("configs/market_snapshot.json")
DEFAULT_QUALITY_REPORT = Path("reports/market_snapshot_quality.json")
DEFAULT_MIN_PUBLIC_COUNT = 3
DEFAULT_MIN_SLICE_COUNT = 10

REQUIRED_COLUMNS = {
    "posisi",
    "provinsi",
    "deskripsi_lengkap",
    "level",
    "salary_disclosed",
}


class Extractor(Protocol):
    """Small contract used to keep aggregation testable."""

    def extract(self, text: str) -> ExtractionResult: ...


def _clean_label(value: object, *, unknown: str = "Unknown") -> str:
    if pd.isna(value):
        return unknown
    label = re.sub(r"\s+", " ", str(value)).strip()
    return label or unknown


def _share(count: int, denominator: int) -> float:
    return round(count / denominator, 4) if denominator else 0.0


def _ranked_counts(labels: list[str], denominator: int) -> list[dict[str, Any]]:
    counts = Counter(labels)
    return [
        {"label": label, "count": count, "share": _share(count, denominator)}
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))
    ]


def _title_counts(frame: pd.DataFrame, *, min_public_count: int) -> tuple[list[dict[str, Any]], int]:
    variants: dict[str, Counter[str]] = defaultdict(Counter)
    for raw_title in frame["posisi"]:
        display = _clean_label(raw_title)
        variants[display.casefold()][display] += 1

    published: list[dict[str, Any]] = []
    suppressed = 0
    total = len(frame)
    for spellings in variants.values():
        count = sum(spellings.values())
        if count < min_public_count:
            suppressed += count
            continue
        display = sorted(
            spellings.items(),
            key=lambda item: (-item[1], item[0].isupper(), item[0].casefold(), item[0]),
        )[0][0]
        published.append({"label": display, "count": count, "share": _share(count, total)})
    published.sort(key=lambda item: (-item["count"], item["label"].casefold()))
    return published, suppressed


def _skill_counts(
    frame: pd.DataFrame,
    *,
    extractor: Extractor,
    min_public_count: int,
    cache: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    descriptions = list(dict.fromkeys(_clean_label(value) for value in frame["deskripsi_lengkap"]))
    counts: Counter[tuple[str, str]] = Counter()
    cache = cache if cache is not None else {}
    for description in descriptions:
        if description not in cache:
            cache[description] = extractor.extract(description)
        result = cache[description]
        for category, matches in (
            ("technical_skill", result.technical_skills),
            ("tool", result.tools),
            ("soft_skill", result.soft_skills),
        ):
            counts.update((category, match.canonical) for match in matches)

    rows = [
        {
            "category": category,
            "label": label,
            "count": count,
            "share": _share(count, len(descriptions)),
        }
        for (category, label), count in counts.items()
        if count >= min_public_count
    ]
    rows.sort(key=lambda item: (item["category"], -item["count"], item["label"].casefold()))
    return rows, len(descriptions)


def _skill_slices(
    frame: pd.DataFrame,
    *,
    extractor: Extractor,
    min_public_count: int,
    min_slice_count: int,
    cache: dict[str, Any],
    overall_counts: list[dict[str, Any]],
    overall_unique_descriptions: int,
    title_counts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    slices = [
        {
            "id": "overall",
            "dimension": "overall",
            "label": "All listings",
            "listing_count": len(frame),
            "unique_descriptions": overall_unique_descriptions,
            "skill_counts": overall_counts,
        }
    ]

    province_labels = frame["provinsi"].map(_clean_label)
    for row in _ranked_counts(province_labels.tolist(), len(frame)):
        if row["label"] == "Unknown" or row["count"] < min_slice_count:
            continue
        subset = frame.loc[province_labels == row["label"]]
        counts, unique_descriptions = _skill_counts(
            subset,
            extractor=extractor,
            min_public_count=min_public_count,
            cache=cache,
        )
        if unique_descriptions >= min_slice_count:
            slices.append(
                {
                    "id": f"province:{row['label'].casefold()}",
                    "dimension": "province",
                    "label": f"Location · {row['label']}",
                    "listing_count": len(subset),
                    "unique_descriptions": unique_descriptions,
                    "skill_counts": counts,
                }
            )

    normalized_titles = frame["posisi"].map(lambda value: _clean_label(value).casefold())
    for row in title_counts:
        if row["count"] < min_slice_count:
            continue
        title_key = row["label"].casefold()
        subset = frame.loc[normalized_titles == title_key]
        counts, unique_descriptions = _skill_counts(
            subset,
            extractor=extractor,
            min_public_count=min_public_count,
            cache=cache,
        )
        if unique_descriptions >= min_slice_count:
            slices.append(
                {
                    "id": f"role:{title_key}",
                    "dimension": "role",
                    "label": f"Role · {row['label']}",
                    "listing_count": len(subset),
                    "unique_descriptions": unique_descriptions,
                    "skill_counts": counts,
                }
            )
    return slices


def _source_metadata(provenance: dict[str, Any]) -> dict[str, Any]:
    sources = provenance.get("sources", [])
    if len(sources) != 1:
        raise ValueError("Expected exactly one documented source for the market snapshot.")
    source = sources[0]
    window = source["observation_window"]
    return {
        "dataset_id": source["id"],
        "title": source["title"],
        "creator": source["creator"],
        "url": source["url"],
        "version": source["version"],
        "license": source["license"]["spdx"],
        "observation_window": {
            "start": str(window["start"]),
            "end": str(window["end"]),
            "duration_days": int(window["duration_days"]),
        },
        "scope": source["scope"],
        "raw_sha256": source["local_artifact"]["sha256"],
    }


def build_market_snapshot(
    frame: pd.DataFrame,
    provenance: dict[str, Any],
    *,
    extractor: Extractor | None = None,
    min_public_count: int = DEFAULT_MIN_PUBLIC_COUNT,
    min_slice_count: int = DEFAULT_MIN_SLICE_COUNT,
    processed_sha256: str | None = None,
) -> dict[str, Any]:
    """Aggregate cleaned rows without exposing job-level fields or unsupported trends."""
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required market snapshot columns: {', '.join(missing)}")
    if min_public_count < 2:
        raise ValueError("min_public_count must be at least 2 for a public aggregate.")
    if min_slice_count < min_public_count:
        raise ValueError("min_slice_count must be at least min_public_count.")
    if frame.empty:
        raise ValueError("Cannot build a market snapshot from an empty dataset.")
    if frame["deskripsi_lengkap"].isna().any():
        raise ValueError("Market snapshot descriptions must not be missing.")

    extractor = extractor or EntityExtractor()
    total = len(frame)
    extraction_cache: dict[str, Any] = {}
    skill_counts, unique_descriptions = _skill_counts(
        frame,
        extractor=extractor,
        min_public_count=min_public_count,
        cache=extraction_cache,
    )
    title_counts, suppressed_titles = _title_counts(frame, min_public_count=min_public_count)
    skill_slices = _skill_slices(
        frame,
        extractor=extractor,
        min_public_count=min_public_count,
        min_slice_count=min_slice_count,
        cache=extraction_cache,
        overall_counts=skill_counts,
        overall_unique_descriptions=unique_descriptions,
        title_counts=title_counts,
    )
    provinces = [_clean_label(value) for value in frame["provinsi"]]
    seniority = [_clean_label(value) for value in frame["level"]]
    salary_disclosed = int(frame["salary_disclosed"].fillna(False).astype(bool).sum())
    reported_provinces = len({label for label in provinces if label != "Unknown"})

    return {
        "schema_version": "1.0.0",
        "source": _source_metadata(provenance),
        "input_fingerprint": {"processed_sha256": processed_sha256 or "not-recorded"},
        "summary": {
            "total_listings": total,
            "unique_descriptions": unique_descriptions,
            "reported_provinces": reported_provinces,
            "salary_disclosed_listings": salary_disclosed,
            "salary_disclosure_rate": _share(salary_disclosed, total),
            "unknown_province_listings": provinces.count("Unknown"),
        },
        "metric_contract": {
            "listing_denominator": total,
            "skill_demand_denominator": unique_descriptions,
            "listing_grain": "one cleaned job posting row",
            "skill_demand_grain": "one exact-unique full job description",
            "skill_measure": "documents with at least one canonical taxonomy match",
            "title_normalization": "case-insensitive with collapsed whitespace",
            "seniority_source": "source-provided level; missing values shown as Unknown",
            "filter_design": "one independent overall, province, or normalized-title slice",
            "filter_slice_minimum_unique_descriptions": min_slice_count,
        },
        "province_counts": _ranked_counts(provinces, total),
        "seniority_counts": _ranked_counts(seniority, total),
        "title_counts": title_counts,
        "skill_counts": skill_counts,
        "skill_slices": skill_slices,
        "suppression": {
            "minimum_published_count": min_public_count,
            "minimum_slice_descriptions": min_slice_count,
            "suppressed_title_listings": suppressed_titles,
            "applies_to": ["title_counts", "skill_counts"],
        },
        "privacy": {
            "aggregate_only": True,
            "row_level_fields_included": False,
            "company_names_included": False,
            "raw_descriptions_included": False,
            "salary_values_included": False,
        },
        "caveats": [
            "This is a 30-day snapshot of one Kaggle dataset sourced from JobStreet Indonesia, not the whole market.",
            "There is only one observation window, so the dashboard cannot support trend or change claims.",
            "Skill demand is rule-extracted from explicit text and is not a human-validated market label.",
            "Salary is shown only as disclosure coverage because the modelling data gate is not met.",
        ],
    }


def _quality_report(snapshot: dict[str, Any], artifact_bytes: bytes) -> dict[str, Any]:
    summary = snapshot["summary"]
    total = summary["total_listings"]
    title_reconciliation = sum(row["count"] for row in snapshot["title_counts"])
    title_reconciliation += snapshot["suppression"]["suppressed_title_listings"]
    checks = {
        "province_counts_reconcile_to_listings": sum(row["count"] for row in snapshot["province_counts"]) == total,
        "seniority_counts_reconcile_to_listings": sum(row["count"] for row in snapshot["seniority_counts"]) == total,
        "title_counts_reconcile_after_suppression": title_reconciliation == total,
        "skill_counts_do_not_exceed_denominator": all(
            row["count"] <= summary["unique_descriptions"] for row in snapshot["skill_counts"]
        ),
        "slice_counts_do_not_exceed_denominators": all(
            row["count"] <= slice_["unique_descriptions"]
            for slice_ in snapshot["skill_slices"]
            for row in slice_["skill_counts"]
        ),
        "filtered_slices_meet_minimum_size": all(
            slice_["id"] == "overall"
            or slice_["unique_descriptions"] >= snapshot["suppression"]["minimum_slice_descriptions"]
            for slice_ in snapshot["skill_slices"]
        ),
        "overall_slice_reconciles": snapshot["skill_slices"][0]["skill_counts"] == snapshot["skill_counts"],
        "public_counts_meet_threshold": all(
            row["count"] >= snapshot["suppression"]["minimum_published_count"]
            for field in ("title_counts", "skill_counts")
            for row in snapshot[field]
        )
        and all(
            row["count"] >= snapshot["suppression"]["minimum_published_count"]
            for slice_ in snapshot["skill_slices"]
            for row in slice_["skill_counts"]
        ),
        "aggregate_privacy_contract": all(
            (
                snapshot["privacy"]["aggregate_only"],
                not snapshot["privacy"]["row_level_fields_included"],
                not snapshot["privacy"]["company_names_included"],
                not snapshot["privacy"]["raw_descriptions_included"],
                not snapshot["privacy"]["salary_values_included"],
            )
        ),
        "single_window_disables_trend_claims": snapshot["source"]["observation_window"]["duration_days"] == 30,
    }
    return {
        "schema_version": "1.0.0",
        "artifact_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "rows_profiled": total,
        "unique_descriptions_profiled": summary["unique_descriptions"],
        "checks": checks,
        "verdict": "pass" if all(checks.values()) else "fail",
    }


def generate_market_snapshot(
    input_path: Path = DEFAULT_INPUT,
    provenance_path: Path = DEFAULT_PROVENANCE,
    output_path: Path = DEFAULT_OUTPUT,
    quality_report_path: Path = DEFAULT_QUALITY_REPORT,
    *,
    min_public_count: int = DEFAULT_MIN_PUBLIC_COUNT,
    min_slice_count: int = DEFAULT_MIN_SLICE_COUNT,
    extractor: Extractor | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read private rows, then persist only a deterministic aggregate and its QA evidence."""
    if not input_path.exists():
        raise FileNotFoundError(f"Cleaned input not found: {input_path}")
    if not provenance_path.exists():
        raise FileNotFoundError(f"Provenance not found: {provenance_path}")
    input_bytes = input_path.read_bytes()
    frame = pd.read_csv(input_path)
    provenance = yaml.safe_load(provenance_path.read_text(encoding="utf-8"))
    snapshot = build_market_snapshot(
        frame,
        provenance,
        extractor=extractor,
        min_public_count=min_public_count,
        min_slice_count=min_slice_count,
        processed_sha256=hashlib.sha256(input_bytes).hexdigest(),
    )
    artifact_text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    artifact_bytes = artifact_text.encode("utf-8")
    quality = _quality_report(snapshot, artifact_bytes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    quality_report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(artifact_bytes)
    quality_report_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot, quality


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--quality-report", type=Path, default=DEFAULT_QUALITY_REPORT)
    parser.add_argument("--min-public-count", type=int, default=DEFAULT_MIN_PUBLIC_COUNT)
    parser.add_argument("--min-slice-count", type=int, default=DEFAULT_MIN_SLICE_COUNT)
    args = parser.parse_args()
    generate_market_snapshot(
        args.input,
        args.provenance,
        args.output,
        args.quality_report,
        min_public_count=args.min_public_count,
        min_slice_count=args.min_slice_count,
    )
    print("Market snapshot generation completed; inspect the configured quality-report artifact.")


if __name__ == "__main__":
    main()
