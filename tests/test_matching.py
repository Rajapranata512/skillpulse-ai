import pytest

from skillpulse.matching import CVJobMatcher


def test_match_reports_score_overlap_and_skill_gap() -> None:
    cv = (
        "Data analyst with 3 years experience using Python, SQL, Excel and Tableau. "
        "Bachelor degree, strong communication, open to hybrid work."
    )
    job = (
        "Mid-level analyst with 2 years experience. Requires Python, SQL, statistics, "
        "Power BI, Tableau, communication, bachelor degree, and hybrid work."
    )

    result = CVJobMatcher().match(cv, job)

    assert 0 < result.overall_score < 100
    assert {"Python", "SQL", "Tableau", "Communication"} <= set(result.matched_skills)
    assert set(result.missing_skills) == {"Power BI", "Statistics"}
    assert {item.skill for item in result.learning_priorities} == {"Power BI", "Statistics"}


def test_score_weights_are_normalized_over_detected_requirements() -> None:
    result = CVJobMatcher().match("Python developer", "Python and SQL required")
    applicable = [item for item in result.category_scores if item.applicable]

    assert sum(item.effective_weight for item in applicable) == pytest.approx(1.0)
    assert result.overall_score == 50.0


def test_experience_receives_partial_credit() -> None:
    result = CVJobMatcher().match(
        "Data analyst with 2 years experience and Python.",
        "Data analyst with 4 years experience and Python.",
    )
    experience = next(item for item in result.category_scores if item.category == "experience")

    assert experience.score == 0.5
    assert experience.candidate_value == 2.0
    assert experience.job_requirement == 4.0


def test_job_without_supported_requirements_is_rejected() -> None:
    with pytest.raises(ValueError, match="No supported job requirements"):
        CVJobMatcher().match("Experienced candidate", "Join our fast-growing company")


def test_invalid_custom_weights_are_rejected() -> None:
    all_zero = {key: 0.0 for key in CVJobMatcher().weights}
    with pytest.raises(ValueError, match="weights"):
        CVJobMatcher(weights=all_zero)
