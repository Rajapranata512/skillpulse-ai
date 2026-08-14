from __future__ import annotations

import hashlib
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
    internal_report = publication_guard.PublicationFile("reports/annotation_readiness.json", b"{}")
    assert any("internal-only" in item for item in publication_guard.audit_file(internal_report))


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


def test_root_license_is_the_only_extensionless_legal_text_allowed() -> None:
    license_file = publication_guard.PublicationFile("LICENSE", b"MIT License\n")
    arbitrary_file = publication_guard.PublicationFile("PRIVATE_NOTES", b"internal\n")

    assert publication_guard.audit_file(license_file) == []
    assert "file type is not on the public text allowlist" in publication_guard.audit_file(arbitrary_file)


def test_only_hash_pinned_reviewed_png_media_is_allowed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    png = b"\x89PNG\r\n\x1a\n" + (0).to_bytes(4, "big") + b"IEND" + b"\x00" * 4
    path = "docs/assets/reviewed.png"
    monkeypatch.setitem(publication_guard.ALLOWED_PUBLIC_MEDIA_SHA256, path, hashlib.sha256(png).hexdigest())

    assert publication_guard.audit_file(publication_guard.PublicationFile(path, png)) == []
    assert "public media does not match its reviewed SHA-256" in publication_guard.audit_file(
        publication_guard.PublicationFile(path, png + b"tampered")
    )


def test_pinned_png_with_text_metadata_is_denied(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    text_chunk = (0).to_bytes(4, "big") + b"tEXt" + b"\x00" * 4
    iend = (0).to_bytes(4, "big") + b"IEND" + b"\x00" * 4
    png = b"\x89PNG\r\n\x1a\n" + text_chunk + iend
    path = "docs/assets/metadata.png"
    monkeypatch.setitem(publication_guard.ALLOWED_PUBLIC_MEDIA_SHA256, path, hashlib.sha256(png).hexdigest())

    violations = publication_guard.audit_file(publication_guard.PublicationFile(path, png))
    assert "public PNG contains metadata chunk tEXt" in violations
