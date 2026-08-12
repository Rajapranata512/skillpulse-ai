from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from skillpulse.data import pipeline
from skillpulse.extraction import EntityExtractor
from skillpulse.extraction.engine import _starts_with_term_after_whitespace
from skillpulse.market import snapshot

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "capture_demo_media.py"
SPEC = importlib.util.spec_from_file_location("capture_demo_media_security", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
capture_demo_media = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capture_demo_media
SPEC.loader.exec_module(capture_demo_media)


def test_pipeline_cli_does_not_print_report_content(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(pipeline, "run", lambda *args: {"private": "sensitive-row-derived-value"})
    monkeypatch.setattr(sys, "argv", ["skillpulse-prepare"])

    pipeline.main()

    output = capsys.readouterr().out
    assert "sensitive-row-derived-value" not in output
    assert output == "Data preparation completed; inspect the configured report artifact for aggregate metrics.\n"


def test_market_cli_does_not_print_private_derived_content(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        snapshot,
        "generate_market_snapshot",
        lambda *args, **kwargs: ({"summary": {"private": "sensitive"}}, {"verdict": "pass"}),
    )
    monkeypatch.setattr(sys, "argv", ["skillpulse-market-snapshot"])

    snapshot.main()

    output = capsys.readouterr().out
    assert "sensitive" not in output
    assert output == "Market snapshot generation completed; inspect the configured quality-report artifact.\n"


@pytest.mark.parametrize(
    "origin",
    [
        "https://127.0.0.1:18080",
        "http://localhost:18080",
        "http://127.0.0.1:18080/path",
        "http://127.0.0.1:18080?next=external",
        "http://user@127.0.0.1:18080",
        "http://127.0.0.1:99999",
    ],
)
def test_browser_proxy_rejects_any_origin_outside_exact_loopback(origin: str) -> None:
    with pytest.raises(ValueError, match="Loopback upstream"):
        capture_demo_media._loopback_targets(origin)


def test_browser_proxy_maps_only_fixed_api_paths() -> None:
    assert capture_demo_media._loopback_targets("http://127.0.0.1:18080") == {
        "/health": "http://127.0.0.1:18080/health",
        "/v1/models": "http://127.0.0.1:18080/v1/models",
        "/v1/extract": "http://127.0.0.1:18080/v1/extract",
        "/v1/match": "http://127.0.0.1:18080/v1/match",
    }


def test_context_exclusions_are_linear_and_preserve_boundaries() -> None:
    assert _starts_with_term_after_whitespace(" " * 50_000 + "teams.", ("team", "teams"))
    extractor = EntityExtractor()
    leadership_audience = extractor.extract("Present to Leadership teams.")
    data_reliability = extractor.extract("Resolve data reliability issues.")
    leadership_skill = extractor.extract("Leadership teamwork is required.")
    assert "Leadership" not in {item.canonical for item in leadership_audience.soft_skills}
    assert "Data Analysis" not in {item.canonical for item in data_reliability.technical_skills}
    assert "Leadership" in {item.canonical for item in leadership_skill.soft_skills}
