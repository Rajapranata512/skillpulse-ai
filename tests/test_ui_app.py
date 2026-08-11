"""End-to-end widget-state tests for the public Streamlit demo."""

from __future__ import annotations

import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from skillpulse.ui.examples import EXAMPLE_CV, EXAMPLE_EXTRACTION, EXAMPLE_JOB

APP_PATH = Path(__file__).parents[1] / "src" / "skillpulse" / "ui" / "app.py"

MATCH_RESPONSE = {
    "overall_score": 67.5,
    "verdict": "potential_match",
    "matched_skills": ["Communication", "Python", "SQL", "Tableau"],
    "missing_skills": ["Power BI", "Statistics"],
    "category_scores": [
        {
            "category": "technical_skills",
            "score": 0.6667,
            "effective_weight": 0.3,
            "explanation": "2 dari 3 persyaratan cocok.",
        }
    ],
    "learning_priorities": [
        {
            "skill": "Statistics",
            "priority": "high",
            "reason": "Disebut pada lowongan tetapi belum terdeteksi di CV.",
        }
    ],
    "disclaimer": "Gunakan sebagai decision support, bukan keputusan rekrutmen otomatis.",
}

EXTRACTION_RESPONSE = {
    "contract_version": "1.0.0",
    "taxonomy_version": "0.2.0",
    "technical_skills": [{"canonical": "Python"}, {"canonical": "SQL"}],
    "tools": [{"canonical": "Power BI"}],
    "soft_skills": [{"canonical": "Communication"}],
    "experience_years": 0.0,
    "seniority": "entry",
    "work_arrangement": "hybrid",
}


@pytest.fixture
def ui_api(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    state: dict[str, Any] = {"requests": [], "fail_match": False}

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            state["requests"].append(("GET", self.path, None))
            self._respond(200, {"status": "ok", "contract_version": "1.0.0"})

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            state["requests"].append(("POST", self.path, payload))
            if self.path == "/v1/match" and state["fail_match"]:
                self._respond(422, {"detail": {"message": "Requirement pekerjaan belum dapat diekstrak."}})
            elif self.path == "/v1/match":
                self._respond(200, MATCH_RESPONSE)
            elif self.path == "/v1/extract":
                self._respond(200, EXTRACTION_RESPONSE)
            else:
                self._respond(404, {"detail": {"message": "Not found"}})

        def log_message(self, _format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("SKILLPULSE_API_URL", f"http://127.0.0.1:{server.server_port}")
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _app() -> AppTest:
    return AppTest.from_file(APP_PATH, default_timeout=10).run()


def test_initial_demo_is_private_explainable_and_has_explicit_empty_states(ui_api: dict[str, Any]) -> None:
    app = _app()

    assert not app.exception
    assert [area.value for area in app.text_area] == ["", "", ""]
    assert {button.label for button in app.button} == {
        "Gunakan data contoh",
        "Analyze match",
        "Gunakan contoh extraction",
        "Extract requirements",
    }
    assert any("Privacy by design" in item.value for item in app.markdown)
    assert any("@media (max-width: 640px)" in item.value for item in app.markdown)
    assert any("Hasil explainable match" in item.value for item in app.info)
    assert any("Entity hasil extraction" in item.value for item in app.info)
    assert app.selectbox(key="market_segment").value == "All listings"
    assert app.selectbox(key="market_skill_category").value == "All extracted requirements"
    market_metrics = {metric.label: metric.value for metric in app.metric}
    assert market_metrics["Listings in snapshot"] == "555"
    assert market_metrics["Unique descriptions"] == "542"
    assert market_metrics["Reported provinces"] == "18"
    assert market_metrics["Salary disclosed"] == "77 (13.9%)"
    assert any("keseluruhan pasar" in item.value for item in app.markdown)
    assert not app.file_uploader
    assert all(request[0] == "GET" for request in ui_api["requests"])


def test_sample_match_and_extraction_journeys_render_contract_evidence(ui_api: dict[str, Any]) -> None:
    app = _app()

    app.button(key="load_match_example").click().run()
    assert app.text_area(key="match_cv_text").value == EXAMPLE_CV
    assert app.text_area(key="match_job_text").value == EXAMPLE_JOB

    app.button(key="analyze_match").click().run()
    metrics = {metric.label: metric.value for metric in app.metric}
    assert {label: metrics[label] for label in ("Match score", "Verdict", "Skill gaps")} == {
        "Match score": "67.5/100",
        "Verdict": "Potential match",
        "Skill gaps": "2",
    }
    assert any("Power BI" in item.value for item in app.markdown)
    assert any("decision support" in item.value for item in app.caption)

    app.button(key="load_extraction_example").click().run()
    assert app.text_area(key="extraction_job_text").value == EXAMPLE_EXTRACTION
    app.button(key="extract_requirements").click().run()
    extraction_metrics = {metric.label: metric.value for metric in app.metric}
    assert {label: extraction_metrics[label] for label in ("Experience", "Seniority", "Work mode")} == {
        "Experience": "0.0",
        "Seniority": "Entry",
        "Work mode": "Hybrid",
    }
    assert any("Python" in item.value and "SQL" in item.value for item in app.markdown)

    post_paths = [request[1] for request in ui_api["requests"] if request[0] == "POST"]
    assert post_paths == ["/v1/match", "/v1/extract"]


def test_market_snapshot_filter_is_local_source_backed_and_api_independent(ui_api: dict[str, Any]) -> None:
    app = _app()

    initial_posts = [request for request in ui_api["requests"] if request[0] == "POST"]
    app.selectbox(key="market_segment").select("Role · Data Analyst").run()
    app.selectbox(key="market_skill_category").select("Tools").run()

    assert app.selectbox(key="market_segment").value == "Role · Data Analyst"
    assert app.selectbox(key="market_skill_category").value == "Tools"
    assert [request for request in ui_api["requests"] if request[0] == "POST"] == initial_posts
    assert any("Active filter: Role · Data Analyst" in item.value for item in app.caption)
    assert any(
        "Salary prediction and time-series claims remain intentionally disabled" in item.value
        for item in app.warning
    )
    assert not app.exception


def test_empty_and_domain_error_states_are_user_safe(ui_api: dict[str, Any]) -> None:
    app = _app()

    app.button(key="analyze_match").click().run()
    assert any("Isi CV dan job description" in item.value for item in app.error)
    assert not any(request[0] == "POST" for request in ui_api["requests"])

    app.text_area(key="match_cv_text").set_value("Python dan SQL").run()
    app.text_area(key="match_job_text").set_value("Butuh kandidat Python").run()
    ui_api["fail_match"] = True
    app.button(key="analyze_match").click().run()

    assert any("Requirement pekerjaan belum dapat diekstrak" in item.value for item in app.error)
    assert not any("Python dan SQL" in item.value for item in app.error)
