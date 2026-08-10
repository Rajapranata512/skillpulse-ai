"""Public-safe relevance benchmark scaffold for the explainable matcher."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .engine import CVJobMatcher


@dataclass(frozen=True)
class RoleSpec:
    title: str
    technical: tuple[str, ...]
    tools: tuple[str, ...]
    soft: tuple[str, ...]
    education: str
    experience: int
    seniority: str
    arrangement: str


ROLE_SPECS = (
    RoleSpec(
        "Data Analyst",
        ("Python", "SQL", "Data Analysis"),
        ("Excel", "Tableau"),
        ("Communication",),
        "Bachelor",
        2,
        "mid",
        "hybrid",
    ),
    RoleSpec(
        "BI Analyst",
        ("SQL", "Data Visualization"),
        ("Power BI", "SQL Server"),
        ("Presentation",),
        "Bachelor",
        3,
        "mid",
        "onsite",
    ),
    RoleSpec(
        "Data Engineer",
        ("Python", "SQL", "ETL"),
        ("Apache Airflow", "Apache Spark", "Docker"),
        ("Problem Solving",),
        "Bachelor",
        4,
        "senior",
        "hybrid",
    ),
    RoleSpec(
        "Machine Learning Engineer",
        ("Python", "Machine Learning", "REST API"),
        ("PyTorch", "Docker", "Git"),
        ("Problem Solving",),
        "Bachelor",
        3,
        "mid",
        "remote",
    ),
    RoleSpec(
        "NLP Engineer",
        ("Python", "NLP", "Machine Learning"),
        ("PyTorch", "Docker"),
        ("Communication",),
        "Master",
        3,
        "mid",
        "remote",
    ),
    RoleSpec(
        "Product Analyst",
        ("SQL", "Statistics", "Data Analysis"),
        ("Google Analytics", "Tableau"),
        ("Communication", "Presentation"),
        "Bachelor",
        2,
        "mid",
        "hybrid",
    ),
    RoleSpec(
        "Marketing Analyst",
        ("SQL", "Data Analysis"),
        ("Excel", "Google Analytics", "Looker Studio"),
        ("Presentation",),
        "Bachelor",
        2,
        "mid",
        "onsite",
    ),
    RoleSpec(
        "Data Scientist",
        ("Python", "R", "Machine Learning", "Statistics"),
        ("Scikit-learn", "Pandas"),
        ("Critical Thinking",),
        "Bachelor",
        3,
        "mid",
        "hybrid",
    ),
    RoleSpec(
        "Analytics Engineer",
        ("SQL", "ETL", "Data Visualization"),
        ("BigQuery", "Git", "Apache Airflow"),
        ("Problem Solving",),
        "Bachelor",
        3,
        "mid",
        "remote",
    ),
    RoleSpec(
        "Junior Reporting Analyst",
        ("SQL", "Data Visualization"),
        ("Excel", "Power BI"),
        ("Communication",),
        "Bachelor",
        0,
        "entry",
        "onsite",
    ),
)
RELEVANCE_COLUMNS = (
    "pair_id",
    "job_group_id",
    "cv_text",
    "job_text",
    "cv_sha256",
    "job_sha256",
    "human_relevance_score",
    "human_rationale",
    "review_status",
    "annotator",
    "notes",
)
REVIEW_STATUSES = {"needs_review", "reviewed"}
AI_RELEVANCE_COLUMNS = (
    "pair_id",
    "ai_relevance_score",
    "ai_rationale",
    "annotator",
    "review_status",
    "notes",
)
SCENARIOS = ("complete", "mostly", "partial", "adjacent", "mismatch")
SCENARIO_SCORES = {"complete": 4, "mostly": 3, "partial": 2, "adjacent": 1, "mismatch": 0}
SCENARIO_RATIONALES = {
    "complete": "Synthetic CV includes every explicit job requirement.",
    "mostly": "Synthetic CV covers most requirements with small skill and experience gaps.",
    "partial": "Synthetic CV covers only a limited subset of the explicit requirements.",
    "adjacent": "Synthetic CV has adjacent analytics capability but limited role-specific evidence.",
    "mismatch": "Synthetic CV intentionally uses a different technical profile.",
}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _joined(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none stated"


def _seniority_text(value: str) -> str:
    return {"entry": "Junior", "mid": "Mid-level", "senior": "Senior"}[value]


def _job_text(role: RoleSpec) -> str:
    experience = (
        "Fresh graduates are eligible" if role.experience == 0 else f"Requires {role.experience} years experience"
    )
    return (
        f"{role.title}. {_seniority_text(role.seniority)} role. {experience}. "
        f"Required technical skills: {_joined(role.technical)}. "
        f"Required tools: {_joined(role.tools)}. "
        f"Required soft skills: {_joined(role.soft)}. Minimum {role.education} degree. "
        f"This is a {role.arrangement} position."
    )


def _cv_text(role: RoleSpec, scenario: str) -> str:
    if scenario == "complete":
        technical, tools, soft = role.technical, role.tools, role.soft
        education, experience = role.education, role.experience
        seniority, arrangement = role.seniority, role.arrangement
    elif scenario == "mostly":
        technical = role.technical[:-1] or role.technical
        tools = role.tools[:-1] or role.tools
        soft = role.soft[:1]
        education, experience = role.education, max(role.experience - 1, 0)
        seniority, arrangement = role.seniority, role.arrangement
    elif scenario == "partial":
        technical, tools, soft = role.technical[:1], role.tools[:1], ()
        education, experience = "Diploma", max(role.experience // 2, 0)
        seniority, arrangement = "entry", role.arrangement
    elif scenario == "adjacent":
        technical, tools, soft = ("Data Analysis", "Statistics"), ("Excel",), ("Communication",)
        education, experience = "Bachelor", 1
        seniority, arrangement = "entry", "onsite"
    elif scenario == "mismatch":
        technical, tools, soft = ("JavaScript", "Go"), ("Git",), ("Teamwork",)
        education, experience = "High School", 1
        seniority, arrangement = "entry", "onsite"
    else:
        raise ValueError(f"Unknown synthetic scenario: {scenario}")

    experience_text = "Fresh graduate" if experience == 0 else f"{experience} years experience"
    return (
        f"{_seniority_text(seniority)} candidate with {experience_text}. "
        f"Technical skills: {_joined(technical)}. Tools: {_joined(tools)}. "
        f"Soft skills: {_joined(soft)}. Education: {education}. "
        f"Prefers {arrangement} work."
    )


def create_relevance_candidate_set() -> pd.DataFrame:
    """Create 50 synthetic CV-job pairs without embedding intended relevance labels."""
    records: list[dict[str, str]] = []
    pair_number = 1
    for role_index, role in enumerate(ROLE_SPECS, start=1):
        rotated = SCENARIOS[role_index % len(SCENARIOS) :] + SCENARIOS[: role_index % len(SCENARIOS)]
        job = _job_text(role)
        for scenario in rotated:
            cv = _cv_text(role, scenario)
            records.append(
                {
                    "pair_id": f"pair_{pair_number:03d}",
                    "job_group_id": f"job_{role_index:02d}",
                    "cv_text": cv,
                    "job_text": job,
                    "cv_sha256": _digest(cv),
                    "job_sha256": _digest(job),
                    "human_relevance_score": "",
                    "human_rationale": "",
                    "review_status": "needs_review",
                    "annotator": "",
                    "notes": "",
                }
            )
            pair_number += 1
    return pd.DataFrame(records, columns=RELEVANCE_COLUMNS)


def _require_columns(frame: pd.DataFrame) -> None:
    missing = sorted(set(RELEVANCE_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing relevance columns: {', '.join(missing)}")


def _spearman(first: list[float], second: list[float]) -> float | None:
    if len(first) < 2 or len(set(first)) < 2 or len(set(second)) < 2:
        return None
    first_rank = pd.Series(first, dtype=float).rank(method="average")
    second_rank = pd.Series(second, dtype=float).rank(method="average")
    value = first_rank.corr(second_rank)
    return None if pd.isna(value) else round(float(value), 4)


def evaluate_relevance_baseline(
    frame: pd.DataFrame,
    matcher: CVJobMatcher | None = None,
    *,
    minimum_pairs: int = 50,
) -> dict[str, Any]:
    """Evaluate matcher v0.1 only on explicitly human-reviewed synthetic pairs."""
    if minimum_pairs < 1:
        raise ValueError("minimum_pairs must be positive")
    _require_columns(frame)
    if frame["pair_id"].astype(str).duplicated().any():
        raise ValueError("pair_id must be unique")
    invalid_statuses = sorted(set(frame["review_status"].fillna("").str.strip()) - REVIEW_STATUSES)
    if invalid_statuses:
        raise ValueError(f"Invalid relevance review statuses: {', '.join(invalid_statuses)}")
    for _, row in frame.iterrows():
        if _digest(str(row["cv_text"])) != str(row["cv_sha256"]).strip():
            raise ValueError(f"CV text fingerprint changed for {row['pair_id']}.")
        if _digest(str(row["job_text"])) != str(row["job_sha256"]).strip():
            raise ValueError(f"Job text fingerprint changed for {row['pair_id']}.")

    reviewed = frame[frame["review_status"].fillna("").str.strip().eq("reviewed")].copy()
    scores: list[int] = []
    for _, row in reviewed.iterrows():
        value = str(row["human_relevance_score"]).strip()
        try:
            numeric = float(value)
        except ValueError as error:
            raise ValueError(f"Invalid human relevance score for {row['pair_id']}.") from error
        if not numeric.is_integer() or not 0 <= numeric <= 4:
            raise ValueError(f"Human relevance score must be an integer 0-4 for {row['pair_id']}.")
        if not str(row["annotator"]).strip() or not str(row["human_rationale"]).strip():
            raise ValueError(f"Annotator and rationale are required for {row['pair_id']}.")
        scores.append(int(numeric))

    engine = matcher or CVJobMatcher()
    model_scores: list[float] = []
    model_verdicts: list[str] = []
    latencies_ms: list[float] = []
    explanation_complete = 0
    for _, row in reviewed.iterrows():
        started = time.perf_counter()
        result = engine.match(str(row["cv_text"]), str(row["job_text"]))
        latencies_ms.append((time.perf_counter() - started) * 1000)
        model_scores.append(result.overall_score)
        model_verdicts.append(result.verdict)
        explanation_complete += int(bool(result.category_scores and result.disclaimer))

    normalized_human = [score * 25.0 for score in scores]
    human_verdicts = [
        "strong_match" if score == 4 else "potential_match" if score >= 2 else "skill_gap" for score in scores
    ]
    group_correlations: dict[str, float | None] = {}
    for group_id, group in reviewed.assign(_human=scores, _model=model_scores).groupby("job_group_id"):
        group_correlations[str(group_id)] = _spearman(
            group["_human"].astype(float).tolist(), group["_model"].astype(float).tolist()
        )
    category_error: dict[str, dict[str, float | int]] = {}
    for score in range(5):
        indices = [index for index, value in enumerate(scores) if value == score]
        if indices:
            category_error[str(score)] = {
                "pairs": len(indices),
                "mean_model_score": round(sum(model_scores[index] for index in indices) / len(indices), 2),
                "mae_to_human_scale": round(
                    sum(abs(model_scores[index] - normalized_human[index]) for index in indices) / len(indices), 2
                ),
            }

    annotators = sorted({str(value).strip() for value in reviewed["annotator"] if str(value).strip()})
    enough_pairs = len(reviewed) >= minimum_pairs
    enough_groups = reviewed["job_group_id"].nunique() >= len(ROLE_SPECS)
    rationale_complete = reviewed["human_rationale"].fillna("").str.strip().ne("").all()
    return {
        "evaluation_type": "human relevance evaluation of exact-taxonomy matcher v0.1",
        "claim_status": "baseline_only_semantic_challenger_not_evaluated",
        "pairs_available": len(frame),
        "pairs_reviewed": len(reviewed),
        "job_groups_reviewed": int(reviewed["job_group_id"].nunique()),
        "minimum_pairs": minimum_pairs,
        "annotators": annotators,
        "ready_for_baseline_evaluation": bool(enough_pairs and enough_groups and rationale_complete),
        "ready_for_ml_qg_3": False,
        "metrics": {
            "spearman_global": _spearman([float(value) for value in scores], model_scores),
            "spearman_by_job_group": group_correlations,
            "mae_on_0_100_scale": (
                round(
                    sum(abs(model - human) for model, human in zip(model_scores, normalized_human, strict=True))
                    / len(scores),
                    2,
                )
                if scores
                else None
            ),
            "verdict_accuracy": (
                round(
                    sum(left == right for left, right in zip(model_verdicts, human_verdicts, strict=True))
                    / len(scores),
                    4,
                )
                if scores
                else None
            ),
            "category_level_error": category_error,
            "latency_ms_p50": round(float(pd.Series(latencies_ms).quantile(0.50)), 3) if latencies_ms else None,
            "latency_ms_p95": round(float(pd.Series(latencies_ms).quantile(0.95)), 3) if latencies_ms else None,
            "explanation_completeness": round(explanation_complete / len(reviewed), 4) if len(reviewed) else None,
        },
        "warnings": [
            "Pairs are synthetic and cover only taxonomy-supported requirements.",
            "ML-QG-3 remains open until a semantic challenger is compared on the same frozen human labels.",
        ],
    }


def create_ai_relevance_labels() -> pd.DataFrame:
    """Create deterministic synthetic-oracle labels without touching human-review columns."""
    records: list[dict[str, str | int]] = []
    pair_number = 1
    for role_index, _role in enumerate(ROLE_SPECS, start=1):
        rotated = SCENARIOS[role_index % len(SCENARIOS) :] + SCENARIOS[: role_index % len(SCENARIOS)]
        for scenario in rotated:
            records.append(
                {
                    "pair_id": f"pair_{pair_number:03d}",
                    "ai_relevance_score": SCENARIO_SCORES[scenario],
                    "ai_rationale": SCENARIO_RATIONALES[scenario],
                    "annotator": "synthetic_scenario_oracle_v1",
                    "review_status": "ai_reviewed",
                    "notes": f"Designed scenario: {scenario}; not a human judgment.",
                }
            )
            pair_number += 1
    return pd.DataFrame(records, columns=AI_RELEVANCE_COLUMNS)


def evaluate_ai_relevance_baseline(
    candidates: pd.DataFrame,
    labels: pd.DataFrame,
    matcher: CVJobMatcher | None = None,
    *,
    minimum_pairs: int = 50,
) -> dict[str, Any]:
    """Evaluate v0.1 against synthetic-oracle labels without claiming ML-QG-3."""
    _require_columns(candidates)
    missing = sorted(set(AI_RELEVANCE_COLUMNS) - set(labels.columns))
    if missing:
        raise ValueError(f"Missing AI relevance columns: {', '.join(missing)}")
    if candidates["pair_id"].astype(str).duplicated().any() or labels["pair_id"].astype(str).duplicated().any():
        raise ValueError("pair_id must be unique in candidates and AI labels")
    candidate_ids = set(candidates["pair_id"].astype(str))
    label_ids = set(labels["pair_id"].astype(str))
    if candidate_ids != label_ids:
        raise ValueError("AI label pair_id set must exactly match the candidate set")
    if not labels["review_status"].astype(str).eq("ai_reviewed").all():
        raise ValueError("AI labels must use review_status=ai_reviewed")
    if labels["annotator"].fillna("").astype(str).str.strip().eq("").any():
        raise ValueError("AI labels require explicit synthetic annotator provenance")
    if labels["ai_rationale"].fillna("").astype(str).str.strip().eq("").any():
        raise ValueError("AI labels require a rationale for every pair")

    working = candidates.copy()
    indexed = labels.set_index(labels["pair_id"].astype(str), drop=False)
    for row_index, pair_id in working["pair_id"].astype(str).items():
        label = indexed.loc[pair_id]
        score = str(label["ai_relevance_score"]).strip()
        try:
            numeric = float(score)
        except ValueError as error:
            raise ValueError(f"Invalid AI relevance score for {pair_id}") from error
        if not numeric.is_integer() or not 0 <= numeric <= 4:
            raise ValueError(f"AI relevance score must be an integer 0-4 for {pair_id}")
        working.at[row_index, "human_relevance_score"] = str(int(numeric))
        working.at[row_index, "human_rationale"] = str(label["ai_rationale"])
        working.at[row_index, "review_status"] = "reviewed"
        working.at[row_index, "annotator"] = str(label["annotator"])
        working.at[row_index, "notes"] = str(label["notes"])

    report = evaluate_relevance_baseline(working, matcher=matcher, minimum_pairs=minimum_pairs)
    experimental_ready = report["ready_for_baseline_evaluation"]
    report["evaluation_type"] = "synthetic-oracle relevance evaluation of exact-taxonomy matcher v0.1"
    report["claim_status"] = "ai_pseudo_labels_not_human_ml_qg_3"
    report["ready_for_experimental_comparison"] = experimental_ready
    report["ready_for_baseline_evaluation"] = False
    report["ready_for_ml_qg_3"] = False
    report["warnings"].insert(
        0,
        "Scores encode the synthetic scenario design; they are not independent human relevance judgments.",
    )
    return report
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create", help="Create 50 unlabeled synthetic pairs")
    create_parser.add_argument("--output", type=Path, default=Path("data/evaluation/matching_relevance_candidates.csv"))
    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate human-reviewed pairs")
    evaluate_parser.add_argument(
        "--input", type=Path, default=Path("data/evaluation/matching_relevance_candidates.csv")
    )
    evaluate_parser.add_argument("--output", type=Path, default=Path("reports/matching_relevance_baseline.json"))
    evaluate_parser.add_argument("--minimum-pairs", type=int, default=50)
    create_ai_parser = subparsers.add_parser(
        "create-ai-labels", help="Create deterministic synthetic-oracle labels in a separate file"
    )
    create_ai_parser.add_argument(
        "--output", type=Path, default=Path("data/evaluation/matching_relevance_ai_labels.csv")
    )
    evaluate_ai_parser = subparsers.add_parser(
        "evaluate-ai", help="Evaluate matcher v0.1 against synthetic-oracle labels"
    )
    evaluate_ai_parser.add_argument(
        "--candidates", type=Path, default=Path("data/evaluation/matching_relevance_candidates.csv")
    )
    evaluate_ai_parser.add_argument(
        "--labels", type=Path, default=Path("data/evaluation/matching_relevance_ai_labels.csv")
    )
    evaluate_ai_parser.add_argument(
        "--output", type=Path, default=Path("reports/matching_relevance_ai_baseline.json")
    )
    evaluate_ai_parser.add_argument("--minimum-pairs", type=int, default=50)
    semantic_parser = subparsers.add_parser(
        "evaluate-semantic", help="Compare exact-taxonomy baseline with multilingual semantic hybrid"
    )
    semantic_parser.add_argument(
        "--candidates", type=Path, default=Path("data/evaluation/matching_relevance_candidates.csv")
    )
    semantic_parser.add_argument(
        "--labels", type=Path, default=Path("data/evaluation/matching_relevance_ai_labels.csv")
    )
    semantic_parser.add_argument(
        "--output", type=Path, default=Path("reports/matching_semantic_challenger.json")
    )
    semantic_parser.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    semantic_parser.add_argument("--semantic-weight", type=float, default=0.20)
    semantic_parser.add_argument("--minimum-pairs", type=int, default=50)
    args = parser.parse_args()

    if args.command == "create":
        frame = create_relevance_candidate_set()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(args.output, index=False)
        print(json.dumps({"output": str(args.output), "pairs_created": len(frame), "synthetic": True}, indent=2))
        return
    if args.command == "create-ai-labels":
        frame = create_ai_relevance_labels()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(args.output, index=False)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "pairs_labeled": len(frame),
                    "claim_status": "synthetic_oracle_not_human",
                },
                indent=2,
            )
        )
        return
    if args.command == "evaluate-semantic":
        from .semantic import SemanticHybridMatcher, SentenceTransformerEmbedder, evaluate_semantic_challenger

        candidates = pd.read_csv(args.candidates, dtype=str, keep_default_na=False)
        labels = pd.read_csv(args.labels, dtype=str, keep_default_na=False)
        matcher = SemanticHybridMatcher(
            embedder=SentenceTransformerEmbedder(args.model),
            semantic_weight=args.semantic_weight,
        )
        report = evaluate_semantic_challenger(
            candidates,
            labels,
            matcher=matcher,
            minimum_pairs=args.minimum_pairs,
        )
    elif args.command == "evaluate-ai":
        candidates = pd.read_csv(args.candidates, dtype=str, keep_default_na=False)
        labels = pd.read_csv(args.labels, dtype=str, keep_default_na=False)
        report = evaluate_ai_relevance_baseline(
            candidates,
            labels,
            minimum_pairs=args.minimum_pairs,
        )
    else:
        frame = pd.read_csv(args.input, dtype=str, keep_default_na=False)
        report = evaluate_relevance_baseline(frame, minimum_pairs=args.minimum_pairs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
