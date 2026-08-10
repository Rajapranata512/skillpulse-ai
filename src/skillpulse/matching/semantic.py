"""Multilingual semantic challenger layered on the explainable taxonomy matcher."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Protocol

import pandas as pd

from .engine import CategoryScore, CVJobMatcher, LearningPriority

DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class TextEmbedder(Protocol):
    """Minimal embedding contract used for testability and lazy model loading."""

    model_name: str

    def encode(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Return one dense vector per input text."""


class SentenceTransformerEmbedder:
    """Lazy adapter around Sentence Transformers."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                'Semantic dependencies are missing. Install with: pip install -e ".[semantic]"'
            ) from error
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return self._model.encode(list(texts), normalize_embeddings=True).tolist()


@dataclass(frozen=True)
class SemanticMatchResult:
    """Matcher-compatible result with auditable baseline and semantic components."""

    overall_score: float
    verdict: str
    matched_skills: list[str]
    missing_skills: list[str]
    category_scores: list[CategoryScore]
    learning_priorities: list[LearningPriority]
    disclaimer: str
    taxonomy_score: float
    semantic_score: float
    semantic_weight: float
    embedding_model: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cosine_similarity(first: Sequence[float], second: Sequence[float]) -> float:
    if len(first) != len(second) or not first:
        raise ValueError("Embedding vectors must be non-empty and have equal dimensions")
    numerator = sum(left * right for left, right in zip(first, second, strict=True))
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if first_norm == 0 or second_norm == 0:
        raise ValueError("Embedding vectors must have non-zero norms")
    return numerator / (first_norm * second_norm)


class SemanticHybridMatcher:
    """Blend semantic similarity with the existing explainable taxonomy baseline."""

    def __init__(
        self,
        baseline: CVJobMatcher | None = None,
        embedder: TextEmbedder | None = None,
        *,
        semantic_weight: float = 0.20,
    ) -> None:
        if not 0 <= semantic_weight <= 1:
            raise ValueError("semantic_weight must be between 0 and 1")
        self.baseline = baseline or CVJobMatcher()
        self.embedder = embedder or SentenceTransformerEmbedder()
        self.semantic_weight = semantic_weight

    def match(self, cv_text: str, job_text: str) -> SemanticMatchResult:
        baseline = self.baseline.match(cv_text, job_text)
        vectors = self.embedder.encode((cv_text, job_text))
        if len(vectors) != 2:
            raise ValueError("Embedder must return exactly two vectors")
        similarity = _cosine_similarity(vectors[0], vectors[1])
        semantic_score = round(100 * min(max(similarity, 0.0), 1.0), 1)
        taxonomy_weight = 1.0 - self.semantic_weight
        overall = round(taxonomy_weight * baseline.overall_score + self.semantic_weight * semantic_score, 1)
        verdict = "strong_match" if overall >= 80 else "potential_match" if overall >= 60 else "skill_gap"
        return SemanticMatchResult(
            overall_score=overall,
            verdict=verdict,
            matched_skills=baseline.matched_skills,
            missing_skills=baseline.missing_skills,
            category_scores=baseline.category_scores,
            learning_priorities=baseline.learning_priorities,
            disclaimer=(
                f"{baseline.disclaimer} Semantic similarity is an experimental {self.semantic_weight:.0%} "
                "challenger component and is not a hiring decision."
            ),
            taxonomy_score=baseline.overall_score,
            semantic_score=semantic_score,
            semantic_weight=self.semantic_weight,
            embedding_model=self.embedder.model_name,
        )


def evaluate_semantic_challenger(
    candidates: pd.DataFrame,
    labels: pd.DataFrame,
    matcher: SemanticHybridMatcher | None = None,
    *,
    minimum_pairs: int = 50,
) -> dict[str, Any]:
    """Compare baseline and hybrid on identical synthetic labels without opening ML-QG-3."""
    from .relevance import evaluate_ai_relevance_baseline

    engine = matcher or SemanticHybridMatcher()
    baseline = evaluate_ai_relevance_baseline(candidates, labels, minimum_pairs=minimum_pairs)
    challenger = evaluate_ai_relevance_baseline(
        candidates,
        labels,
        matcher=engine,
        minimum_pairs=minimum_pairs,
    )
    challenger["evaluation_type"] = "synthetic-oracle multilingual semantic-hybrid challenger"
    baseline_metrics = baseline["metrics"]
    challenger_metrics = challenger["metrics"]
    baseline_spearman = baseline_metrics["spearman_global"]
    challenger_spearman = challenger_metrics["spearman_global"]
    baseline_mae = baseline_metrics["mae_on_0_100_scale"]
    challenger_mae = challenger_metrics["mae_on_0_100_scale"]
    return {
        "evaluation_type": "synthetic-oracle baseline versus semantic challenger",
        "claim_status": "experimental_ai_labels_not_human_ml_qg_3",
        "pairs_compared": challenger["pairs_reviewed"],
        "model_name": engine.embedder.model_name,
        "semantic_weight": engine.semantic_weight,
        "ready_for_experimental_comparison": challenger["ready_for_experimental_comparison"],
        "ready_for_ml_qg_3": False,
        "baseline_metrics": baseline_metrics,
        "challenger_metrics": challenger_metrics,
        "delta": {
            "spearman_global": (
                round(challenger_spearman - baseline_spearman, 4)
                if baseline_spearman is not None and challenger_spearman is not None
                else None
            ),
            "mae_on_0_100_scale": (
                round(challenger_mae - baseline_mae, 2)
                if baseline_mae is not None and challenger_mae is not None
                else None
            ),
        },
        "warnings": [
            "Synthetic scenario labels are not independent human judgments.",
            "Do not select or tune the semantic challenger as a portfolio claim until human labels are frozen.",
        ],
    }
