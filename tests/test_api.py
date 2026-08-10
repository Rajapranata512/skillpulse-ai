from fastapi.testclient import TestClient

from skillpulse.api import create_app

client = TestClient(create_app())


def test_health_and_model_metadata_are_versioned_and_privacy_explicit() -> None:
    health = client.get("/health")
    metadata = client.get("/v1/models")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "skillpulse-api", "contract_version": "1.0.0"}
    assert metadata.status_code == 200
    assert metadata.json()["stores_input_text"] is False
    assert metadata.json()["decision_support_only"] is True
    assert metadata.json()["semantic_challenger_status"] == "evaluated_not_promoted"


def test_extract_endpoint_returns_evidence_and_versions() -> None:
    response = client.post(
        "/v1/extract",
        json={"text": "Butuh Python, SQL, Power BI, minimal S1 untuk posisi hybrid."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_version"] == "1.0.0"
    assert payload["taxonomy_version"] == "0.2.0"
    assert [item["canonical"] for item in payload["technical_skills"]] == ["Python", "SQL"]
    assert payload["tools"][0]["canonical"] == "Power BI"
    assert payload["technical_skills"][0]["start"] >= 0


def test_match_endpoint_returns_explainable_gap() -> None:
    response = client.post(
        "/v1/match",
        json={
            "cv_text": "Data analyst with Python, SQL, Excel and bachelor degree.",
            "job_text": "Need Python, SQL, Power BI, bachelor degree and 2 years experience.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_score"] < 100
    assert "Power BI" in payload["missing_skills"]
    assert payload["category_scores"]
    assert payload["learning_priorities"]
    assert "decision support" in payload["disclaimer"]


def test_api_rejects_unknown_fields_and_unsupported_job() -> None:
    unknown = client.post("/v1/extract", json={"text": "Python", "save_cv": True})
    unsupported = client.post(
        "/v1/match",
        json={"cv_text": "Experienced candidate", "job_text": "Join our growing company"},
    )

    assert unknown.status_code == 422
    assert unsupported.status_code == 422
    assert unsupported.json()["detail"]["code"] == "domain_validation_error"


def test_openapi_contains_all_public_endpoints_and_contract_models() -> None:
    schema = client.get("/openapi.json").json()

    assert {"/health", "/v1/models", "/v1/extract", "/v1/match"} <= set(schema["paths"])
    assert "ExtractionResponse" in schema["components"]["schemas"]
    assert "MatchResponse" in schema["components"]["schemas"]
