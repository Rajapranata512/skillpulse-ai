import re
import tomllib
from pathlib import Path

from skillpulse.api.app import create_app

PORTFOLIO_DOCS = (
    Path("README.md"),
    Path("SECURITY.md"),
    Path("PRIVACY.md"),
    Path("DATA_ATTRIBUTION.md"),
    Path("docs/architecture.md"),
    Path("docs/case_study.md"),
    Path("docs/demo_checklist.md"),
    Path("docs/release_checklist.md"),
    Path("docs/model_card.md"),
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
DOCUMENTED_API_ENDPOINTS = {"/health", "/v1/models", "/v1/extract", "/v1/match"}


def _local_link_targets(document: Path) -> list[Path]:
    targets: list[Path] = []
    for raw_target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
        target = raw_target.strip().strip("<>").split("#", maxsplit=1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        targets.append((document.parent / target).resolve())
    return targets


def test_recruiter_facing_local_markdown_links_resolve() -> None:
    missing = {
        str(document): [str(target) for target in _local_link_targets(document) if not target.exists()]
        for document in PORTFOLIO_DOCS
    }

    assert {document: targets for document, targets in missing.items() if targets} == {}


def test_documented_api_endpoints_match_the_live_contract() -> None:
    live_endpoints = {
        route.path
        for route in create_app().routes
        if route.path not in {"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"}
    }
    assert live_endpoints == DOCUMENTED_API_ENDPOINTS

    for document in (Path("README.md"), Path("PRD.md"), Path("docs/architecture.md")):
        content = document.read_text(encoding="utf-8")
        for endpoint in DOCUMENTED_API_ENDPOINTS:
            assert endpoint in content
        assert "`/metadata`" not in content


def test_public_license_and_package_metadata_are_consistent() -> None:
    license_text = Path("LICENSE").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    attribution = Path("DATA_ATTRIBUTION.md").read_text(encoding="utf-8")
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert license_text.startswith("MIT License\n")
    assert "Copyright (c) 2026 Rajapranata512" in license_text
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    assert project["urls"]["Repository"] == "https://github.com/Rajapranata512/skillpulse-ai"
    assert "[MIT License](LICENSE)" in readme
    assert "Creative Commons Attribution 4.0 International" in attribution
