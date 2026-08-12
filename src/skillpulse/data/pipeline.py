"""Reproducible preparation pipeline for the SkillPulse job dataset."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_INPUT = Path("lowongan data dan analytics jobstreet.csv")
DEFAULT_OUTPUT = Path("data/processed/jobs_clean.csv")
DEFAULT_REPORT = Path("reports/data_quality.json")

REQUIRED_COLUMNS = {
    "posisi",
    "perusahaan",
    "kota",
    "provinsi",
    "gaji",
    "tools",
    "pendidikan",
    "pengalaman",
    "deskripsi_lengkap",
    "level",
}

TEXT_COLUMNS = [
    "posisi",
    "perusahaan",
    "kota",
    "provinsi",
    "tools",
    "pendidikan",
    "deskripsi_lengkap",
    "level",
]


def _normalize_text(value: Any) -> Any:
    """Trim and collapse whitespace while preserving missing values."""
    if pd.isna(value):
        return pd.NA
    normalized = re.sub(r"\s+", " ", str(value)).strip()
    return normalized if normalized else pd.NA


def _parse_salary(value: Any) -> float | None:
    """Parse a single numeric IDR salary without inventing missing ranges."""
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if not text or text in {"nan", "none", "n/a", "-"}:
        return None

    compact = re.sub(r"[^0-9,.]", "", text)
    if not compact:
        return None

    # The current source stores whole-number IDR values, sometimes as 9500000.0.
    compact = compact.replace(",", "")
    try:
        parsed = float(compact)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def validate_schema(frame: pd.DataFrame) -> None:
    """Fail early when a source file does not match the documented schema."""
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def build_quality_report(raw: pd.DataFrame, clean: pd.DataFrame) -> dict[str, Any]:
    """Return JSON-serializable quality indicators for review and CI artifacts."""
    salary_count = int(clean["salary_monthly_idr"].notna().sum())
    return {
        "raw_rows": int(len(raw)),
        "clean_rows": int(len(clean)),
        "removed_duplicate_rows": int(len(raw) - len(clean)),
        "columns": int(len(clean.columns)),
        "salary_disclosed_rows": salary_count,
        "salary_disclosure_rate": round(salary_count / len(clean), 4) if len(clean) else 0.0,
        "missing_by_column": {
            column: int(clean[column].isna().sum()) for column in clean.columns
        },
        "unique_job_descriptions": int(clean["deskripsi_lengkap"].nunique(dropna=True)),
    }


def prepare_jobs(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Validate, clean, deduplicate, and profile a job vacancy dataframe."""
    validate_schema(frame)
    raw = frame.copy()
    clean = frame.copy()

    for column in TEXT_COLUMNS:
        clean[column] = clean[column].map(_normalize_text)

    clean["pengalaman"] = pd.to_numeric(clean["pengalaman"], errors="coerce")
    clean["salary_monthly_idr"] = clean["gaji"].map(_parse_salary).astype("Float64")
    clean["salary_disclosed"] = clean["salary_monthly_idr"].notna()

    deduplication_key = ["posisi", "perusahaan", "kota", "deskripsi_lengkap"]
    clean = clean.drop_duplicates(subset=deduplication_key, keep="first").reset_index(drop=True)
    clean.insert(0, "job_id", [f"ID-JOB-{index:05d}" for index in range(1, len(clean) + 1)])

    report = build_quality_report(raw, clean)
    return clean, report


def run(input_path: Path, output_path: Path, report_path: Path) -> dict[str, Any]:
    """Read the source file and persist reproducible pipeline outputs."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input dataset not found: {input_path}")

    raw = pd.read_csv(input_path)
    clean, report = prepare_jobs(raw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output_path, index=False)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    run(args.input, args.output, args.report)
    print("Data preparation completed; inspect the configured report artifact for aggregate metrics.")


if __name__ == "__main__":
    main()

