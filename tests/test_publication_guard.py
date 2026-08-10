from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "publication_guard.py"
SPEC = importlib.util.spec_from_file_location("publication_guard", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
publication_guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = publication_guard
SPEC.loader.exec_module(publication_guard)


def test_public_safe_source_passes() -> None:
    file = publication_guard.PublicationFile("src/skillpulse/example.py", b"VALUE = 42\n")
    assert publication_guard.audit_file(file) == []


def test_synthetic_relevance_candidates_are_the_only_allowed_csv() -> None:
    allowed = publication_guard.PublicationFile(
        "data/evaluation/matching_relevance_candidates.csv",
        b"pair_id,cv_text,job_text\npair_1,synthetic cv,synthetic job\n",
    )
    denied = publication_guard.PublicationFile("data/annotations/gold_sample.csv", b"row,text\n1,private\n")
    assert publication_guard.audit_file(allowed) == []
    assert "human annotation working data is private" in publication_guard.audit_file(denied)


def test_historical_academic_artifacts_are_denied() -> None:
    file = publication_guard.PublicationFile("RM.ipynb", b"{}")
    violations = publication_guard.audit_file(file)
    assert any("historical/user-owned" in violation for violation in violations)


def test_secret_token_is_detected_without_storing_a_real_token_fixture() -> None:
    fake_token = ("gh" + "p_" + "A" * 36).encode()
    violations = publication_guard.content_violations(b"token = \"" + fake_token + b"\"\n")
    assert "possible GitHub token" in violations


def test_local_user_path_is_detected() -> None:
    local_path = ("C:" + "\\Users\\private-user\\project").encode()
    violations = publication_guard.content_violations(local_path)
    assert "possible Windows user path" in violations


def test_binary_content_is_denied() -> None:
    assert "binary content is not allowed" in publication_guard.content_violations(b"abc\x00def")
