import pytest

from skillpulse.matching.semantic import SemanticHybridMatcher, _cosine_similarity


class FakeEmbedder:
    model_name = "fake-deterministic-embedder"

    def encode(self, texts):  # type: ignore[no-untyped-def]
        assert len(texts) == 2
        return [[1.0, 0.0], [0.8, 0.6]]


def test_semantic_hybrid_preserves_explanations_and_exposes_components() -> None:
    matcher = SemanticHybridMatcher(embedder=FakeEmbedder(), semantic_weight=0.2)
    result = matcher.match(
        "Mid-level candidate with 2 years experience. Technical skills: Python, SQL. "
        "Tools: Excel. Education: Bachelor. Prefers hybrid work.",
        "Data Analyst. Mid-level role. Requires 2 years experience. Required technical skills: Python, SQL. "
        "Required tools: Excel. Minimum Bachelor degree. This is a hybrid position.",
    )

    assert result.semantic_score == 80.0
    assert result.embedding_model == "fake-deterministic-embedder"
    assert result.category_scores
    assert result.disclaimer
    assert 0 <= result.overall_score <= 100


def test_semantic_hybrid_validates_weight_and_vectors() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        SemanticHybridMatcher(embedder=FakeEmbedder(), semantic_weight=1.1)
    with pytest.raises(ValueError, match="equal dimensions"):
        _cosine_similarity([1.0], [1.0, 2.0])
