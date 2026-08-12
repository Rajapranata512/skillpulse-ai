"""Explainable dictionary and pattern baseline for bilingual extraction."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class EntityMatch:
    canonical: str
    matched_text: str
    start: int
    end: int


@dataclass(frozen=True)
class ExtractionResult:
    technical_skills: list[EntityMatch]
    tools: list[EntityMatch]
    soft_skills: list[EntityMatch]
    education: list[str]
    experience_years: float | None
    seniority: str
    work_arrangement: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CONTEXTUAL_TECHNICAL_PATTERNS = {
    "Data Analysis": [
        r"\banaly[sz](?:e|es|ed|ing)\s+(?:[\w-]+\s+){0,3}?data\b",
        r"\bmenganalis(?:is|a)\s+(?:[\w-]+\s+){0,4}?data\b",
        r"\banalisa\s+data\b",
        r"\bmengevaluasi\s+data\b",
    ],
    "Data Visualization": [r"\bvisuali[sz]ation\b", r"\bvisualisasi\b"],
    "ETL": [r"\bdata\s+pipelines?\b"],
}

CONTEXTUAL_SOFT_PATTERNS = {
    "Attention to Detail": [r"\bdetail\s*,\s*terstruktur\b"],
}


def _clause_around(text: str, start: int, end: int) -> str:
    left = max(text.rfind(separator, 0, start) for separator in (".", "\n", ";"))
    right_positions = [position for separator in (".", "\n", ";") if (position := text.find(separator, end)) >= 0]
    right = min(right_positions, default=len(text))
    return text[left + 1 : right]


def _starts_with_term_after_whitespace(text: str, terms: tuple[str, ...]) -> bool:
    if not text or not text[0].isspace():
        return False
    normalized = text.lstrip().casefold()
    for term in terms:
        if not normalized.startswith(term):
            continue
        boundary = normalized[len(term) : len(term) + 1]
        if not boundary or (not boundary.isalnum() and boundary != "_"):
            return True
    return False


def _contextually_valid(text: str, candidate: EntityMatch) -> bool:
    clause = _clause_around(text, candidate.start, candidate.end)
    if candidate.canonical == "Java" and re.search(
        r"\b(?:west|east|central)\s+java\b|\b(?:around|across)\s+java\b|"
        r"\bjava\s*(?:\(\s*indonesia\s*\)|,\s*indonesia)",
        clause,
        re.IGNORECASE,
    ):
        return False
    if (
        candidate.canonical == "Statistics"
        and candidate.matched_text.casefold() in {"statistics", "statistik"}
        and re.search(
            r"\b(?:bachelor(?:['’]s)?(?:\s+degree)?|degree|s1|education|pendidikan|lulusan|major)\b"
            r"[^.\n;]{0,80}$",
            text[max(0, candidate.start - 100) : candidate.start],
            re.IGNORECASE,
        )
    ):
        return False
    if candidate.canonical == "Data Analysis" and _starts_with_term_after_whitespace(
        text[candidate.end : candidate.end + 30], ("challenges", "reliability")
    ):
        return False
    if candidate.canonical == "Leadership" and _starts_with_term_after_whitespace(
        text[candidate.end : candidate.end + 20], ("team", "teams")
    ):
        return False
    return True


def _contextual_technical_matches(text: str) -> list[EntityMatch]:
    matches: list[EntityMatch] = []
    for canonical, patterns in CONTEXTUAL_TECHNICAL_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(EntityMatch(canonical, match.group(), match.start(), match.end()))
    for match in re.finditer(r"(?<![\w])R(?![\w])", text):
        context = text[max(0, match.start() - 60) : min(len(text), match.end() + 60)]
        if re.search(
            r"\b(python|sql|programming|languages?|coding|one\s+of)\b",
            context,
            re.IGNORECASE,
        ):
            matches.append(EntityMatch("R", match.group(), match.start(), match.end()))
    return matches


def _contextual_soft_matches(text: str) -> list[EntityMatch]:
    matches: list[EntityMatch] = []
    for canonical, patterns in CONTEXTUAL_SOFT_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(EntityMatch(canonical, match.group(), match.start(), match.end()))
    return matches


def _load_entities(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("entities", [])


def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![\w]){escaped}(?![\w])", re.IGNORECASE)


class EntityExtractor:
    """Extract normalized entities while retaining explainable source spans."""

    def __init__(
        self,
        skills_path: Path = Path("configs/skill_taxonomy.yaml"),
        soft_skills_path: Path = Path("configs/soft_skills.yaml"),
    ) -> None:
        self.skills = _load_entities(skills_path)
        self.soft_skills = _load_entities(soft_skills_path)

    @staticmethod
    def _dictionary_matches(text: str, entities: list[dict[str, Any]]) -> list[EntityMatch]:
        candidates: list[EntityMatch] = []
        for entity in entities:
            for alias in sorted(entity["aliases"], key=len, reverse=True):
                for match in _alias_pattern(alias).finditer(text):
                    candidates.append(EntityMatch(entity["canonical"], match.group(), match.start(), match.end()))
        candidates.sort(key=lambda item: (item.start, -(item.end - item.start)))
        accepted: list[EntityMatch] = []
        seen: set[str] = set()
        for candidate in candidates:
            overlaps = any(candidate.start < item.end and candidate.end > item.start for item in accepted)
            if candidate.canonical not in seen and not overlaps and _contextually_valid(text, candidate):
                accepted.append(candidate)
                seen.add(candidate.canonical)
        return sorted(accepted, key=lambda item: item.start)

    @staticmethod
    def _experience(text: str) -> float | None:
        number = r"(?P<years>\d+(?:[.,]\d+)?)"
        range_suffix = r"(?:\s*(?:\+|(?:-|to|\u2013|\u2014)\s*\d+(?:[.,]\d+)?))?"
        unit = r"(?:years?|yrs?|tahun|th(?:n)?\.?)"
        patterns = [
            rf"(?:minimum|minimal|min\.?|at\s+least)\s*(?:of\s+)?"
            rf"{number}{range_suffix}\s*{unit}"
            rf"(?:\s+(?:of\s+)?(?:[\w/-]+\s+){{0,4}}?experience|\s+pengalaman)?",
            rf"{number}{range_suffix}\s*{unit}\s+(?:of\s+)?"
            rf"(?:[\w/-]+\s+){{0,4}}?experience",
            rf"(?:experience|pengalaman)[^.\n]{{0,100}}?"
            rf"(?:(?:minimum|minimal|min\.?|at\s+least)\s*(?:of\s+)?)?"
            rf"{number}{range_suffix}\s*{unit}",
            rf"(?:year\s+of\s+experience|pengalaman\s+kerja)\s*[:\r\n -]*"
            rf"{number}{range_suffix}(?:\s*{unit})?",
        ]
        candidates: list[tuple[int, float]] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                years = float(match.group("years").replace(",", "."))
                candidates.append((match.start(), years))
        if candidates:
            return min(candidates, key=lambda item: item[0])[1]
        if re.search(
            r"fresh\s*graduates?|freshgraduates?|lulusan\s*baru|no\s+experience",
            text,
            re.IGNORECASE,
        ):
            return 0.0
        return None

    @staticmethod
    def _seniority(text: str, years: float | None) -> str:
        del years  # Experience is scored separately and must not imply a job level.
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        title_context = first_line[:240]
        title_rules = [
            (
                "entry",
                r"\b(junior|jr\.?|entry[ -]level|fresh\s*graduate|"
                r"intern(?:ship)?|summer\s+analyst|trainee)\b",
            ),
            (
                "senior",
                r"\b(senior|sr\.?|lead|principal|manager|head|supervisor)\b",
            ),
            ("mid", r"\b(mid[ -]level|intermediate|associate)\b"),
        ]
        for label, pattern in title_rules:
            if re.search(pattern, title_context, re.IGNORECASE):
                return label

        explicit_rules = [
            (
                "entry",
                r"\b(fresh\s*graduates?|freshgraduates?|entry[ -]level)"
                r"(?:\s+(?:are\s+)?welcome)?\b",
            ),
            ("mid", r"\b(?:position|job|seniority)\s+level\s*:?\s*mid(?:dle)?\b"),
            ("senior", r"\b(?:position|job|seniority)\s+level\s*:?\s*senior\b"),
        ]
        for label, pattern in explicit_rules:
            if re.search(pattern, text, re.IGNORECASE):
                return label
        return "unknown"

    @staticmethod
    def _work_arrangement(text: str) -> str:
        rules = [
            ("hybrid", r"\b(hybrid|hibrida)\b"),
            ("remote", r"\b(remote|work from home|wfh|jarak jauh)\b"),
            ("onsite", r"\b(onsite|on-site|work from office|wfo|di kantor)\b"),
        ]
        return next((label for label, pattern in rules if re.search(pattern, text, re.IGNORECASE)), "unknown")

    @staticmethod
    def _education(text: str) -> list[str]:
        rules = {
            "High School": r"\b(sma|smk|high school)\b",
            "Diploma": r"\b(diploma|d3|d4)\b",
            "Bachelor": r"\b(s1|bachelor(?:'s)?|sarjana)\b",
            "Master": r"\b(s2|master(?:'s)?|magister)\b",
            "Doctorate": r"\b(s3|ph\.?d\.?|doctorate|doktor)\b",
        }
        return [label for label, pattern in rules.items() if re.search(pattern, text, re.IGNORECASE)]

    def extract(self, text: str) -> ExtractionResult:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        matches = self._dictionary_matches(text, self.skills)
        seen = {item.canonical for item in matches}
        for candidate in _contextual_technical_matches(text):
            overlaps = any(candidate.start < item.end and candidate.end > item.start for item in matches)
            if candidate.canonical not in seen and not overlaps and _contextually_valid(text, candidate):
                matches.append(candidate)
                seen.add(candidate.canonical)
        matches.sort(key=lambda item: item.start)
        soft_matches = self._dictionary_matches(text, self.soft_skills)
        seen_soft = {item.canonical for item in soft_matches}
        for candidate in _contextual_soft_matches(text):
            overlaps = any(candidate.start < item.end and candidate.end > item.start for item in soft_matches)
            if candidate.canonical not in seen_soft and not overlaps:
                soft_matches.append(candidate)
                seen_soft.add(candidate.canonical)
        soft_matches.sort(key=lambda item: item.start)
        types = {entity["canonical"]: entity["type"] for entity in self.skills}
        years = self._experience(text)
        return ExtractionResult(
            technical_skills=[m for m in matches if types[m.canonical] == "technical_skill"],
            tools=[m for m in matches if types[m.canonical] == "tool"],
            soft_skills=soft_matches,
            education=self._education(text),
            experience_years=years,
            seniority=self._seniority(text, years),
            work_arrangement=self._work_arrangement(text),
        )
