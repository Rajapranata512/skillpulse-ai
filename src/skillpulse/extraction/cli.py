"""Command-line extraction helpers for SkillPulse AI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .agreement import evaluate_annotation_agreement, write_blind_second_annotation_batch
from .engine import EntityExtractor
from .evaluation import evaluate_ai_assisted_annotations, evaluate_gold_annotations
from .review import REVIEW_STATUSES, write_annotation_review_pack
from .review_batch import (
    append_audit_log,
    create_review_batch,
    import_human_review_batch,
    write_csv_atomic,
)


def extract_text(text: str) -> dict[str, object]:
    return EntityExtractor().extract(text).to_dict()


def extract_csv(input_path: Path, output_path: Path, text_column: str = "deskripsi_lengkap") -> None:
    frame = pd.read_csv(input_path)
    if text_column not in frame.columns:
        raise ValueError(f"Column '{text_column}' not found in {input_path}")

    extractor = EntityExtractor()
    enriched = frame.copy()
    enriched["extracted_technical_skills"] = (
        frame[text_column]
        .fillna("")
        .map(lambda text: "|".join(item.canonical for item in extractor.extract(str(text)).technical_skills))
    )
    enriched["extracted_tools"] = (
        frame[text_column]
        .fillna("")
        .map(lambda text: "|".join(item.canonical for item in extractor.extract(str(text)).tools))
    )
    enriched["extracted_soft_skills"] = (
        frame[text_column]
        .fillna("")
        .map(lambda text: "|".join(item.canonical for item in extractor.extract(str(text)).soft_skills))
    )
    enriched["extracted_education"] = (
        frame[text_column].fillna("").map(lambda text: "|".join(extractor.extract(str(text)).education))
    )
    enriched["extracted_experience_years"] = (
        frame[text_column].fillna("").map(lambda text: extractor.extract(str(text)).experience_years)
    )
    enriched["extracted_seniority"] = (
        frame[text_column].fillna("").map(lambda text: extractor.extract(str(text)).seniority)
    )
    enriched["extracted_work_arrangement"] = (
        frame[text_column].fillna("").map(lambda text: extractor.extract(str(text)).work_arrangement)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    text_parser = subparsers.add_parser("text", help="Extract entities from one text string")
    text_parser.add_argument("value", help="Input job description or CV text")

    csv_parser = subparsers.add_parser("csv", help="Extract entities for every row in a CSV column")
    csv_parser.add_argument("--input", type=Path, default=Path("lowongan data dan analytics jobstreet.csv"))
    csv_parser.add_argument("--output", type=Path, default=Path("data/processed/jobs_with_extraction.csv"))
    csv_parser.add_argument("--text-column", default="deskripsi_lengkap")

    gold_parser = subparsers.add_parser("gold", help="Score reviewed gold annotations")
    gold_parser.add_argument("--annotations", type=Path, default=Path("data/annotations/gold_sample.csv"))

    provisional_parser = subparsers.add_parser(
        "provisional", help="Score AI-assisted labels without claiming human gold"
    )
    provisional_parser.add_argument("--annotations", type=Path, default=Path("data/annotations/gold_sample.csv"))
    provisional_parser.add_argument("--output", type=Path, default=Path("reports/extraction_ai_assisted_eval.json"))

    review_parser = subparsers.add_parser("review-pack", help="Build a read-only HTML annotation review pack")
    review_parser.add_argument("--annotations", type=Path, default=Path("data/annotations/gold_sample.csv"))
    review_parser.add_argument("--output", type=Path, default=Path("reports/annotation_review_pack.html"))
    review_parser.add_argument("--status", choices=sorted(REVIEW_STATUSES), default="ai_reviewed")

    batch_parser = subparsers.add_parser(
        "review-batch", help="Export an editable, fingerprinted human-review CSV"
    )
    batch_parser.add_argument("--annotations", type=Path, default=Path("data/annotations/gold_sample.csv"))
    batch_parser.add_argument(
        "--output", type=Path, default=Path("data/annotations/review_batch_remaining.csv")
    )
    batch_parser.add_argument("--status", choices=sorted(REVIEW_STATUSES), default="needs_review")

    import_parser = subparsers.add_parser(
        "review-import", help="Validate and merge explicitly completed human-review rows"
    )
    import_parser.add_argument("--annotations", type=Path, default=Path("data/annotations/gold_sample.csv"))
    import_parser.add_argument("--batch", type=Path, default=Path("data/annotations/review_batch_remaining.csv"))
    import_parser.add_argument("--output", type=Path, required=True)
    import_parser.add_argument("--audit-log", type=Path, default=Path("data/annotations/review_log.csv"))
    import_parser.add_argument("--review-date")
    import_parser.add_argument(
        "--confirm-human-review",
        action="store_true",
        help="Attest that a human checked every row marked reviewed in the batch",
    )

    agreement_batch_parser = subparsers.add_parser(
        "agreement-batch", help="Export a blind CSV for an independent second annotator"
    )
    agreement_batch_parser.add_argument(
        "--primary", type=Path, default=Path("data/annotations/gold_sample.csv")
    )
    agreement_batch_parser.add_argument(
        "--output", type=Path, default=Path("data/annotations/second_annotator_blind.csv")
    )

    agreement_parser = subparsers.add_parser(
        "agreement", help="Evaluate blind primary-secondary annotation agreement"
    )
    agreement_parser.add_argument(
        "--primary", type=Path, default=Path("data/annotations/gold_sample.csv")
    )
    agreement_parser.add_argument(
        "--secondary", type=Path, default=Path("data/annotations/second_annotator_blind.csv")
    )
    agreement_parser.add_argument(
        "--output", type=Path, default=Path("reports/annotation_agreement.json")
    )
    agreement_parser.add_argument("--minimum-documents", type=int, default=100)
    args = parser.parse_args()

    if args.command == "text":
        print(json.dumps(extract_text(args.value), indent=2))
        return

    if args.command == "csv":
        extract_csv(args.input, args.output, args.text_column)
        print(json.dumps({"output": str(args.output), "rows_processed": len(pd.read_csv(args.output))}, indent=2))
        return

    if args.command == "review-pack":
        frame = pd.read_csv(args.annotations)
        rows = write_annotation_review_pack(frame, args.output, status=args.status)
        print(json.dumps({"output": str(args.output), "rows_included": rows, "status": args.status}, indent=2))
        return

    if args.command == "review-batch":
        frame = pd.read_csv(args.annotations, dtype=str, keep_default_na=False)
        batch = create_review_batch(frame, status=args.status)
        write_csv_atomic(batch, args.output)
        print(json.dumps({"output": str(args.output), "rows_included": len(batch), "status": args.status}, indent=2))
        return

    if args.command == "review-import":
        if not args.confirm_human_review:
            parser.error("review-import requires --confirm-human-review after real human verification")
        annotations = pd.read_csv(args.annotations, dtype=str, keep_default_na=False)
        batch = pd.read_csv(args.batch, dtype=str, keep_default_na=False)
        result = import_human_review_batch(
            annotations,
            batch,
            human_review_confirmed=True,
            reviewed_at=args.review_date,
        )
        write_csv_atomic(result.annotations, args.output)
        append_audit_log(args.audit_log, result.audit_log)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "audit_log": str(args.audit_log),
                    "rows_applied": result.rows_applied,
                    "quality_valid": result.quality_report["valid"],
                    "status_counts": result.quality_report["status_counts"],
                },
                indent=2,
            )
        )
        return

    if args.command == "agreement-batch":
        primary = pd.read_csv(args.primary, dtype=str, keep_default_na=False)
        rows = write_blind_second_annotation_batch(primary, args.output)
        print(json.dumps({"output": str(args.output), "rows_included": rows, "blind": True}, indent=2))
        return

    if args.command == "agreement":
        primary = pd.read_csv(args.primary, dtype=str, keep_default_na=False)
        secondary = pd.read_csv(args.secondary, dtype=str, keep_default_na=False)
        report = evaluate_annotation_agreement(
            primary, secondary, minimum_documents=args.minimum_documents
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    frame = pd.read_csv(args.annotations)
    if args.command == "provisional":
        report = evaluate_ai_assisted_annotations(frame, EntityExtractor())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        report = evaluate_gold_annotations(frame, EntityExtractor())
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
