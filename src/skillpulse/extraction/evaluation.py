"""Evaluate the extraction baseline against weak labels and reviewed gold annotations."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from .annotation_quality import validate_annotation_frame
from .engine import EntityExtractor


def _split_labels(value: Any) -> list[str]:
    if pd.isna(value) or str(value).strip().lower() == "tidak ada tools spesifik":
        return []
    return [item.strip() for item in re.split(r"[,;/|]", str(value)) if item.strip()]


def _split_gold_labels(value: Any) -> set[str]:
    if pd.isna(value):
        return set()
    return {item.strip() for item in str(value).split("|") if item.strip()}


def _normalize_scalar(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_years(value: Any) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return ""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value).strip()


def _metric_counts(predicted: set[str], expected: set[str]) -> tuple[int, int, int]:
    return len(predicted & expected), len(predicted - expected), len(expected - predicted)


def _alias_lookup(extractor: EntityExtractor) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for entity in extractor.skills:
        lookup[entity["canonical"].casefold()] = entity["canonical"]
        for alias in entity["aliases"]:
            lookup[alias.casefold()] = entity["canonical"]
    return lookup


def evaluate(frame: pd.DataFrame, extractor: EntityExtractor) -> dict[str, Any]:
    """Calculate micro set metrics on ground-truth labels covered by the taxonomy."""
    lookup = _alias_lookup(extractor)
    tp = fp = fn = covered_labels = all_labels = 0
    exact_documents = 0
    evaluated_documents = 0

    for _, row in frame.iterrows():
        raw_labels = _split_labels(row.get("tools"))
        all_labels += len(raw_labels)
        expected = {lookup[label.casefold()] for label in raw_labels if label.casefold() in lookup}
        covered_labels += len(expected)
        if not expected:
            continue

        text = f"{row.get('posisi', '')}. {row.get('deskripsi_lengkap', '')}"
        result = extractor.extract(text)
        predicted = {match.canonical for match in result.technical_skills + result.tools}
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
        exact_documents += int(predicted == expected)
        evaluated_documents += 1

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "evaluation_type": "weak-label baseline; manual gold review still required",
        "documents_total": int(len(frame)),
        "documents_evaluated": evaluated_documents,
        "taxonomy_label_coverage": round(covered_labels / all_labels, 4) if all_labels else 0.0,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "document_exact_match": round(exact_documents / evaluated_documents, 4) if evaluated_documents else 0.0,
    }


def create_annotation_sample(frame: pd.DataFrame, output: Path, size: int = 100) -> None:
    """Create a deterministic, review-ready sample without claiming it is gold data."""
    sample = frame.sample(n=min(size, len(frame)), random_state=42).copy()
    annotation = pd.DataFrame(
        {
            "source_row": sample.index,
            "text": sample["posisi"].fillna("") + ". " + sample["deskripsi_lengkap"].fillna(""),
            "weak_tools": sample["tools"],
            "weak_experience_years": sample["pengalaman"],
            "weak_seniority": sample["level"],
            "gold_technical_skills": "",
            "gold_tools": "",
            "gold_soft_skills": "",
            "gold_education": "",
            "gold_experience_years": "",
            "gold_seniority": "",
            "gold_work_arrangement": "",
            "review_status": "needs_review",
            "annotator": "",
            "notes": "",
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    annotation.to_csv(output, index=False)


def evaluate_gold_annotations(frame: pd.DataFrame, extractor: EntityExtractor) -> dict[str, Any]:
    """Score reviewed gold annotations across each extracted field."""
    reviewed = frame[frame["review_status"].fillna("").str.strip().eq("reviewed")].copy()
    if reviewed.empty:
        return {
            "evaluation_type": "gold-set evaluation",
            "documents_reviewed": 0,
            "message": "No reviewed annotations yet. Mark rows as reviewed in data/annotations/gold_sample.csv.",
        }

    entity_fields = {
        "technical_skills": "gold_technical_skills",
        "tools": "gold_tools",
        "soft_skills": "gold_soft_skills",
        "education": "gold_education",
    }
    metrics: dict[str, dict[str, float | int]] = {}

    for field, column in entity_fields.items():
        tp = fp = fn = exact = 0
        for _, row in reviewed.iterrows():
            result = extractor.extract(row["text"])
            predicted_value = getattr(result, field)
            if field == "education":
                predicted = set(predicted_value)
            else:
                predicted = {item.canonical for item in predicted_value}
            expected = _split_gold_labels(row[column])
            current_tp, current_fp, current_fn = _metric_counts(predicted, expected)
            tp += current_tp
            fp += current_fp
            fn += current_fn
            exact += int(predicted == expected)

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        metrics[field] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "exact_match": round(exact / len(reviewed), 4),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
        }

    experience_exact = 0
    seniority_exact = 0
    work_arrangement_exact = 0
    for _, row in reviewed.iterrows():
        result = extractor.extract(row["text"])
        gold_years = _normalize_years(row["gold_experience_years"])
        if result.experience_years is None:
            predicted_years = ""
        else:
            predicted_years = f"{result.experience_years:g}"
        experience_exact += int(predicted_years == gold_years)
        seniority_exact += int(result.seniority == _normalize_scalar(row["gold_seniority"]))
        work_arrangement_exact += int(result.work_arrangement == _normalize_scalar(row["gold_work_arrangement"]))

    metrics["experience_years"] = {"exact_match": round(experience_exact / len(reviewed), 4)}
    metrics["seniority"] = {"exact_match": round(seniority_exact / len(reviewed), 4)}
    metrics["work_arrangement"] = {"exact_match": round(work_arrangement_exact / len(reviewed), 4)}
    return {
        "evaluation_type": "gold-set evaluation",
        "documents_reviewed": int(len(reviewed)),
        "metrics": metrics,
    }


def analyze_annotation_errors(
    frame: pd.DataFrame,
    extractor: EntityExtractor,
    review_status: str = "ai_reviewed",
    max_examples: int = 10,
) -> dict[str, Any]:
    """Summarize label-level errors for one explicitly selected review status."""
    selected = frame[frame["review_status"].fillna("").str.strip().eq(review_status)].copy()
    if selected.empty:
        return {"documents_analyzed": 0, "entity_errors": {}, "scalar_errors": {}}

    extracted = [(row, extractor.extract(row["text"])) for _, row in selected.iterrows()]
    entity_fields = {
        "technical_skills": "gold_technical_skills",
        "tools": "gold_tools",
        "soft_skills": "gold_soft_skills",
        "education": "gold_education",
    }
    entity_errors: dict[str, Any] = {}
    for field, column in entity_fields.items():
        false_positives: Counter[str] = Counter()
        false_negatives: Counter[str] = Counter()
        examples: list[dict[str, Any]] = []
        for row, result in extracted:
            predicted_value = getattr(result, field)
            predicted = set(predicted_value) if field == "education" else {item.canonical for item in predicted_value}
            expected = _split_gold_labels(row[column])
            current_fp = sorted(predicted - expected)
            current_fn = sorted(expected - predicted)
            false_positives.update(current_fp)
            false_negatives.update(current_fn)
            if (current_fp or current_fn) and len(examples) < max_examples:
                examples.append(
                    {
                        "source_row": str(row.get("source_row", "")),
                        "false_positives": current_fp,
                        "false_negatives": current_fn,
                    }
                )
        entity_errors[field] = {
            "false_positives": [{"label": label, "count": count} for label, count in false_positives.most_common()],
            "false_negatives": [{"label": label, "count": count} for label, count in false_negatives.most_common()],
            "examples": examples,
        }

    scalar_fields = {
        "experience_years": "gold_experience_years",
        "seniority": "gold_seniority",
        "work_arrangement": "gold_work_arrangement",
    }
    scalar_errors: dict[str, Any] = {}
    for field, column in scalar_fields.items():
        mismatch_count = 0
        examples = []
        for row, result in extracted:
            predicted_value = getattr(result, field)
            if field == "experience_years":
                predicted = "" if predicted_value is None else f"{predicted_value:g}"
            else:
                predicted = str(predicted_value)
            expected = _normalize_years(row[column]) if field == "experience_years" else _normalize_scalar(row[column])
            if predicted != expected:
                mismatch_count += 1
                if len(examples) < max_examples:
                    examples.append(
                        {
                            "source_row": str(row.get("source_row", "")),
                            "predicted": predicted,
                            "expected": expected,
                        }
                    )
        scalar_errors[field] = {"mismatches": mismatch_count, "examples": examples}

    return {
        "documents_analyzed": int(len(selected)),
        "entity_errors": entity_errors,
        "scalar_errors": scalar_errors,
    }


def evaluate_ai_assisted_annotations(frame: pd.DataFrame, extractor: EntityExtractor) -> dict[str, Any]:
    """Evaluate AI-assisted labels without presenting them as human gold."""
    provisional = frame.copy()
    included = provisional["review_status"].fillna("").str.strip().eq("ai_reviewed")
    provisional["review_status"] = included.map({True: "reviewed", False: "excluded"})
    report = evaluate_gold_annotations(provisional, extractor)
    documents = int(report.pop("documents_reviewed", 0))
    report.update(
        {
            "evaluation_type": "AI-assisted provisional evaluation",
            "claim_status": "not_human_gold",
            "review_status_included": "ai_reviewed",
            "documents_evaluated": documents,
            "annotation_quality": validate_annotation_frame(frame, extractor),
            "error_analysis": analyze_annotation_errors(frame, extractor),
        }
    )
    if documents == 0:
        report["message"] = "No ai_reviewed annotations are available."
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("lowongan data dan analytics jobstreet.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/extraction_baseline.json"))
    parser.add_argument("--annotations", type=Path, default=Path("data/annotations/gold_sample.csv"))
    parser.add_argument("--gold-report", type=Path, default=Path("reports/extraction_gold_eval.json"))
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--recreate-annotations", action="store_true")
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    extractor = EntityExtractor()
    report = evaluate(frame, extractor)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.recreate_annotations or not args.annotations.exists():
        create_annotation_sample(frame, args.annotations, args.sample_size)
    gold_frame = pd.read_csv(args.annotations)
    gold_report = evaluate_gold_annotations(gold_frame, extractor)
    args.gold_report.parent.mkdir(parents=True, exist_ok=True)
    args.gold_report.write_text(json.dumps(gold_report, indent=2), encoding="utf-8")
    print(json.dumps({"weak_label_report": report, "gold_report": gold_report}, indent=2))


if __name__ == "__main__":
    main()
