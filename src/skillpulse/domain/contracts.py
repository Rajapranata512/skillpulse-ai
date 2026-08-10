"""Versioned Pydantic contracts shared by future API and presentation layers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skillpulse.extraction.engine import ExtractionResult
from skillpulse.matching.engine import MatchResult

CONTRACT_VERSION = "1.0.0"
TAXONOMY_VERSION = "0.2.0"
EXTRACTION_MODEL_VERSION = "taxonomy-rules-0.2.0"
MATCHING_MODEL_VERSION = "exact-taxonomy-0.1.0"
MAX_TEXT_LENGTH = 50_000


class StrictContract(BaseModel):
    """Reject undeclared fields so accidental API drift fails loudly."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class ExtractionRequest(StrictContract):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class MatchRequest(StrictContract):
    cv_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    job_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class EntityEvidence(StrictContract):
    canonical: str = Field(min_length=1)
    matched_text: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_span(self) -> EntityEvidence:
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class ExtractionResponse(StrictContract):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    model_version: Literal[EXTRACTION_MODEL_VERSION] = EXTRACTION_MODEL_VERSION
    taxonomy_version: Literal[TAXONOMY_VERSION] = TAXONOMY_VERSION
    technical_skills: list[EntityEvidence]
    tools: list[EntityEvidence]
    soft_skills: list[EntityEvidence]
    education: list[str]
    experience_years: float | None = Field(default=None, ge=0)
    seniority: Literal["entry", "mid", "senior", "unknown"]
    work_arrangement: Literal["remote", "hybrid", "onsite", "unknown"]

    @classmethod
    def from_result(cls, result: ExtractionResult) -> ExtractionResponse:
        return cls.model_validate(result.to_dict())


class CategoryScoreResponse(StrictContract):
    category: str
    applicable: bool
    configured_weight: float = Field(ge=0, le=1)
    effective_weight: float = Field(ge=0, le=1)
    score: float | None = Field(default=None, ge=0, le=1)
    matched: list[str]
    missing: list[str]
    candidate_value: str | float | None
    job_requirement: str | float | None
    explanation: str


class LearningPriorityResponse(StrictContract):
    skill: str
    category: str
    priority: Literal["high", "medium", "low"]
    reason: str


class MatchResponse(StrictContract):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    model_version: Literal[MATCHING_MODEL_VERSION] = MATCHING_MODEL_VERSION
    taxonomy_version: Literal[TAXONOMY_VERSION] = TAXONOMY_VERSION
    overall_score: float = Field(ge=0, le=100)
    verdict: Literal["strong_match", "potential_match", "skill_gap"]
    matched_skills: list[str]
    missing_skills: list[str]
    category_scores: list[CategoryScoreResponse]
    learning_priorities: list[LearningPriorityResponse]
    disclaimer: str

    @classmethod
    def from_result(cls, result: MatchResult) -> MatchResponse:
        return cls.model_validate(result.to_dict())


class ModelMetadataResponse(StrictContract):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    taxonomy_version: Literal[TAXONOMY_VERSION] = TAXONOMY_VERSION
    extraction_model_version: Literal[EXTRACTION_MODEL_VERSION] = EXTRACTION_MODEL_VERSION
    matching_model_version: Literal[MATCHING_MODEL_VERSION] = MATCHING_MODEL_VERSION
    semantic_challenger_status: Literal["evaluated_not_promoted"] = "evaluated_not_promoted"
    decision_support_only: Literal[True] = True
    stores_input_text: Literal[False] = False


class HealthResponse(StrictContract):
    status: Literal["ok"] = "ok"
    service: Literal["skillpulse-api"] = "skillpulse-api"
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION

def build_contract_artifact() -> dict[str, Any]:
    """Return deterministic JSON Schemas for API implementation and contract tests."""
    models = (
        ExtractionRequest,
        ExtractionResponse,
        MatchRequest,
        MatchResponse,
        ModelMetadataResponse,
        HealthResponse,
    )
    return {
        "artifact_type": "SkillPulse transport-neutral domain contract",
        "contract_version": CONTRACT_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "schemas": {model.__name__: model.model_json_schema() for model in models},
        "privacy": {
            "raw_cv_persistence": False,
            "request_body_logging": False,
            "decision_support_only": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/api_contract_v1.json"))
    args = parser.parse_args()
    artifact = build_contract_artifact()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "contract_version": CONTRACT_VERSION}, indent=2))


if __name__ == "__main__":
    main()
