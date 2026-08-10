"""Explainable baseline for matching a CV against a job description."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from skillpulse.extraction import EntityExtractor, ExtractionResult

DEFAULT_WEIGHTS = {
    "technical_skills": 0.30,
    "tools": 0.25,
    "soft_skills": 0.10,
    "education": 0.10,
    "experience": 0.15,
    "seniority": 0.05,
    "work_arrangement": 0.05,
}

EDUCATION_LEVELS = {
    "High School": 1,
    "Diploma": 2,
    "Bachelor": 3,
    "Master": 4,
    "Doctorate": 5,
}

SENIORITY_LEVELS = {"entry": 1, "mid": 2, "senior": 3}


@dataclass(frozen=True)
class CategoryScore:
    """One auditable component of a match score."""

    category: str
    applicable: bool
    configured_weight: float
    effective_weight: float
    score: float | None
    matched: list[str]
    missing: list[str]
    candidate_value: str | float | None
    job_requirement: str | float | None
    explanation: str


@dataclass(frozen=True)
class LearningPriority:
    skill: str
    category: str
    priority: str
    reason: str


@dataclass(frozen=True)
class MatchResult:
    """Serializable result returned by the matching baseline."""

    overall_score: float
    verdict: str
    matched_skills: list[str]
    missing_skills: list[str]
    category_scores: list[CategoryScore]
    learning_priorities: list[LearningPriority]
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical_set(result: ExtractionResult, attribute: str) -> set[str]:
    return {item.canonical for item in getattr(result, attribute)}


def _set_category(
    category: str,
    candidate: set[str],
    required: set[str],
    weight: float,
) -> CategoryScore:
    matched = sorted(candidate & required)
    missing = sorted(required - candidate)
    if not required:
        return CategoryScore(
            category=category,
            applicable=False,
            configured_weight=weight,
            effective_weight=0.0,
            score=None,
            matched=[],
            missing=[],
            candidate_value=None,
            job_requirement=None,
            explanation="Tidak ada persyaratan yang terdeteksi pada job description.",
        )
    score = len(matched) / len(required)
    return CategoryScore(
        category=category,
        applicable=True,
        configured_weight=weight,
        effective_weight=0.0,
        score=round(score, 4),
        matched=matched,
        missing=missing,
        candidate_value=None,
        job_requirement=None,
        explanation=f"{len(matched)} dari {len(required)} persyaratan cocok.",
    )


def _education_category(
    candidate: list[str], required: list[str], weight: float
) -> CategoryScore:
    if not required:
        return CategoryScore(
            "education", False, weight, 0.0, None, [], [], None, None,
            "Tidak ada persyaratan pendidikan yang terdeteksi.",
        )
    candidate_level = max((EDUCATION_LEVELS[item] for item in candidate), default=0)
    required_name = max(required, key=lambda item: EDUCATION_LEVELS[item])
    required_level = EDUCATION_LEVELS[required_name]
    candidate_name = (
        max(candidate, key=lambda item: EDUCATION_LEVELS[item]) if candidate else "unknown"
    )
    score = 1.0 if candidate_level >= required_level else candidate_level / required_level
    return CategoryScore(
        "education", True, weight, 0.0, round(score, 4),
        [required_name] if score == 1.0 else [],
        [] if score == 1.0 else [required_name],
        candidate_name, required_name,
        "Pendidikan memenuhi persyaratan minimum." if score == 1.0
        else "Pendidikan yang terdeteksi belum mencapai persyaratan minimum.",
    )


def _experience_category(
    candidate: float | None, required: float | None, weight: float
) -> CategoryScore:
    if required is None:
        return CategoryScore(
            "experience", False, weight, 0.0, None, [], [], candidate, None,
            "Tidak ada persyaratan pengalaman yang terdeteksi.",
        )
    score = 0.0 if candidate is None else min(candidate / required, 1.0) if required > 0 else 1.0
    meets = score == 1.0
    return CategoryScore(
        "experience", True, weight, 0.0, round(score, 4),
        [f"{required:g} years"] if meets else [],
        [] if meets else [f"{required:g} years"],
        candidate, required,
        "Pengalaman memenuhi persyaratan minimum." if meets
        else "Pengalaman yang terdeteksi masih di bawah persyaratan minimum.",
    )


def _label_category(
    category: str,
    candidate: str,
    required: str,
    weight: float,
) -> CategoryScore:
    if required == "unknown":
        return CategoryScore(
            category, False, weight, 0.0, None, [], [], candidate, None,
            f"Tidak ada persyaratan {category.replace('_', ' ')} yang terdeteksi.",
        )
    if candidate == "unknown":
        score = 0.0
    elif category == "seniority":
        distance = abs(SENIORITY_LEVELS[candidate] - SENIORITY_LEVELS[required])
        score = 1.0 if distance == 0 else 0.5 if distance == 1 else 0.0
    else:
        score = 1.0 if candidate == required else 0.0
    return CategoryScore(
        category, True, weight, 0.0, score,
        [required] if score == 1.0 else [],
        [] if score == 1.0 else [required],
        candidate, required,
        "Kriteria cocok." if score == 1.0 else "Kriteria belum cocok atau belum tercantum di CV.",
    )


class CVJobMatcher:
    """Compare extracted requirements and expose every score component."""

    def __init__(
        self,
        extractor: EntityExtractor | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.extractor = extractor or EntityExtractor()
        self.weights = DEFAULT_WEIGHTS | (weights or {})
        if any(value < 0 for value in self.weights.values()) or not any(self.weights.values()):
            raise ValueError("weights must be non-negative and contain at least one positive value")

    def match(self, cv_text: str, job_text: str) -> MatchResult:
        cv = self.extractor.extract(cv_text)
        job = self.extractor.extract(job_text)

        categories = [
            _set_category(
                "technical_skills",
                _canonical_set(cv, "technical_skills"),
                _canonical_set(job, "technical_skills"),
                self.weights["technical_skills"],
            ),
            _set_category(
                "tools",
                _canonical_set(cv, "tools"),
                _canonical_set(job, "tools"),
                self.weights["tools"],
            ),
            _set_category(
                "soft_skills",
                _canonical_set(cv, "soft_skills"),
                _canonical_set(job, "soft_skills"),
                self.weights["soft_skills"],
            ),
            _education_category(cv.education, job.education, self.weights["education"]),
            _experience_category(
                cv.experience_years, job.experience_years, self.weights["experience"]
            ),
            _label_category("seniority", cv.seniority, job.seniority, self.weights["seniority"]),
            _label_category(
                "work_arrangement",
                cv.work_arrangement,
                job.work_arrangement,
                self.weights["work_arrangement"],
            ),
        ]

        active_weight = sum(item.configured_weight for item in categories if item.applicable)
        if active_weight == 0:
            raise ValueError("No supported job requirements were detected in job_text")

        normalized: list[CategoryScore] = []
        for item in categories:
            effective = item.configured_weight / active_weight if item.applicable else 0.0
            values = asdict(item)
            values["effective_weight"] = round(effective, 4)
            normalized.append(CategoryScore(**values))

        overall = round(
            100 * sum((item.score or 0.0) * item.effective_weight for item in normalized),
            1,
        )
        matched = sorted({skill for item in normalized[:3] for skill in item.matched})
        missing = sorted({skill for item in normalized[:3] for skill in item.missing})
        priorities = self._learning_priorities(normalized)
        verdict = "strong_match" if overall >= 80 else "potential_match" if overall >= 60 else "skill_gap"
        return MatchResult(
            overall_score=overall,
            verdict=verdict,
            matched_skills=matched,
            missing_skills=missing,
            category_scores=normalized,
            learning_priorities=priorities,
            disclaimer=(
                "Baseline berbasis taxonomy; gunakan sebagai decision support, bukan keputusan "
                "rekrutmen otomatis. Skor hanya mencakup persyaratan yang berhasil diekstrak."
            ),
        )

    @staticmethod
    def _learning_priorities(categories: list[CategoryScore]) -> list[LearningPriority]:
        priorities: list[LearningPriority] = []
        priority_order = {"technical_skills": "high", "tools": "high", "soft_skills": "medium"}
        for category in categories[:3]:
            for skill in category.missing:
                priorities.append(
                    LearningPriority(
                        skill=skill,
                        category=category.category,
                        priority=priority_order[category.category],
                        reason=f"Disebut pada lowongan tetapi belum terdeteksi di CV ({category.category}).",
                    )
                )
        return priorities
