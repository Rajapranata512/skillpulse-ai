"""Capture public-safe SkillPulse browser states and verify responsive overflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

CAPTURE_SPECS = (
    ("desktop-empty.png", "initial_empty"),
    ("desktop-match.png", "successful_match"),
    ("desktop-validation-error.png", "blank_input_error"),
    ("mobile-extraction.png", "successful_extraction"),
)
DESKTOP_VIEWPORT = {"width": 1440, "height": 1000}
MOBILE_VIEWPORT = {"width": 390, "height": 844}
OVERFLOW_TOLERANCE_PX = 2


def build_service_commands(api_port: int, ui_port: int) -> tuple[list[str], list[str], dict[str, str]]:
    api_url = f"http://127.0.0.1:{api_port}"
    api_command = [
        sys.executable,
        "-m",
        "uvicorn",
        "skillpulse.api.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(api_port),
        "--no-access-log",
    ]
    ui_command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "src/skillpulse/ui/app.py",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(ui_port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    environment = {**os.environ, "SKILLPULSE_API_URL": api_url}
    return api_command, ui_command, environment


def _wait_for_http(url: str, process: subprocess.Popen[bytes], service: str, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last_error = "not ready"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{service} exited with code {process.returncode} before becoming healthy.")
        try:
            with urlopen(url, timeout=2) as response:  # noqa: S310 - loopback service is intentional
                if response.status == 200:
                    return
        except (URLError, TimeoutError, ConnectionError) as error:
            last_error = str(error)
        time.sleep(0.25)
    raise RuntimeError(f"{service} did not become healthy at {url}: {last_error}")


def _stop(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def overflow_is_acceptable(viewport_width: int, document_width: int) -> bool:
    return document_width <= viewport_width + OVERFLOW_TOLERANCE_PX


def _responsive_measurement(page: Any, label: str) -> dict[str, int | str]:
    measurement = page.evaluate(
        """() => ({
          viewport_width: window.innerWidth,
          document_width: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)
        })"""
    )
    viewport_width = int(measurement["viewport_width"])
    document_width = int(measurement["document_width"])
    if not overflow_is_acceptable(viewport_width, document_width):
        raise AssertionError(
            f"{label} has horizontal overflow: document={document_width}px viewport={viewport_width}px"
        )
    return {"state": label, "viewport_width": viewport_width, "document_width": document_width}


def png_metadata(path: Path) -> dict[str, int | str]:
    content = path.read_bytes()
    if len(content) < 24 or content[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Expected a PNG capture: {path.name}")
    width, height = struct.unpack(">II", content[16:24])
    return {
        "file": path.name,
        "bytes": len(content),
        "width": width,
        "height": height,
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _save(page: Any, output: Path, filename: str) -> None:
    page.screenshot(path=output / filename, full_page=True, animations="disabled")


def _wait_for_app(page: Any, ui_url: str) -> None:
    page.goto(ui_url, wait_until="domcontentloaded", timeout=45_000)
    page.get_by_role("heading", name="SkillPulse AI", exact=True).wait_for(timeout=30_000)
    # Streamlit intentionally collapses the sidebar on a mobile viewport, so the
    # health text remains attached but is not visible until the sidebar is opened.
    page.get_by_text("API online", exact=False).wait_for(state="attached", timeout=30_000)


def _capture(output: Path, ui_url: str) -> tuple[list[dict[str, int | str]], list[dict[str, int | str]]]:
    from playwright.sync_api import sync_playwright

    measurements: list[dict[str, int | str]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            desktop = browser.new_context(viewport=DESKTOP_VIEWPORT, color_scheme="light")
            page = desktop.new_page()
            _wait_for_app(page, ui_url)
            measurements.append(_responsive_measurement(page, "desktop_empty"))
            _save(page, output, "desktop-empty.png")

            page.get_by_role("button", name="Gunakan data contoh", exact=True).click()
            page.get_by_role("button", name="Analyze match", exact=True).click()
            page.get_by_text("67.5/100", exact=True).wait_for(timeout=30_000)
            measurements.append(_responsive_measurement(page, "desktop_match"))
            _save(page, output, "desktop-match.png")

            page.get_by_label("CV text", exact=True).fill("")
            page.get_by_role("button", name="Analyze match", exact=True).click()
            page.get_by_text("Isi CV dan job description sebelum menjalankan analisis.", exact=True).wait_for(
                timeout=30_000
            )
            measurements.append(_responsive_measurement(page, "desktop_validation_error"))
            _save(page, output, "desktop-validation-error.png")
            desktop.close()

            mobile = browser.new_context(
                viewport=MOBILE_VIEWPORT,
                color_scheme="light",
                device_scale_factor=1,
                is_mobile=True,
            )
            page = mobile.new_page()
            _wait_for_app(page, ui_url)
            page.get_by_role("tab", name="Extract Job", exact=True).click()
            page.get_by_role("button", name="Gunakan contoh extraction", exact=True).click()
            page.get_by_role("button", name="Extract requirements", exact=True).click()
            page.get_by_text("Technical skills", exact=True).wait_for(timeout=30_000)
            page.get_by_text("Power BI", exact=True).wait_for(timeout=30_000)
            measurements.append(_responsive_measurement(page, "mobile_extraction"))
            _save(page, output, "mobile-extraction.png")
            mobile.close()
        finally:
            browser.close()

    captures = [png_metadata(output / filename) | {"state": state} for filename, state in CAPTURE_SPECS]
    return captures, measurements


def capture_demo(output: Path, api_port: int, ui_port: int) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    for filename, _ in CAPTURE_SPECS:
        (output / filename).unlink(missing_ok=True)
    (output / "browser-qa.json").unlink(missing_ok=True)

    api_command, ui_command, environment = build_service_commands(api_port, ui_port)
    api_process: subprocess.Popen[bytes] | None = None
    ui_process: subprocess.Popen[bytes] | None = None
    with tempfile.TemporaryDirectory(prefix="skillpulse-browser-qa-") as temporary_directory:
        temp = Path(temporary_directory)
        with (temp / "api.log").open("wb") as api_log, (temp / "ui.log").open("wb") as ui_log:
            try:
                api_process = subprocess.Popen(api_command, stdout=api_log, stderr=subprocess.STDOUT)
                _wait_for_http(f"http://127.0.0.1:{api_port}/health", api_process, "API")
                ui_process = subprocess.Popen(
                    ui_command,
                    stdout=ui_log,
                    stderr=subprocess.STDOUT,
                    env=environment,
                )
                _wait_for_http(f"http://127.0.0.1:{ui_port}/_stcore/health", ui_process, "UI")
                captures, measurements = _capture(output, f"http://127.0.0.1:{ui_port}")
            finally:
                _stop(ui_process)
                _stop(api_process)

    report: dict[str, Any] = {
        "artifact_type": "SkillPulse public-safe Chromium responsive QA",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit": os.getenv("GITHUB_SHA", "local-uncommitted-run"),
        "engine": "Playwright Chromium",
        "status": "passed",
        "privacy": {
            "input_source": "repository public-safe examples only",
            "raw_user_cv_used": False,
            "external_application_network": False,
            "service_bind_address": "127.0.0.1",
        },
        "assertions": {
            "horizontal_overflow_tolerance_px": OVERFLOW_TOLERANCE_PX,
            "all_states_within_viewport": True,
            "api_access_log_disabled": True,
            "services_stopped_after_capture": True,
        },
        "measurements": measurements,
        "captures": captures,
        "limitations": [
            "Chromium automation does not replace keyboard, screen-reader, or cross-browser human review.",
            "Captured media uses synthetic examples and is CI evidence, not public deployment evidence.",
        ],
    }
    (output / "browser-qa.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/browser-qa"))
    parser.add_argument("--api-port", type=int, default=18080)
    parser.add_argument("--ui-port", type=int, default=18501)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = capture_demo(args.output, args.api_port, args.ui_port)
    print(
        f"Browser QA: PASS ({len(report['captures'])} captures, "
        f"{len(report['measurements'])} responsive states)"
    )


if __name__ == "__main__":
    main()
