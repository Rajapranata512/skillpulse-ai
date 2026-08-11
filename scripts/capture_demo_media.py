"""Capture public-safe SkillPulse browser states, loading, and cross-browser smoke QA."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CAPTURE_SPECS = (
    ("desktop-empty.png", "initial_empty"),
    ("desktop-loading.png", "match_loading"),
    ("desktop-match.png", "successful_match"),
    ("desktop-validation-error.png", "blank_input_error"),
    ("mobile-extraction.png", "successful_extraction"),
    ("desktop-api-offline.png", "api_offline_error"),
)
DESKTOP_VIEWPORT = {"width": 1440, "height": 1000}
MOBILE_VIEWPORT = {"width": 390, "height": 844}
OVERFLOW_TOLERANCE_PX = 2


def build_service_commands(
    api_port: int, ui_port: int, *, api_base_url: str | None = None
) -> tuple[list[str], list[str], dict[str, str]]:
    api_url = api_base_url or f"http://127.0.0.1:{api_port}"
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


def _start_delay_proxy(
    upstream_url: str, proxy_port: int, delay_seconds: float
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    allowed_paths = {"/health", "/v1/models", "/v1/extract", "/v1/match"}

    class DelayProxyHandler(BaseHTTPRequestHandler):
        def _forward(self) -> None:
            if self.path not in allowed_paths:
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else None
            if self.command == "POST" and self.path == "/v1/match":
                time.sleep(delay_seconds)
            request = Request(
                f"{upstream_url}{self.path}",
                data=body,
                headers={"Content-Type": "application/json"} if body else {},
                method=self.command,
            )
            try:
                with urlopen(request, timeout=10) as response:  # noqa: S310 - loopback proxy only
                    status = response.status
                    payload = response.read()
                    content_type = response.headers.get("Content-Type", "application/json")
            except HTTPError as error:
                status = error.code
                payload = error.read()
                content_type = error.headers.get("Content-Type", "application/json")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
            self._forward()

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
            self._forward()

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", proxy_port), DelayProxyHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="skillpulse-qa-proxy", daemon=True)
    thread.start()
    return server, thread


def _stop_proxy(server: ThreadingHTTPServer | None, thread: threading.Thread | None) -> None:
    if server is None or getattr(server, "_skillpulse_stopped", False):
        return
    server._skillpulse_stopped = True
    server.shutdown()
    server.server_close()
    if thread is not None:
        thread.join(timeout=5)


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


def _activate_with_keyboard(page: Any, locator: Any) -> None:
    locator.focus()
    is_focused = locator.evaluate("element => element === document.activeElement")
    if not is_focused:
        raise AssertionError("Expected the keyboard target to receive focus.")
    page.keyboard.press("Enter")


def _load_match_example_with_keyboard(page: Any) -> None:
    from playwright.sync_api import expect

    _activate_with_keyboard(page, page.get_by_role("button", name="Gunakan data contoh", exact=True))
    expect(page.get_by_label("CV text", exact=True)).not_to_have_value("", timeout=30_000)
    expect(page.get_by_label("Job description", exact=True)).not_to_have_value("", timeout=30_000)


def _complete_match_with_keyboard(
    page: Any, *, loading_output: Path | None = None
) -> dict[str, int | str] | None:
    _load_match_example_with_keyboard(page)
    _activate_with_keyboard(page, page.get_by_role("button", name="Analyze match", exact=True))
    loading_measurement = None
    if loading_output is not None:
        page.get_by_text("Menganalisis requirement dan skill gap", exact=False).wait_for(timeout=30_000)
        loading_measurement = _responsive_measurement(page, "chromium_desktop_loading")
        _save(page, loading_output, "desktop-loading.png")
    page.get_by_text("67.5/100", exact=True).wait_for(timeout=30_000)
    return loading_measurement


def _capture_chromium(
    playwright: Any, output: Path, ui_url: str
) -> tuple[list[dict[str, int | str]], list[dict[str, int | str]]]:
    from playwright.sync_api import expect

    measurements: list[dict[str, int | str]] = []
    browser = playwright.chromium.launch(headless=True)
    try:
        desktop = browser.new_context(viewport=DESKTOP_VIEWPORT, color_scheme="light")
        page = desktop.new_page()
        _wait_for_app(page, ui_url)
        measurements.append(_responsive_measurement(page, "chromium_desktop_empty"))
        _save(page, output, "desktop-empty.png")

        loading_measurement = _complete_match_with_keyboard(page, loading_output=output)
        if loading_measurement is None:
            raise AssertionError("Expected a loading-state measurement.")
        measurements.append(loading_measurement)
        measurements.append(_responsive_measurement(page, "chromium_desktop_match_keyboard"))
        _save(page, output, "desktop-match.png")

        page.get_by_label("CV text", exact=True).fill("")
        _activate_with_keyboard(page, page.get_by_role("button", name="Analyze match", exact=True))
        page.get_by_text("Isi CV dan job description sebelum menjalankan analisis.", exact=True).wait_for(
            timeout=30_000
        )
        measurements.append(_responsive_measurement(page, "chromium_desktop_validation_error"))
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
        extraction_tab = page.get_by_role("tab", name="Extract Job", exact=True)
        extraction_tab.click()
        page.get_by_role("button", name="Gunakan contoh extraction", exact=True).click()
        extraction_text = page.get_by_label("Job description to extract", exact=True)
        expect(extraction_text).to_be_visible(timeout=30_000)
        expect(extraction_text).not_to_have_value("", timeout=30_000)
        page.get_by_role("button", name="Extract requirements", exact=True).click()
        technical_heading = page.get_by_text("Technical skills", exact=True)
        technical_heading.wait_for(state="attached", timeout=30_000)
        extraction_tab.click()
        technical_heading.wait_for(state="visible", timeout=30_000)
        page.get_by_text("Power BI", exact=True).wait_for(timeout=30_000)
        measurements.append(_responsive_measurement(page, "chromium_mobile_extraction"))
        _save(page, output, "mobile-extraction.png")
        mobile.close()
    finally:
        browser.close()

    return [], measurements


def _smoke_secondary_browser(
    playwright: Any, ui_url: str, engine_name: str
) -> dict[str, int | str | bool]:
    browser_type = getattr(playwright, engine_name)
    browser = browser_type.launch(headless=True)
    try:
        context = browser.new_context(viewport=DESKTOP_VIEWPORT, color_scheme="light")
        page = context.new_page()
        _wait_for_app(page, ui_url)
        _complete_match_with_keyboard(page)
        measurement = _responsive_measurement(page, f"{engine_name}_desktop_match_keyboard")
        context.close()
    finally:
        browser.close()
    return measurement | {"keyboard_activation": True}


def _capture_api_offline(
    playwright: Any, output: Path, ui_url: str, stop_proxy: Callable[[], None]
) -> dict[str, int | str | bool]:
    browser = playwright.chromium.launch(headless=True)
    try:
        context = browser.new_context(viewport=DESKTOP_VIEWPORT, color_scheme="light")
        page = context.new_page()
        _wait_for_app(page, ui_url)
        _load_match_example_with_keyboard(page)
        stop_proxy()
        _activate_with_keyboard(page, page.get_by_role("button", name="Analyze match", exact=True))
        page.get_by_text("SkillPulse API tidak dapat dihubungi", exact=False).first.wait_for(timeout=30_000)
        measurement = _responsive_measurement(page, "chromium_desktop_api_offline")
        _save(page, output, "desktop-api-offline.png")
        context.close()
    finally:
        browser.close()
    return measurement | {"safe_error_visible": True}


def _run_browser_qa(
    output: Path, ui_url: str, stop_proxy: Callable[[], None]
) -> tuple[
    list[dict[str, int | str]],
    list[dict[str, int | str]],
    dict[str, int | str | bool],
    dict[str, int | str | bool],
    dict[str, int | str | bool],
]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        captures, measurements = _capture_chromium(playwright, output, ui_url)
        firefox = _smoke_secondary_browser(playwright, ui_url, "firefox")
        webkit = _smoke_secondary_browser(playwright, ui_url, "webkit")
        offline = _capture_api_offline(playwright, output, ui_url, stop_proxy)
    captures = [png_metadata(output / filename) | {"state": state} for filename, state in CAPTURE_SPECS]
    return captures, measurements, firefox, webkit, offline


def capture_demo(
    output: Path, api_port: int, ui_port: int, proxy_port: int, delay_seconds: float
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    for filename, _ in CAPTURE_SPECS:
        (output / filename).unlink(missing_ok=True)
    (output / "browser-qa.json").unlink(missing_ok=True)

    proxy_url = f"http://127.0.0.1:{proxy_port}"
    api_command, ui_command, environment = build_service_commands(
        api_port, ui_port, api_base_url=proxy_url
    )
    api_process: subprocess.Popen[bytes] | None = None
    ui_process: subprocess.Popen[bytes] | None = None
    proxy_server: ThreadingHTTPServer | None = None
    proxy_thread: threading.Thread | None = None
    with tempfile.TemporaryDirectory(prefix="skillpulse-browser-qa-") as temporary_directory:
        temp = Path(temporary_directory)
        with (temp / "api.log").open("wb") as api_log, (temp / "ui.log").open("wb") as ui_log:
            try:
                api_process = subprocess.Popen(api_command, stdout=api_log, stderr=subprocess.STDOUT)
                _wait_for_http(f"http://127.0.0.1:{api_port}/health", api_process, "API")
                proxy_server, proxy_thread = _start_delay_proxy(
                    f"http://127.0.0.1:{api_port}", proxy_port, delay_seconds
                )
                ui_process = subprocess.Popen(
                    ui_command, stdout=ui_log, stderr=subprocess.STDOUT, env=environment
                )
                _wait_for_http(f"http://127.0.0.1:{ui_port}/_stcore/health", ui_process, "UI")
                def stop_proxy() -> None:
                    _stop_proxy(proxy_server, proxy_thread)

                captures, measurements, firefox, webkit, offline = _run_browser_qa(
                    output, f"http://127.0.0.1:{ui_port}", stop_proxy
                )
            finally:
                _stop(ui_process)
                _stop_proxy(proxy_server, proxy_thread)
                _stop(api_process)

    report: dict[str, Any] = {
        "artifact_type": "SkillPulse public-safe multi-engine responsive and resilience QA",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit": os.getenv("GITHUB_SHA", "local-uncommitted-run"),
        "engines": ["Playwright Chromium", "Playwright Firefox", "Playwright WebKit"],
        "status": "passed",
        "privacy": {
            "input_source": "repository public-safe examples only",
            "raw_user_cv_used": False,
            "external_application_network": False,
            "service_bind_address": "127.0.0.1",
            "proxy_allowlist": ["/health", "/v1/models", "/v1/extract", "/v1/match"],
        },
        "assertions": {
            "horizontal_overflow_tolerance_px": OVERFLOW_TOLERANCE_PX,
            "all_states_within_viewport": True,
            "keyboard_activation_verified": True,
            "match_loading_state_captured": True,
            "api_offline_safe_error_captured": True,
            "firefox_match_smoke": True,
            "webkit_match_smoke": True,
            "api_access_log_disabled": True,
            "services_stopped_after_capture": True,
        },
        "measurements": measurements,
        "firefox_smoke": firefox,
        "webkit_smoke": webkit,
        "api_offline": offline,
        "captures": captures,
        "limitations": [
            "Automated keyboard activation does not replace screen-reader or human usability review.",
            "Playwright WebKit is useful compatibility evidence but is not a real Safari/device review.",
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
    parser.add_argument("--proxy-port", type=int, default=18081)
    parser.add_argument("--delay-seconds", type=float, default=1.5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = capture_demo(
        args.output, args.api_port, args.ui_port, args.proxy_port, args.delay_seconds
    )
    print(
        f"Browser QA: PASS ({len(report['captures'])} captures, "
        f"{len(report['measurements'])} Chromium states, Firefox/WebKit smoke)"
    )


if __name__ == "__main__":
    main()
