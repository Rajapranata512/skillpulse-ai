from __future__ import annotations

import importlib.util
import struct
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "capture_demo_media.py"
SPEC = importlib.util.spec_from_file_location("capture_demo_media", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
capture_demo_media = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capture_demo_media
SPEC.loader.exec_module(capture_demo_media)


def test_service_commands_are_loopback_only_and_disable_request_logs() -> None:
    api, ui, environment = capture_demo_media.build_service_commands(18080, 18501)

    assert api[api.index("--host") + 1] == "127.0.0.1"
    assert "--no-access-log" in api
    assert ui[ui.index("--server.address") + 1] == "127.0.0.1"
    assert ui[ui.index("--server.headless") + 1] == "true"
    assert environment["SKILLPULSE_API_URL"] == "http://127.0.0.1:18080"

    _, _, proxied_environment = capture_demo_media.build_service_commands(
        18080, 18501, api_base_url="http://127.0.0.1:18081"
    )
    assert proxied_environment["SKILLPULSE_API_URL"] == "http://127.0.0.1:18081"


def test_responsive_tolerance_is_explicit() -> None:
    assert capture_demo_media.overflow_is_acceptable(390, 392)
    assert not capture_demo_media.overflow_is_acceptable(390, 393)


def test_browser_qa_contract_declares_three_engines_and_resilience(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        capture_demo_media,
        "_run_browser_qa",
        lambda output, ui_url, stop_proxy: (
            [
                {
                    "file": filename,
                    "state": state,
                    "bytes": 1,
                    "width": 1,
                    "height": 1,
                    "sha256": "0" * 64,
                }
                for filename, state in capture_demo_media.CAPTURE_SPECS
            ],
            [{"state": "chromium_desktop_empty", "viewport_width": 1440, "document_width": 1440}],
            {
                "state": "firefox_desktop_match_keyboard",
                "viewport_width": 1440,
                "document_width": 1440,
                "keyboard_activation": True,
            },
            {
                "state": "webkit_desktop_match_keyboard",
                "viewport_width": 1440,
                "document_width": 1440,
                "keyboard_activation": True,
            },
            {
                "state": "chromium_desktop_api_offline",
                "viewport_width": 1440,
                "document_width": 1440,
                "safe_error_visible": True,
            },
        ),
    )
    monkeypatch.setattr(capture_demo_media, "_wait_for_http", lambda *args, **kwargs: None)
    monkeypatch.setattr(capture_demo_media, "_stop", lambda process: None)
    monkeypatch.setattr(capture_demo_media, "_stop_proxy", lambda server, thread: None)
    monkeypatch.setattr(
        capture_demo_media, "_start_delay_proxy", lambda upstream, port, delay: (object(), object())
    )

    class DummyProcess:
        def poll(self) -> None:
            return None

    monkeypatch.setattr(capture_demo_media.subprocess, "Popen", lambda *args, **kwargs: DummyProcess())

    report = capture_demo_media.capture_demo(tmp_path, 18080, 18501, 18081, 1.5)

    assert report["engines"] == [
        "Playwright Chromium",
        "Playwright Firefox",
        "Playwright WebKit",
    ]
    assert report["assertions"]["keyboard_activation_verified"] is True
    assert report["assertions"]["match_loading_state_captured"] is True
    assert report["firefox_smoke"]["keyboard_activation"] is True
    assert report["webkit_smoke"]["keyboard_activation"] is True
    assert report["api_offline"]["safe_error_visible"] is True


def test_png_metadata_records_dimensions_and_rejects_other_files(tmp_path: Path) -> None:
    png = tmp_path / "capture.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", 390, 844))

    metadata = capture_demo_media.png_metadata(png)
    assert metadata["width"] == 390
    assert metadata["height"] == 844
    assert len(metadata["sha256"]) == 64

    invalid = tmp_path / "capture.txt"
    invalid.write_text("not a screenshot", encoding="utf-8")
    with pytest.raises(ValueError, match="Expected a PNG"):
        capture_demo_media.png_metadata(invalid)
