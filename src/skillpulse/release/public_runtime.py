"""Run the public Streamlit UI with a loopback-only FastAPI process."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_PUBLIC_PORT = 10_000
DEFAULT_API_PORT = 8_000
DEFAULT_RATE_LIMIT = 30
STARTUP_TIMEOUT_SECONDS = 30.0


def _positive_port(value: str, *, name: str) -> int:
    try:
        port = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer port.") from error
    if not 1_024 <= port <= 65_535:
        raise ValueError(f"{name} must be between 1024 and 65535.")
    return port


def _nonnegative_integer(value: str, *, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error
    if parsed < 0:
        raise ValueError(f"{name} must be zero or positive.")
    return parsed


@dataclass(frozen=True)
class PublicRuntimeConfig:
    public_host: str = "127.0.0.1"
    public_port: int = DEFAULT_PUBLIC_PORT
    api_port: int = DEFAULT_API_PORT
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> PublicRuntimeConfig:
        source = os.environ if environment is None else environment
        config = cls(
            public_host=source.get("SKILLPULSE_PUBLIC_HOST", "127.0.0.1").strip(),
            public_port=_positive_port(source.get("PORT", str(DEFAULT_PUBLIC_PORT)), name="PORT"),
            api_port=_positive_port(
                source.get("SKILLPULSE_INTERNAL_API_PORT", str(DEFAULT_API_PORT)),
                name="SKILLPULSE_INTERNAL_API_PORT",
            ),
            rate_limit_per_minute=_nonnegative_integer(
                source.get("SKILLPULSE_API_RATE_LIMIT_PER_MINUTE", str(DEFAULT_RATE_LIMIT)),
                name="SKILLPULSE_API_RATE_LIMIT_PER_MINUTE",
            ),
        )
        if config.public_host not in {"127.0.0.1", "0.0.0.0"}:
            raise ValueError("SKILLPULSE_PUBLIC_HOST must be an exact supported bind address.")
        if config.public_port == config.api_port:
            raise ValueError("Public Streamlit and internal API ports must differ.")
        return config


def runtime_commands(config: PublicRuntimeConfig) -> tuple[list[str], list[str]]:
    app_path = Path(__file__).resolve().parents[1] / "ui" / "app.py"
    api = [
        sys.executable,
        "-m",
        "uvicorn",
        "skillpulse.api.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(config.api_port),
        "--no-access-log",
    ]
    ui = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        f"--server.port={config.public_port}",
        f"--server.address={config.public_host}",
        "--server.headless=true",
        "--server.enableCORS=true",
        "--server.enableXsrfProtection=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    return api, ui


def child_environment(config: PublicRuntimeConfig, environment: Mapping[str, str] | None = None) -> dict[str, str]:
    child = dict(os.environ if environment is None else environment)
    child["SKILLPULSE_API_URL"] = f"http://127.0.0.1:{config.api_port}"
    child["SKILLPULSE_API_RATE_LIMIT_PER_MINUTE"] = str(config.rate_limit_per_minute)
    return child


def _wait_for_api(process: subprocess.Popen[bytes], port: int) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    health_url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Internal API stopped during startup.")
        try:
            with urlopen(health_url, timeout=1.0) as response:  # noqa: S310 - fixed loopback URL
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.2)
    raise RuntimeError("Internal API did not become healthy before the startup deadline.")


def _stop_processes(processes: Sequence[subprocess.Popen[bytes]]) -> None:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 10.0
    for process in reversed(processes):
        if process.poll() is not None:
            continue
        try:
            process.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)


def run(config: PublicRuntimeConfig | None = None) -> int:
    runtime = config or PublicRuntimeConfig.from_environment()
    api_command, ui_command = runtime_commands(runtime)
    environment = child_environment(runtime)
    processes: list[subprocess.Popen[bytes]] = []
    stopping = False

    def request_stop(_signum: int, _frame: FrameType | None) -> None:
        nonlocal stopping
        stopping = True

    previous_handlers: dict[signal.Signals, signal.Handlers] = {}
    for event in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[event] = signal.signal(event, request_stop)
    try:
        api_process = subprocess.Popen(api_command, env=environment)
        processes.append(api_process)
        _wait_for_api(api_process, runtime.api_port)
        ui_process = subprocess.Popen(ui_command, env=environment)
        processes.append(ui_process)
        print(f"SkillPulse public runtime ready on port {runtime.public_port}; internal API is loopback-only.")
        while not stopping:
            api_status = api_process.poll()
            ui_status = ui_process.poll()
            if api_status is not None:
                raise RuntimeError(f"Internal API exited unexpectedly with status {api_status}.")
            if ui_status is not None:
                return ui_status
            time.sleep(0.5)
        return 0
    finally:
        _stop_processes(processes)
        for event, handler in previous_handlers.items():
            signal.signal(event, handler)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    raise SystemExit(run())


if __name__ == "__main__":
    main()
