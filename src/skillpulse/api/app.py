"""Privacy-safe FastAPI service for extraction and explainable matching."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from skillpulse.domain import (
    CONTRACT_VERSION,
    ExtractionRequest,
    ExtractionResponse,
    HealthResponse,
    MatchRequest,
    MatchResponse,
    ModelMetadataResponse,
)
from skillpulse.extraction import EntityExtractor
from skillpulse.matching import CVJobMatcher

from .rate_limit import SlidingWindowRateLimiter

RATE_LIMIT_ENV = "SKILLPULSE_API_RATE_LIMIT_PER_MINUTE"
RATE_LIMITED_PATHS = frozenset({"/v1/extract", "/v1/match"})


def _rate_limit_from_environment() -> int:
    raw = os.getenv(RATE_LIMIT_ENV, "0").strip()
    try:
        limit = int(raw)
    except ValueError as error:
        raise ValueError(f"{RATE_LIMIT_ENV} must be an integer.") from error
    if limit < 0:
        raise ValueError(f"{RATE_LIMIT_ENV} must be zero or positive.")
    return limit


def create_app(
    extractor: EntityExtractor | None = None,
    matcher: CVJobMatcher | None = None,
    *,
    rate_limit_per_minute: int | None = None,
) -> FastAPI:
    """Build an app with injectable deterministic engines for testing and deployment."""
    extraction_engine = extractor or EntityExtractor()
    matching_engine = matcher or CVJobMatcher(extractor=extraction_engine)
    service = FastAPI(
        title="SkillPulse AI API",
        summary="Bilingual job requirement extraction and explainable CV-job matching.",
        version=CONTRACT_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    configured_limit = _rate_limit_from_environment() if rate_limit_per_minute is None else rate_limit_per_minute
    limiter = SlidingWindowRateLimiter(configured_limit)

    @service.middleware("http")
    async def analysis_rate_limit(request: Request, call_next: Any) -> Any:
        limited = request.method == "POST" and request.url.path in RATE_LIMITED_PATHS
        if limited and not limiter.allow():
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": "60"},
                content={"detail": {"code": "rate_limit_exceeded", "message": "Batas demo tercapai; coba lagi nanti."}},
            )
        return await call_next(request)

    @service.exception_handler(ValueError)
    async def domain_validation_error(_request: Request, error: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "domain_validation_error",
                    "message": str(error),
                }
            },
        )

    @service.get("/health", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        return HealthResponse()

    @service.get("/v1/models", response_model=ModelMetadataResponse, tags=["metadata"])
    def model_metadata() -> ModelMetadataResponse:
        return ModelMetadataResponse()

    @service.post("/v1/extract", response_model=ExtractionResponse, tags=["intelligence"])
    def extract(payload: ExtractionRequest) -> ExtractionResponse:
        return ExtractionResponse.from_result(extraction_engine.extract(payload.text))

    @service.post("/v1/match", response_model=MatchResponse, tags=["intelligence"])
    def match(payload: MatchRequest) -> MatchResponse:
        return MatchResponse.from_result(matching_engine.match(payload.cv_text, payload.job_text))

    return service


app = create_app()


def main() -> None:
    try:
        import uvicorn
    except ImportError as error:
        raise RuntimeError('API server dependency missing. Install with: pip install -e ".[api]"') from error
    uvicorn.run(
        "skillpulse.api.app:app",
        host="127.0.0.1",
        port=8000,
        access_log=False,
    )


def openapi_contract() -> dict[str, Any]:
    """Expose a deterministic hook for contract-generation tests."""
    return app.openapi()


if __name__ == "__main__":
    main()
