"""Small standard-library client for the versioned SkillPulse API."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SkillPulseAPIError(RuntimeError):
    """User-safe API connectivity or domain error."""


class SkillPulseAPIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, payload: dict[str, str] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
            method="POST" if data else "GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - local/configured API is intentional
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8")).get("detail", {})
                message = detail.get("message") if isinstance(detail, dict) else str(detail)
            except (json.JSONDecodeError, UnicodeDecodeError):
                message = f"API returned HTTP {error.code}."
            raise SkillPulseAPIError(message or f"API returned HTTP {error.code}.") from error
        except (URLError, TimeoutError) as error:
            raise SkillPulseAPIError(
                f"SkillPulse API tidak dapat dihubungi di {self.base_url}. Jalankan `skillpulse-api` terlebih dahulu."
            ) from error

    def health(self) -> dict[str, Any]:
        return self._request("/health")

    def extract(self, text: str) -> dict[str, Any]:
        return self._request("/v1/extract", {"text": text})

    def match(self, cv_text: str, job_text: str) -> dict[str, Any]:
        return self._request("/v1/match", {"cv_text": cv_text, "job_text": job_text})
