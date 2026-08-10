"""Command-line interface for explainable CV-to-job matching."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import CVJobMatcher


def _read_text(value: str | None, path: Path | None, label: str) -> str:
    if value:
        return value
    if path:
        return path.read_text(encoding="utf-8")
    raise ValueError(f"Provide either --{label}-text or --{label}-file")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cv-text")
    parser.add_argument("--cv-file", type=Path)
    parser.add_argument("--job-text")
    parser.add_argument("--job-file", type=Path)
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    cv_text = _read_text(args.cv_text, args.cv_file, "cv")
    job_text = _read_text(args.job_text, args.job_file, "job")
    report = CVJobMatcher().match(cv_text, job_text).to_dict()
    payload = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
