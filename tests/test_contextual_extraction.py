import pytest

from skillpulse.extraction import EntityExtractor


def _technical(text: str) -> set[str]:
    return {item.canonical for item in EntityExtractor().extract(text).technical_skills}


def _soft(text: str) -> set[str]:
    return {item.canonical for item in EntityExtractor().extract(text).soft_skills}


def test_java_geography_is_not_a_programming_skill() -> None:
    assert "Java" not in _technical("Willing to be placed across West Java, Indonesia.")
    assert "Java" not in _technical("Willing to work all around Java (Indonesia).")
    assert "Java" in _technical("Strong Java programming skills are required.")


def test_statistics_degree_context_is_not_a_technical_skill() -> None:
    assert "Statistics" not in _technical("Bachelor degree in Mathematics, Statistics, or Finance.")
    assert "Statistics" in _technical("Experience with statistical analysis and forecasting.")


def test_standalone_r_is_recognized_only_in_safe_skill_context() -> None:
    assert "R" in _technical("Experience with Python, R, or SQL is a plus.")
    assert "R" in _technical("Use Python and/or R programming languages.")
    assert "R" not in _technical("We are hiring a researcher for reporting.")


@pytest.mark.parametrize(
    "text",
    [
        "Menganalisis dan menginterpretasikan data dari berbagai sumber.",
        "Analyze rich user behavioral data to identify trends.",
        "Menguasai formula, pivot, dan analisa data.",
        "Monitor and analyze performance data every day.",
    ],
)
def test_observed_analysis_phrases_map_to_data_analysis(text: str) -> None:
    assert "Data Analysis" in _technical(text)


def test_visualization_and_plural_pipeline_patterns_are_supported() -> None:
    skills = _technical("Proven Data Analysis & Visualization and data pipelines experience.")

    assert {"Data Analysis", "Data Visualization", "ETL"} <= skills


def test_observed_soft_skill_phrases_are_normalized() -> None:
    text = (
        "Able to work independently and as part of a team, communicate insights, "
        "prepare presentations, remain detail oriented, analyze findings critically, "
        "and act as a problem solver."
    )

    assert {
        "Teamwork",
        "Communication",
        "Presentation",
        "Attention to Detail",
        "Critical Thinking",
        "Problem Solving",
    } <= _soft(text)


def test_leadership_audience_is_not_a_candidate_skill() -> None:
    skills = _soft("Present dashboards to Product and Leadership teams.")

    assert "Leadership" not in skills


def test_data_analysis_context_exclusions() -> None:
    assert "Data Analysis" not in _technical("Analyze business issues and data challenges.")
    assert "Data Analysis" not in _technical("Analyze and verify data reliability.")
    assert "Data Analysis" not in _technical("Ability to analyze financial statements and market data critically.")


def test_statistical_modeling_is_a_statistics_skill() -> None:
    assert "Statistics" in _technical("Experience with statistical modeling is a plus.")


def test_generic_collaboration_does_not_always_imply_teamwork() -> None:
    assert "Teamwork" not in _soft("Collaborate with stakeholders on the monthly report.")
    assert "Teamwork" in _soft("Able to work cross-functionally across regional teams.")


def test_present_findings_is_not_unconditionally_a_presentation_skill() -> None:
    assert "Presentation" not in _soft("Present findings to Product and Leadership teams.")


def test_observed_indonesian_detail_phrase_is_normalized() -> None:
    assert "Attention to Detail" in _soft(
        "Memiliki kemampuan analisa yang kuat, detail, terstruktur, dan cepat belajar."
    )

def test_detail_noun_is_not_attention_to_detail() -> None:
    assert "Attention to Detail" not in _soft(
        "Preparing the detail print out from SAP advance balance and petty cash."
    )


def test_explicit_collaboration_skills_are_normalized_as_teamwork() -> None:
    assert "Teamwork" in _soft("Candidates must bring stakeholder collaboration skills.")
