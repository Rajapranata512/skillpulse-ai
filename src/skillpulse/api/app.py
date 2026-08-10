"""Privacy-safe FastAPI service for extraction and explainable matching."""

from __future__ import annotations

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


def create_app(
    extractor: EntityExtractor | None = None,
    matcher: CVJobMatcher | None = None,
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
