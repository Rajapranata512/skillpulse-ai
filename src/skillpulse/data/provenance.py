"""Validate machine-readable dataset provenance and local artifact identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_SOURCE_FIELDS = {
    "id",
    "title",
    "platform",
    "creator",
    "url",
    "version",
    "license",
    "observation_window",
    "scope",
    "acquisition",
    "local_artifact",
    "publication_policy",
    "attribution",
}


def _issue(code: str, severity: str, source_id: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "source_id": source_id, "message": message}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source_manifest(
    manifest_path: Path = Path("data/provenance/sources.yaml"),
    root: Path = Path("."),
    require_local: bool = False,
) -> dict[str, Any]:
    """Validate source metadata and optionally verify local file size and SHA-256."""
    if not manifest_path.exists():
        return {
            "valid": False,
            "manifest": str(manifest_path),
            "sources": [],
            "issues": [_issue("manifest_missing", "critical", "manifest", "Source manifest was not found.")],
        }

    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    sources = payload.get("sources")
    if payload.get("schema_version") != 1 or not isinstance(sources, list) or not sources:
        return {
            "valid": False,
            "manifest": str(manifest_path),
            "sources": [],
            "issues": [
                _issue(
                    "invalid_manifest_schema",
                    "critical",
                    "manifest",
                    "schema_version must be 1 and sources must be a non-empty list.",
                )
            ],
        }

    issues: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, source in enumerate(sources):
        source_id = str(source.get("id") or f"source_{index}")
        missing = sorted(REQUIRED_SOURCE_FIELDS - set(source))
        if missing:
            issues.append(
                _issue(
                    "missing_source_fields",
                    "critical",
                    source_id,
                    f"Missing required fields: {', '.join(missing)}.",
                )
            )
        if source_id in seen_ids:
            issues.append(_issue("duplicate_source_id", "critical", source_id, "Source id must be unique."))
        seen_ids.add(source_id)

        source_url = str(source.get("url", ""))
        if not source_url.startswith("https://"):
            issues.append(_issue("invalid_source_url", "high", source_id, "Source URL must use HTTPS."))

        license_data = source.get("license") or {}
        if not all(license_data.get(field) for field in ("name", "spdx", "url")):
            issues.append(
                _issue("incomplete_license", "high", source_id, "License name, SPDX id, and URL are required.")
            )

        artifact = source.get("local_artifact") or {}
        relative_path = str(artifact.get("path", ""))
        expected_hash = str(artifact.get("sha256", "")).casefold()
        expected_bytes = artifact.get("bytes")
        if not relative_path or not SHA256_PATTERN.fullmatch(expected_hash):
            issues.append(
                _issue(
                    "invalid_local_identity",
                    "high",
                    source_id,
                    "Local path and lowercase 64-character SHA-256 are required.",
                )
            )

        local_path = root / relative_path
        local_result: dict[str, Any] = {
            "path": relative_path,
            "present": local_path.is_file(),
            "identity_verified": False,
        }
        if local_path.is_file():
            actual_hash = _sha256(local_path)
            actual_bytes = local_path.stat().st_size
            local_result.update({"bytes": actual_bytes, "sha256": actual_hash})
            size_matches = expected_bytes == actual_bytes
            hash_matches = expected_hash == actual_hash
            local_result["identity_verified"] = bool(size_matches and hash_matches)
            if not size_matches:
                issues.append(
                    _issue("local_size_mismatch", "critical", source_id, "Local file size differs from the manifest.")
                )
            if not hash_matches:
                issues.append(
                    _issue("local_hash_mismatch", "critical", source_id, "Local SHA-256 differs from the manifest.")
                )
        else:
            severity = "high" if require_local else "info"
            issues.append(
                _issue(
                    "local_file_missing",
                    severity,
                    source_id,
                    "Local raw file is absent; download it from the declared source when reproduction requires it.",
                )
            )

        results.append(
            {
                "id": source_id,
                "title": source.get("title"),
                "version": source.get("version"),
                "license": license_data.get("spdx"),
                "local_artifact": local_result,
            }
        )

    blocking = [issue for issue in issues if issue["severity"] in {"critical", "high"}]
    return {
        "valid": not blocking,
        "manifest": str(manifest_path),
        "schema_version": payload.get("schema_version"),
        "sources": results,
        "issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/provenance/sources.yaml"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--require-local", action="store_true")
    args = parser.parse_args()

    report = verify_source_manifest(args.manifest, args.root, args.require_local)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
