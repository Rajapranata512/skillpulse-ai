from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from skillpulse.release import deployment
from skillpulse.release.public_runtime import PublicRuntimeConfig, child_environment, runtime_commands

ROOT = Path(__file__).parents[1]


def test_public_runtime_defaults_to_loopback() -> None:
    config = PublicRuntimeConfig.from_environment({})
    _, ui = runtime_commands(config)
    assert config.public_host == "127.0.0.1"
    assert "--server.address=127.0.0.1" in ui


def test_public_runtime_keeps_api_loopback_only_and_hardens_streamlit() -> None:
    config = PublicRuntimeConfig(
        public_host="0.0.0.0",
        public_port=10_000,
        api_port=8_000,
        rate_limit_per_minute=30,
    )
    api, ui = runtime_commands(config)
    environment = child_environment(config, {"SAFE_EXISTING": "value"})

    assert api[api.index("--host") + 1] == "127.0.0.1"
    assert "--no-access-log" in api
    assert "--server.address=0.0.0.0" in ui
    assert "--server.enableCORS=true" in ui
    assert "--server.enableXsrfProtection=true" in ui
    assert "--browser.gatherUsageStats=false" in ui
    assert environment == {
        "SAFE_EXISTING": "value",
        "SKILLPULSE_API_URL": "http://127.0.0.1:8000",
        "SKILLPULSE_API_RATE_LIMIT_PER_MINUTE": "30",
    }


@pytest.mark.parametrize(
    "environment",
    [
        {"PORT": "8000"},
        {"PORT": "not-a-port"},
        {"PORT": "80"},
        {"SKILLPULSE_PUBLIC_HOST": "external.example"},
        {"SKILLPULSE_API_RATE_LIMIT_PER_MINUTE": "-1"},
    ],
)
def test_public_runtime_rejects_unsafe_configuration(environment: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        PublicRuntimeConfig.from_environment(environment)


def test_render_blueprint_is_single_service_stateless_and_check_gated() -> None:
    blueprint = yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))

    assert set(blueprint) == {"services"}
    assert len(blueprint["services"]) == 1
    service = blueprint["services"][0]
    assert service["type"] == "web"
    assert service["runtime"] == "docker"
    assert service["plan"] == "free"
    assert service["region"] == "singapore"
    assert service["dockerfilePath"] == "./deploy/render/Dockerfile"
    assert service["healthCheckPath"] == "/_stcore/health"
    assert service["autoDeployTrigger"] == "checksPass"
    assert "databases" not in blueprint
    assert all("sync" not in item for item in service["envVars"])


def test_public_container_is_nonroot_and_excludes_private_data() -> None:
    dockerfile = (ROOT / "deploy" / "render" / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY pyproject.toml README.md LICENSE ./" in dockerfile
    assert "USER skillpulse" in dockerfile
    assert 'CMD ["python", "-m", "skillpulse.release.public_runtime"]' in dockerfile
    assert "COPY data" not in dockerfile
    assert "COPY reports" not in dockerfile


def test_deployment_url_validation_is_https_only() -> None:
    assert deployment.normalize_public_url("https://skillpulse-ai.onrender.com") == (
        "https://skillpulse-ai.onrender.com/"
    )
    for unsafe in (
        "http://skillpulse-ai.onrender.com",
        "https://user" + ":password@" + "skillpulse-ai.onrender.com",
        "https://skillpulse-ai.onrender.com?token=value",
        "https://skillpulse-ai.onrender.com:8443",
    ):
        with pytest.raises(ValueError):
            deployment.normalize_public_url(unsafe)


def test_deployment_smoke_detects_ui_and_nonpublic_api(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://skillpulse-ai.onrender.com/_stcore/health": (200, "text/plain", b"ok"),
        "https://skillpulse-ai.onrender.com/": (200, "text/html", b"<html>Streamlit</html>"),
        "https://skillpulse-ai.onrender.com/v1/models": (404, "text/plain", b"not found"),
    }
    monkeypatch.setattr(deployment, "_fetch", responses.__getitem__)

    result = deployment.verify_public_deployment("https://skillpulse-ai.onrender.com")

    assert result.passed
    assert result.api_loopback_only
