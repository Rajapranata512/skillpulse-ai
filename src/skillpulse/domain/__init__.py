"""Stable transport-neutral contracts for SkillPulse services."""

from .contracts import (
    CONTRACT_VERSION,
    TAXONOMY_VERSION,
    ExtractionRequest,
    ExtractionResponse,
    HealthResponse,
    MatchRequest,
    MatchResponse,
    ModelMetadataResponse,
)

__all__ = [
    "CONTRACT_VERSION",
    "TAXONOMY_VERSION",
    "ExtractionRequest",
    "ExtractionResponse",
    "HealthResponse",
    "MatchRequest",
    "MatchResponse",
    "ModelMetadataResponse",
]
