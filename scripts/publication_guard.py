"""Fail closed when a proposed public Git snapshot contains sensitive or irrelevant files."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath

MAX_PUBLIC_FILE_BYTES = 2_000_000

ALLOWED_CSV_PATHS = {
    "data/evaluation/matching_relevance_candidates.csv",
}
ALLOWED_DATA_MARKERS = {
    "data/annotations/.gitkeep",
    "data/processed/.gitkeep",
    "data/raw/.gitkeep",
}
ALLOWED_PUBLIC_MEDIA_SHA256 = {
    "docs/assets/skillpulse-desktop-empty.png": (
        "f7e4b926faf2409453c345f1371bb9be3876c576243cbed1a96ba645d168d22c"
    ),
    "docs/assets/skillpulse-desktop-match.png": (
        "6c65c9b4a2df78ac31addecbfd0136344fe1ddaa97b97ba0f5ee32dc32a6db91"
    ),
    "docs/assets/skillpulse-mobile-extraction.png": (
        "feb1913e314b80cf2bce3a7e4336a2a046a35b40a8c27b5bcea0957c4212ff28"
    ),
}
PNG_METADATA_CHUNKS = {b"eXIf", b"iTXt", b"tEXt", b"zTXt"}
DENIED_INTERNAL_REPORT_PATHS = {
    "reports/annotation_readiness.json",
    "reports/annotation_review_001.md",
    "reports/data_provenance_artifact.json",
    "reports/data_provenance_audit.json",
    "reports/data_provenance_metrics.json",
    "reports/data_provenance_report_qa.md",
    "reports/extraction_ai_assisted_eval.json",
}
SPECIAL_TEXT_FILES = {
    ".dockerignore",
    ".gitattributes",
    ".gitignore",
    ".gitkeep",
    "Dockerfile",
    "pre-push",
}
TEXT_SUFFIXES = {
    ".csv",
    ".gitkeep",
    ".ipynb",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".yaml",
    ".yml",
}
DENIED_SUFFIXES = {
    ".cer",
    ".crt",
    ".db",
    ".env",
    ".html",
    ".key",
    ".p12",
    ".pdf",
    ".pem",
    ".pfx",
    ".sqlite",
    ".sqlite3",
    ".xls",
    ".xlsx",
}

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    ("private key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("GitHub fine-grained token", re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("OpenAI-style key", re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Slack token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(rb"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("Stripe live secret", re.compile(rb"\bsk_live_[0-9A-Za-z]{16,}\b")),
    (
        "credential assignment",
        re.compile(
            rb"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*"
            rb"[\"'][^\"'\r\n]{8,}[\"']"
        ),
    ),
    (
        "database URL with embedded password",
        re.compile(rb"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^:\s]+:[^@\s]+@"),
    ),
)

PRIVACY_PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    ("Windows user path", re.compile(rb"(?i)\b[A-Z]:\\Users\\[^\\\s]+\\")),
    ("macOS user path", re.compile(rb"/" rb"Users/[^/\s]+/")),
    ("Linux home path", re.compile(rb"/" rb"home/[^/\s]+/")),
    ("email address", re.compile(rb"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("Indonesian mobile number", re.compile(rb"(?<!\d)(?:\+62|62|0)8\d{8,11}(?!\d)")),
)


@dataclass(frozen=True)
class PublicationFile:
    path: str
    content: bytes


def _git(*args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _split_nul(payload: bytes) -> list[str]:
    return [entry.decode("utf-8") for entry in payload.split(b"\0") if entry]


def staged_files() -> list[PublicationFile]:
    paths = _split_nul(_git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"))
    return [PublicationFile(path, _git("show", f":{path}")) for path in paths]


def committed_files(ref: str) -> list[PublicationFile]:
    paths = _split_nul(_git("ls-tree", "-r", "--name-only", "-z", ref))
    return [PublicationFile(path, _git("show", f"{ref}:{path}")) for path in paths]


def path_violations(path: str) -> list[str]:
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    lower = normalized.lower()
    suffix = pure.suffix.lower()
    violations: list[str] = []

    if normalized.startswith(".git-research-backup"):
        violations.append("local research Git backup must never be published")
    if normalized in DENIED_INTERNAL_REPORT_PATHS:
        violations.append("historical or internal-only report is outside the clean public release")
    if pure.name == "RM.ipynb" or lower.startswith("acceptanceletter") or lower.startswith("paper kelompok"):
        violations.append("historical/user-owned academic artifact is outside the public product scope")
    if "__pycache__" in pure.parts or ".pytest_cache" in pure.parts or ".ruff_cache" in pure.parts:
        violations.append("generated cache is outside the public scope")
    if any(part.endswith(".egg-info") for part in pure.parts):
        violations.append("generated package metadata is outside the public scope")
    if pure.name == ".env" or pure.name.startswith(".env."):
        violations.append("environment files may contain credentials")
    if suffix in DENIED_SUFFIXES:
        violations.append(f"sensitive or non-source extension is denied: {suffix}")
    if suffix == ".csv" and normalized not in ALLOWED_CSV_PATHS:
        violations.append("CSV publication is deny-by-default; only the synthetic relevance candidate set is allowed")
    if normalized.startswith("data/annotations/") and normalized not in ALLOWED_DATA_MARKERS:
        violations.append("human annotation working data is private")
    if normalized.startswith("data/raw/") and normalized not in ALLOWED_DATA_MARKERS:
        violations.append("raw data is not redistributable from this repository")
    if normalized.startswith("data/processed/") and normalized not in ALLOWED_DATA_MARKERS:
        violations.append("derived row-level data is not part of the public release")
    if normalized.startswith("data/evaluation/") and normalized not in ALLOWED_CSV_PATHS:
        violations.append("evaluation labels are private-by-default to prevent human-gate leakage")
    if (
        normalized not in ALLOWED_PUBLIC_MEDIA_SHA256
        and pure.name not in SPECIAL_TEXT_FILES
        and suffix not in TEXT_SUFFIXES
    ):
        violations.append("file type is not on the public text allowlist")
    return violations


def pinned_media_violations(path: str, content: bytes) -> list[str]:
    violations: list[str] = []
    expected_sha256 = ALLOWED_PUBLIC_MEDIA_SHA256[path]
    if len(content) > MAX_PUBLIC_FILE_BYTES:
        violations.append(f"file exceeds {MAX_PUBLIC_FILE_BYTES} bytes")
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        violations.append("public media does not match its reviewed SHA-256")
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        violations.append("public media is not a valid PNG signature")
        return violations

    offset = 8
    found_iend = False
    while offset + 12 <= len(content):
        length = int.from_bytes(content[offset : offset + 4], "big")
        chunk_type = content[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(content):
            violations.append("public PNG has a malformed chunk boundary")
            break
        if chunk_type in PNG_METADATA_CHUNKS:
            violations.append(f"public PNG contains metadata chunk {chunk_type.decode('ascii')}")
        offset = chunk_end
        if chunk_type == b"IEND":
            found_iend = True
            break
    if not found_iend:
        violations.append("public PNG is missing IEND")
    return violations


def content_violations(content: bytes) -> list[str]:
    violations: list[str] = []
    if len(content) > MAX_PUBLIC_FILE_BYTES:
        violations.append(f"file exceeds {MAX_PUBLIC_FILE_BYTES} bytes")
    if b"\x00" in content:
        violations.append("binary content is not allowed")
        return violations
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        violations.append("content is not valid UTF-8 text")
        return violations

    for label, pattern in (*SECRET_PATTERNS, *PRIVACY_PATTERNS):
        if pattern.search(content):
            violations.append(f"possible {label}")
    return violations


def audit_file(file: PublicationFile) -> list[str]:
    normalized = file.path.replace("\\", "/")
    if normalized in ALLOWED_PUBLIC_MEDIA_SHA256:
        return [*path_violations(normalized), *pinned_media_violations(normalized, file.content)]
    return [*path_violations(file.path), *content_violations(file.content)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--staged", action="store_true", help="Audit the exact staged snapshot.")
    source.add_argument("--commit", metavar="REF", help="Audit every file in a commit, such as HEAD.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        files = staged_files() if args.staged else committed_files(args.commit)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        print(f"Publication guard could not read the Git snapshot: {detail}", file=sys.stderr)
        return 2

    if not files:
        print("Publication guard refused an empty snapshot.", file=sys.stderr)
        return 2

    failures: list[tuple[str, list[str]]] = []
    for file in files:
        violations = audit_file(file)
        if violations:
            failures.append((file.path, violations))

    if failures:
        print("Publication guard blocked the snapshot:", file=sys.stderr)
        for path, violations in failures:
            for violation in violations:
                print(f"- {path}: {violation}", file=sys.stderr)
        return 1

    total_bytes = sum(len(file.content) for file in files)
    print(f"Publication guard: PASS ({len(files)} files, {total_bytes} bytes scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
