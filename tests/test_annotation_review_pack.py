import pandas as pd
import pytest

from skillpulse.extraction.review import build_annotation_review_pack


def _row(status: str = "ai_reviewed") -> dict[str, str]:
    return {
        "source_row": "7",
        "text": "Python & SQL, 2 years experience, bachelor degree, communication.",
        "gold_technical_skills": "Python|SQL",
        "gold_tools": "",
        "gold_soft_skills": "Communication",
        "gold_education": "Bachelor",
        "gold_experience_years": "2.0",
        "gold_seniority": "unknown",
        "gold_work_arrangement": "unknown",
        "review_status": status,
        "annotator": "ai<label>",
        "notes": "Check <source> carefully.",
    }


def test_review_pack_is_read_only_filtered_and_html_escaped() -> None:
    html = build_annotation_review_pack(pd.DataFrame([_row(), _row("needs_review")]))

    assert "1 documents · 0 documents with disagreements" in html
    assert "Source row 7" in html
    assert "ai&lt;label&gt;" in html
    assert "Check &lt;source&gt; carefully." in html
    assert "extractor agreement is\n    not proof of correctness" in html


def test_review_pack_highlights_disagreement() -> None:
    row = _row()
    row["gold_technical_skills"] = "Python"

    html = build_annotation_review_pack(pd.DataFrame([row]))

    assert "1 documents with disagreements · 1 fields to inspect" in html
    assert '<span class="review">REVIEW</span>' in html


def test_review_pack_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="Unsupported review status"):
        build_annotation_review_pack(pd.DataFrame([_row()]), status="invalid")
