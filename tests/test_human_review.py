import copy
import json
from pathlib import Path

from skillpulse.release.human_review import validate_human_review

TEMPLATE = Path("configs/human_accessibility_review.template.json")


def _template() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def _completed_review() -> dict:
    payload = _template()
    payload["review_status"] = "complete"
    payload["reviewer"] = {
        "reviewer_code": "reviewer-01",
        "reviewed_on": "2026-08-11",
        "human_attestation": True,
    }
    for environment in payload["environments"]:
        environment.update(
            {
                "status": "pass",
                "platform": "review-platform",
                "browser": "review-browser",
                "device_class": "physical-device",
            }
        )
        if environment["id"] == "screen_reader":
            environment["assistive_technology"] = "review-screen-reader"
    for check in payload["checks"]:
        check.update({"status": "pass", "evidence_note": f"Observed {check['id']}"})
    payload["media"] = {
        "status": "pass",
        "duration_seconds": 180,
        "synthetic_or_redacted_only": True,
        "no_personal_data": True,
        "narration_complete": True,
        "artifact_reference": "m5c-walkthrough-v1",
    }
    return payload


def test_blank_template_is_valid_but_cannot_close_human_gate() -> None:
    result = validate_human_review(_template())

    assert result["structurally_valid"] is True
    assert result["completion_ready"] is False
    assert result["checks"] == {"total": 9, "passed": 0}
    assert "human_attestation must be true" in result["completion_gaps"]


def test_complete_human_review_passes_machine_checkable_gate() -> None:
    result = validate_human_review(_completed_review())

    assert result["structurally_valid"] is True
    assert result["completion_ready"] is True
    assert result["checks"] == {"total": 9, "passed": 9}
    assert result["completion_gaps"] == []


def test_real_safari_may_be_unavailable_only_with_a_reason() -> None:
    payload = _completed_review()
    safari = next(item for item in payload["environments"] if item["id"] == "real_safari")
    safari.update({"status": "not_applicable", "platform": "", "browser": "", "device_class": ""})

    without_reason = validate_human_review(payload)
    assert "environment real_safari needs a reason when not_applicable" in without_reason["completion_gaps"]

    safari["notes"] = "No Apple hardware was available; automated WebKit evidence remains separate."
    with_reason = validate_human_review(payload)
    assert with_reason["completion_ready"] is True


def test_open_high_finding_blocks_completion() -> None:
    payload = _completed_review()
    payload["findings"].append(
        {"id": "A11Y-01", "severity": "high", "status": "open", "summary": "Focus is not visible."}
    )

    result = validate_human_review(payload)

    assert result["completion_ready"] is False
    assert "finding A11Y-01 must be resolved" in result["completion_gaps"]


def test_media_privacy_and_duration_are_required() -> None:
    payload = _completed_review()
    payload["media"].update({"duration_seconds": 90, "no_personal_data": False})

    result = validate_human_review(payload)

    assert result["completion_ready"] is False
    assert "media.duration_seconds must be between 120 and 240" in result["completion_gaps"]
    assert "media.no_personal_data must be true" in result["completion_gaps"]


def test_unknown_reviewer_fields_are_rejected_to_avoid_personal_data() -> None:
    payload = copy.deepcopy(_template())
    payload["reviewer"]["email"] = ""

    result = validate_human_review(payload)

    assert result["structurally_valid"] is False
    assert "reviewer has unknown fields: email" in result["errors"]


def test_wrong_choice_types_return_validation_errors_instead_of_crashing() -> None:
    payload = _template()
    payload["review_status"] = []
    payload["environments"][0]["status"] = {}
    payload["checks"][0]["status"] = 1
    payload["media"]["status"] = False

    result = validate_human_review(payload)

    assert result["structurally_valid"] is False
    assert len(result["errors"]) == 4
