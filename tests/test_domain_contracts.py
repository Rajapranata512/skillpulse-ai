import pytest
from pydantic import ValidationError

from skillpulse.domain import ExtractionRequest, ExtractionResponse, MatchRequest, MatchResponse
from skillpulse.domain.contracts import MAX_TEXT_LENGTH, build_contract_artifact
from skillpulse.extraction import EntityExtractor
from skillpulse.matching import CVJobMatcher


def test_extraction_result_conforms_to_versioned_contract() -> None:
    result = EntityExtractor().extract("Need Python and SQL. Bachelor degree, hybrid work.")
    response = ExtractionResponse.from_result(result)

    assert response.contract_version == "1.0.0"
    assert response.taxonomy_version == "0.2.0"
    assert [item.canonical for item in response.technical_skills] == ["Python", "SQL"]


def test_match_result_conforms_to_versioned_contract() -> None:
    result = CVJobMatcher().match("Python and SQL", "Python, SQL and Tableau required")
    response = MatchResponse.from_result(result)

    assert 0 <= response.overall_score <= 100
    assert response.missing_skills == ["Tableau"]
    assert response.disclaimer


def test_requests_reject_empty_oversized_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ExtractionRequest(text="")
    with pytest.raises(ValidationError):
        MatchRequest(cv_text="valid", job_text="x" * (MAX_TEXT_LENGTH + 1))
    with pytest.raises(ValidationError):
        ExtractionRequest(text="Python", unexpected=True)  # type: ignore[call-arg]


def test_contract_artifact_is_strict_and_privacy_explicit() -> None:
    artifact = build_contract_artifact()

    assert artifact["contract_version"] == "1.0.0"
    assert artifact["schemas"]["MatchRequest"]["additionalProperties"] is False
    assert artifact["privacy"]["raw_cv_persistence"] is False
