from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from skillpulse.data.provenance import verify_source_manifest


def _manifest(file_path: str, sha256: str, size: int) -> dict[str, object]:
    return {
        "schema_version": 1,
        "sources": [
            {
                "id": "test_source",
                "title": "Test dataset",
                "platform": "Test",
                "creator": "Tester",
                "url": "https://example.com/dataset",
                "version": 1,
                "license": {"name": "CC BY 4.0", "spdx": "CC-BY-4.0", "url": "https://example.com/license"},
                "observation_window": {"start": "2025-01-01", "end": "2025-01-31"},
                "scope": {"unit": "one row"},
                "acquisition": {"project_method": "download"},
                "local_artifact": {"path": file_path, "sha256": sha256, "bytes": size},
                "publication_policy": {"include_raw_file_in_public_repository": False},
                "attribution": "Test attribution",
            }
        ],
    }


def test_provenance_manifest_verifies_local_identity(tmp_path: Path) -> None:
    data = b"source-data"
    source = tmp_path / "source.csv"
    source.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(yaml.safe_dump(_manifest(source.name, digest, len(data))), encoding="utf-8")

    report = verify_source_manifest(manifest, tmp_path, require_local=True)

    assert report["valid"] is True
    assert report["sources"][0]["local_artifact"]["identity_verified"] is True


def test_provenance_manifest_rejects_hash_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("changed", encoding="utf-8")
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(yaml.safe_dump(_manifest(source.name, "0" * 64, source.stat().st_size)), encoding="utf-8")

    report = verify_source_manifest(manifest, tmp_path, require_local=True)

    assert report["valid"] is False
    assert {issue["code"] for issue in report["issues"]} == {"local_hash_mismatch"}


def test_project_manifest_is_valid_when_raw_file_is_optional() -> None:
    report = verify_source_manifest(Path("data/provenance/sources.yaml"))

    assert report["valid"] is True
    assert report["sources"][0]["license"] == "CC-BY-4.0"
