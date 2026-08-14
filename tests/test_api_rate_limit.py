from fastapi.testclient import TestClient

from skillpulse.api import create_app


def test_analysis_rate_limit_is_explicit_safe_and_exempts_health() -> None:
    limited = TestClient(create_app(rate_limit_per_minute=1))
    first = limited.post("/v1/extract", json={"text": "Python"})
    health = limited.get("/health")
    blocked = limited.post("/v1/extract", json={"text": "private candidate text"})

    assert first.status_code == 200
    assert health.status_code == 200
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"
    assert blocked.json() == {
        "detail": {
            "code": "rate_limit_exceeded",
            "message": "Batas demo tercapai; coba lagi nanti.",
        }
    }
    assert "private candidate text" not in blocked.text
