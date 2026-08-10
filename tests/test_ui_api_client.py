import io
import json
from urllib.error import HTTPError, URLError

import pytest

from skillpulse.ui import SkillPulseAPIClient, SkillPulseAPIError
from skillpulse.ui import api_client as client_module


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):  # type: ignore[no-untyped-def]
        return self

    def __exit__(self, *_args):  # type: ignore[no-untyped-def]
        return False

    def read(self) -> bytes:
        return self.body


def test_ui_client_uses_versioned_paths_without_persistence_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse({"overall_score": 75.0})

    monkeypatch.setattr(client_module, "urlopen", fake_urlopen)
    result = SkillPulseAPIClient("http://api.local/", timeout=7).match("cv", "job")

    assert captured == {
        "url": "http://api.local/v1/match",
        "payload": {"cv_text": "cv", "job_text": "job"},
        "timeout": 7,
    }
    assert result["overall_score"] == 75.0


def test_ui_client_surfaces_domain_and_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def domain_error(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        body = io.BytesIO(json.dumps({"detail": {"message": "No requirements"}}).encode())
        raise HTTPError("http://api/v1/match", 422, "", {}, body)

    monkeypatch.setattr(client_module, "urlopen", domain_error)
    with pytest.raises(SkillPulseAPIError, match="No requirements"):
        SkillPulseAPIClient("http://api").match("cv", "job")

    monkeypatch.setattr(client_module, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("off")))
    with pytest.raises(SkillPulseAPIError, match="skillpulse-api"):
        SkillPulseAPIClient("http://api").health()
