"""Privacy-safe smoke checks for the public portfolio deployment."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class DeploymentSmokeResult:
    base_url: str
    https: bool
    ui_health: bool
    landing_page: bool
    api_loopback_only: bool

    @property
    def passed(self) -> bool:
        return self.https and self.ui_health and self.landing_page and self.api_loopback_only


def normalize_public_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Public deployment URL must use HTTPS and include a hostname.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Public deployment URL must not contain credentials, query parameters, or fragments.")
    if parsed.port not in (None, 443):
        raise ValueError("Public deployment URL must use the standard HTTPS port.")
    return f"https://{parsed.hostname}{parsed.path.rstrip('/')}/"


def _fetch(url: str) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "SkillPulse-Deployment-Smoke/1.0"})
    try:
        with urlopen(request, timeout=30.0) as response:  # noqa: S310 - owner-approved HTTPS URL
            return response.status, response.headers.get("Content-Type", ""), response.read(200_000)
    except HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read(200_000)
    except (OSError, URLError) as error:
        raise RuntimeError("Public deployment could not be reached.") from error


def verify_public_deployment(value: str) -> DeploymentSmokeResult:
    base_url = normalize_public_url(value)
    health_status, _, health_body = _fetch(urljoin(base_url, "_stcore/health"))
    landing_status, landing_type, landing_body = _fetch(base_url)
    _, model_type, model_body = _fetch(urljoin(base_url, "v1/models"))
    api_exposed = "application/json" in model_type.lower() and b'"contract_version"' in model_body
    return DeploymentSmokeResult(
        base_url=base_url,
        https=True,
        ui_health=health_status == 200 and health_body.strip().lower() == b"ok",
        landing_page=landing_status == 200
        and "text/html" in landing_type.lower()
        and b"streamlit" in landing_body.lower(),
        api_loopback_only=not api_exposed,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Public HTTPS URL, for example https://skillpulse-ai.onrender.com")
    args = parser.parse_args(argv)
    result = verify_public_deployment(args.url)
    print(json.dumps({**asdict(result), "passed": result.passed}, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
