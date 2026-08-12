import tomllib
from pathlib import Path


def test_dependency_audit_is_fail_closed_and_preserves_evidence() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "dependency-audit:" in workflow
    assert "python -m pip install --upgrade pip setuptools" in workflow
    assert 'python -m pip install -e ".[api,ui,security]"' in workflow
    assert "python -m pip_audit --skip-editable --progress-spinner off --format json" in workflow
    assert "skillpulse-dependency-audit-${{ github.sha }}" in workflow
    assert "if-no-files-found: error" in workflow


def test_codeql_scans_python_with_explicit_least_privilege() -> None:
    workflow = Path(".github/workflows/codeql.yml").read_text(encoding="utf-8")

    assert "github/codeql-action/init@v4" in workflow
    assert "github/codeql-action/analyze@v4" in workflow
    assert "languages: python" in workflow
    assert "queries: security-extended" in workflow
    assert "security-events: write" in workflow
    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow


def test_security_scanner_is_optional_and_version_pinned() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert "pip-audit" not in " ".join(config["project"]["dependencies"])
    assert config["project"]["optional-dependencies"]["security"] == ["pip-audit==2.10.1"]
