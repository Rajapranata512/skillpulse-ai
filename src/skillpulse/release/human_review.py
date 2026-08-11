"""Validate human accessibility and public-safe demo-media review evidence.

The validator is intentionally unable to create reviewer judgments. It only checks a
human-completed JSON record and reports whether the M5c evidence gate is ready to close.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
MILESTONE = "M5c"
REVIEW_STATUSES = {"not_reviewed", "in_progress", "complete"}
ITEM_STATUSES = {"not_reviewed", "pass", "fail", "not_applicable"}
FINDING_SEVERITIES = {"blocker", "high", "medium", "low"}
FINDING_STATUSES = {"open", "resolved"}

REQUIRED_ENVIRONMENTS = {
    "screen_reader": False,
    "mobile_real_device": False,
    "real_safari": True,
}
REQUIRED_CHECKS = (
    "keyboard_focus_order",
    "visible_focus",
    "contrast",
    "screen_reader_structure",
    "status_announcements",
    "error_identification",
    "chart_text_alternatives",
    "mobile_responsiveness",
    "data_table_readability",
)

TOP_LEVEL_KEYS = {
    "schema_version",
    "milestone",
    "review_status",
    "reviewer",
    "environments",
    "checks",
    "findings",
    "media",
}
REVIEWER_KEYS = {"reviewer_code", "reviewed_on", "human_attestation"}
ENVIRONMENT_KEYS = {
    "id",
    "status",
    "platform",
    "browser",
    "assistive_technology",
    "device_class",
    "notes",
}
CHECK_KEYS = {"id", "status", "evidence_note"}
FINDING_KEYS = {"id", "severity", "status", "summary"}
MEDIA_KEYS = {
    "status",
    "duration_seconds",
    "synthetic_or_redacted_only",
    "no_personal_data",
    "narration_complete",
    "artifact_reference",
}


def _is_plain_string(value: object) -> bool:
    return isinstance(value, str)


def _is_choice(value: object, choices: set[str]) -> bool:
    return isinstance(value, str) and value in choices


def _exact_keys(value: object, expected: set[str], path: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return False
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        errors.append(f"{path} is missing fields: {', '.join(missing)}")
    if unknown:
        errors.append(f"{path} has unknown fields: {', '.join(unknown)}")
    return not missing and not unknown


def _validate_date(value: object, errors: list[str]) -> None:
    if value == "":
        return
    if not _is_plain_string(value):
        errors.append("reviewer.reviewed_on must be an ISO date string or blank")
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append("reviewer.reviewed_on must use YYYY-MM-DD")


def _validate_reviewer(value: object, errors: list[str]) -> None:
    if not _exact_keys(value, REVIEWER_KEYS, "reviewer", errors):
        return
    assert isinstance(value, dict)
    code = value["reviewer_code"]
    if not _is_plain_string(code) or len(code) > 80:
        errors.append("reviewer.reviewer_code must be a string of at most 80 characters")
    if _is_plain_string(code) and ("@" in code or "\\" in code or "/" in code):
        errors.append("reviewer.reviewer_code must be pseudonymous and must not contain email/path data")
    _validate_date(value["reviewed_on"], errors)
    if not isinstance(value["human_attestation"], bool):
        errors.append("reviewer.human_attestation must be a boolean")


def _validate_environments(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("environments must be a list")
        return
    seen: set[str] = set()
    for index, environment in enumerate(value):
        path = f"environments[{index}]"
        if not _exact_keys(environment, ENVIRONMENT_KEYS, path, errors):
            continue
        assert isinstance(environment, dict)
        environment_id = environment["id"]
        if not _is_plain_string(environment_id):
            errors.append(f"{path}.id must be a string")
            continue
        if environment_id in seen:
            errors.append(f"duplicate environment id: {environment_id}")
        seen.add(environment_id)
        if environment_id not in REQUIRED_ENVIRONMENTS:
            errors.append(f"unknown environment id: {environment_id}")
        status = environment["status"]
        if not _is_choice(status, ITEM_STATUSES):
            errors.append(f"{path}.status must be one of {sorted(ITEM_STATUSES)}")
        if status == "not_applicable" and not REQUIRED_ENVIRONMENTS.get(environment_id, False):
            errors.append(f"{environment_id} cannot be marked not_applicable")
        for field in ("platform", "browser", "assistive_technology", "device_class", "notes"):
            if not _is_plain_string(environment[field]):
                errors.append(f"{path}.{field} must be a string")
    missing = sorted(set(REQUIRED_ENVIRONMENTS) - seen)
    if missing:
        errors.append(f"environments is missing required ids: {', '.join(missing)}")


def _validate_checks(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("checks must be a list")
        return
    seen: set[str] = set()
    for index, check in enumerate(value):
        path = f"checks[{index}]"
        if not _exact_keys(check, CHECK_KEYS, path, errors):
            continue
        assert isinstance(check, dict)
        check_id = check["id"]
        if not _is_plain_string(check_id):
            errors.append(f"{path}.id must be a string")
            continue
        if check_id in seen:
            errors.append(f"duplicate check id: {check_id}")
        seen.add(check_id)
        if check_id not in REQUIRED_CHECKS:
            errors.append(f"unknown check id: {check_id}")
        status = check["status"]
        if not _is_choice(status, ITEM_STATUSES - {"not_applicable"}):
            errors.append(f"{path}.status must be not_reviewed, pass, or fail")
        if not _is_plain_string(check["evidence_note"]):
            errors.append(f"{path}.evidence_note must be a string")
    missing = sorted(set(REQUIRED_CHECKS) - seen)
    if missing:
        errors.append(f"checks is missing required ids: {', '.join(missing)}")


def _validate_findings(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("findings must be a list")
        return
    seen: set[str] = set()
    for index, finding in enumerate(value):
        path = f"findings[{index}]"
        if not _exact_keys(finding, FINDING_KEYS, path, errors):
            continue
        assert isinstance(finding, dict)
        finding_id = finding["id"]
        if not _is_plain_string(finding_id) or not finding_id.strip():
            errors.append(f"{path}.id must be a non-empty string")
        elif finding_id in seen:
            errors.append(f"duplicate finding id: {finding_id}")
        else:
            seen.add(finding_id)
        if not _is_choice(finding["severity"], FINDING_SEVERITIES):
            errors.append(f"{path}.severity must be one of {sorted(FINDING_SEVERITIES)}")
        if not _is_choice(finding["status"], FINDING_STATUSES):
            errors.append(f"{path}.status must be open or resolved")
        if not _is_plain_string(finding["summary"]) or not finding["summary"].strip():
            errors.append(f"{path}.summary must be a non-empty string")


def _validate_media(value: object, errors: list[str]) -> None:
    if not _exact_keys(value, MEDIA_KEYS, "media", errors):
        return
    assert isinstance(value, dict)
    if not _is_choice(value["status"], ITEM_STATUSES - {"not_applicable"}):
        errors.append("media.status must be not_reviewed, pass, or fail")
    duration = value["duration_seconds"]
    if duration is not None and (not isinstance(duration, int) or isinstance(duration, bool) or duration < 0):
        errors.append("media.duration_seconds must be a non-negative integer or null")
    for field in ("synthetic_or_redacted_only", "no_personal_data", "narration_complete"):
        if not isinstance(value[field], bool):
            errors.append(f"media.{field} must be a boolean")
    if not _is_plain_string(value["artifact_reference"]):
        errors.append("media.artifact_reference must be a string")


def _completion_gaps(payload: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if payload.get("review_status") != "complete":
        gaps.append("review_status must be complete")

    reviewer = payload.get("reviewer", {})
    if not reviewer.get("reviewer_code"):
        gaps.append("reviewer_code is required for completion")
    if not reviewer.get("reviewed_on"):
        gaps.append("reviewed_on is required for completion")
    if reviewer.get("human_attestation") is not True:
        gaps.append("human_attestation must be true")

    environments = {
        item.get("id"): item for item in payload.get("environments", []) if isinstance(item, dict)
    }
    for environment_id, allow_na in REQUIRED_ENVIRONMENTS.items():
        item = environments.get(environment_id, {})
        allowed = {"pass", "not_applicable"} if allow_na else {"pass"}
        if item.get("status") not in allowed:
            suffix = " or be justified as not_applicable" if allow_na else ""
            gaps.append(f"environment {environment_id} must pass{suffix}")
            continue
        if item.get("status") == "not_applicable":
            if not str(item.get("notes", "")).strip():
                gaps.append(f"environment {environment_id} needs a reason when not_applicable")
            continue
        if not str(item.get("platform", "")).strip() or not str(item.get("browser", "")).strip():
            gaps.append(f"environment {environment_id} needs platform and browser evidence")
        if environment_id == "screen_reader" and not str(item.get("assistive_technology", "")).strip():
            gaps.append("environment screen_reader needs assistive_technology evidence")
        if environment_id in {"mobile_real_device", "real_safari"} and not str(
            item.get("device_class", "")
        ).strip():
            gaps.append(f"environment {environment_id} needs device_class evidence")

    checks = {item.get("id"): item for item in payload.get("checks", []) if isinstance(item, dict)}
    for check_id in REQUIRED_CHECKS:
        item = checks.get(check_id, {})
        if item.get("status") != "pass":
            gaps.append(f"check {check_id} must pass")
        elif not str(item.get("evidence_note", "")).strip():
            gaps.append(f"check {check_id} needs an evidence_note")

    for finding in payload.get("findings", []):
        if not isinstance(finding, dict):
            continue
        if finding.get("status") == "open" and finding.get("severity") in {"blocker", "high"}:
            gaps.append(f"finding {finding.get('id', '<unknown>')} must be resolved")

    media = payload.get("media", {})
    if media.get("status") != "pass":
        gaps.append("media.status must pass")
    duration = media.get("duration_seconds")
    if not isinstance(duration, int) or isinstance(duration, bool) or not 120 <= duration <= 240:
        gaps.append("media.duration_seconds must be between 120 and 240")
    if media.get("synthetic_or_redacted_only") is not True:
        gaps.append("media.synthetic_or_redacted_only must be true")
    if media.get("no_personal_data") is not True:
        gaps.append("media.no_personal_data must be true")
    if media.get("narration_complete") is not True:
        gaps.append("media.narration_complete must be true")
    if not str(media.get("artifact_reference", "")).strip():
        gaps.append("media.artifact_reference is required")
    return gaps


def validate_human_review(payload: object) -> dict[str, Any]:
    """Validate structure and completion readiness without mutating human evidence."""
    errors: list[str] = []
    if not _exact_keys(payload, TOP_LEVEL_KEYS, "document", errors):
        return {
            "schema_version": SCHEMA_VERSION,
            "milestone": MILESTONE,
            "structurally_valid": False,
            "review_status": None,
            "completion_ready": False,
            "checks": {"total": 0, "passed": 0},
            "errors": errors,
            "completion_gaps": [],
        }

    assert isinstance(payload, dict)
    if payload["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if payload["milestone"] != MILESTONE:
        errors.append(f"milestone must be {MILESTONE}")
    if not _is_choice(payload["review_status"], REVIEW_STATUSES):
        errors.append(f"review_status must be one of {sorted(REVIEW_STATUSES)}")
    _validate_reviewer(payload["reviewer"], errors)
    _validate_environments(payload["environments"], errors)
    _validate_checks(payload["checks"], errors)
    _validate_findings(payload["findings"], errors)
    _validate_media(payload["media"], errors)

    completion_gaps = [] if errors else _completion_gaps(payload)
    checks = payload["checks"] if isinstance(payload["checks"], list) else []
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone": MILESTONE,
        "structurally_valid": not errors,
        "review_status": payload["review_status"],
        "completion_ready": not errors and not completion_gaps,
        "checks": {
            "total": len(checks),
            "passed": sum(isinstance(item, dict) and item.get("status") == "pass" for item in checks),
        },
        "errors": errors,
        "completion_gaps": completion_gaps,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path, help="Human-completed review JSON")
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Return a non-zero exit code unless all M5c completion evidence passes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(args.review.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"structurally_valid": False, "error": str(exc)}, indent=2))
        return 2
    result = validate_human_review(payload)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["structurally_valid"]:
        return 2
    if args.require_complete and not result["completion_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
