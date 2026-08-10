from pathlib import Path

import pandas as pd

from skillpulse.extraction import EntityExtractor
from skillpulse.extraction.cli import extract_csv, extract_text
from skillpulse.extraction.evaluation import evaluate_gold_annotations


def test_extracts_bilingual_entities_and_attributes() -> None:
    text = (
        "Dicari Junior Data Analyst, minimal 2 tahun pengalaman. "
        "Menguasai Python, SQL, PowerBI dan visualisasi data. "
        "Minimal S1, memiliki kemampuan komunikasi. Posisi hybrid."
    )
    result = EntityExtractor().extract(text)

    assert {item.canonical for item in result.technical_skills} == {
        "Python",
        "SQL",
        "Data Visualization",
    }
    assert {item.canonical for item in result.tools} == {"Power BI"}
    assert {item.canonical for item in result.soft_skills} == {"Communication"}
    assert result.experience_years == 2
    assert result.education == ["Bachelor"]
    assert result.seniority == "entry"
    assert result.work_arrangement == "hybrid"


def test_alias_boundaries_avoid_single_letter_false_positives() -> None:
    result = EntityExtractor().extract("We are hiring a researcher for reporting.")
    assert "R" not in {item.canonical for item in result.technical_skills}


def test_empty_text_is_rejected() -> None:
    try:
        EntityExtractor().extract("  ")
    except ValueError as error:
        assert "non-empty" in str(error)
    else:
        raise AssertionError("Empty text should be rejected")


def test_gold_evaluation_scores_reviewed_rows() -> None:
    annotations = pd.DataFrame(
        [
            {
                "text": "Need Python, SQL, Tableau. Minimal S1 and 2 years experience. Hybrid work.",
                "gold_technical_skills": "Python|SQL",
                "gold_tools": "Tableau",
                "gold_soft_skills": "",
                "gold_education": "Bachelor",
                "gold_experience_years": "2",
                "gold_seniority": "unknown",
                "gold_work_arrangement": "hybrid",
                "review_status": "reviewed",
            },
            {
                "text": "Fresh graduate welcome, strong communication and Excel required. Onsite role.",
                "gold_technical_skills": "",
                "gold_tools": "Excel",
                "gold_soft_skills": "Communication",
                "gold_education": "",
                "gold_experience_years": "0",
                "gold_seniority": "entry",
                "gold_work_arrangement": "onsite",
                "review_status": "reviewed",
            },
        ]
    )

    report = evaluate_gold_annotations(annotations, EntityExtractor())

    assert report["documents_reviewed"] == 2
    assert report["metrics"]["technical_skills"]["f1"] == 1.0
    assert report["metrics"]["tools"]["f1"] == 1.0
    assert report["metrics"]["soft_skills"]["f1"] == 1.0
    assert report["metrics"]["education"]["exact_match"] == 1.0
    assert report["metrics"]["experience_years"]["exact_match"] == 1.0
    assert report["metrics"]["work_arrangement"]["exact_match"] == 1.0


def test_extract_text_returns_serializable_payload() -> None:
    payload = extract_text("Python dan SQL untuk posisi remote.")

    assert payload["seniority"] == "unknown"
    assert payload["work_arrangement"] == "remote"
    assert payload["technical_skills"][0]["canonical"] == "Python"


def test_extract_csv_writes_enriched_file(tmp_path: Path) -> None:
    input_path = tmp_path / "jobs.csv"
    output_path = tmp_path / "jobs_with_extraction.csv"
    pd.DataFrame(
        [
            {"deskripsi_lengkap": "Need Python, SQL, Tableau. Hybrid role."},
            {"deskripsi_lengkap": "Communication and Excel for onsite analyst."},
        ]
    ).to_csv(input_path, index=False)

    extract_csv(input_path, output_path)
    enriched = pd.read_csv(output_path)

    assert list(enriched["extracted_tools"]) == ["Tableau", "Excel"]
    assert list(enriched["extracted_work_arrangement"]) == ["hybrid", "onsite"]
