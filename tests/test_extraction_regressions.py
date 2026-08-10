import pytest

from skillpulse.extraction import EntityExtractor


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "System Analyst Intern. Alumnus, max. 1 year after graduation. Get a min. 3-month internship experience.",
            None,
        ),
        (
            "Our financial institution has a history spanning over 200 years and today serves clients globally.",
            None,
        ),
        (
            "The company launched 2.5 years ago. Requirements: 2+ years of data analytics experience.",
            2.0,
        ),
    ],
)
def test_experience_ignores_non_candidate_durations(text: str, expected: float | None) -> None:
    assert EntityExtractor().extract(text).experience_years == expected


def test_experience_supports_indonesian_year_abbreviation() -> None:
    text = "Memiliki pengalaman sebagai Data Analyst Manager minimal 3 th."

    assert EntityExtractor().extract(text).experience_years == 3.0


def test_seniority_prefers_target_role_over_other_people() -> None:
    text = "Junior Financial Modeling Analyst. Work closely with senior consultants."

    assert EntityExtractor().extract(text).seniority == "entry"


def test_seniority_is_not_inferred_from_experience_years() -> None:
    text = "Data Analyst. Minimum 5 years of relevant experience."

    assert EntityExtractor().extract(text).seniority == "unknown"


def test_supervisor_title_maps_to_senior() -> None:
    text = "System Analyst Supervisor di Jakarta. Pengalaman 3 tahun."

    assert EntityExtractor().extract(text).seniority == "senior"
