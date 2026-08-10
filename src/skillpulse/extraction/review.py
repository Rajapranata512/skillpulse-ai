"""Read-only HTML review packs for human annotation verification."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from .engine import EntityExtractor, ExtractionResult

REVIEW_STATUSES = {"needs_review", "ai_reviewed", "reviewed"}
FIELD_SPECS = (
    ("Technical skills", "gold_technical_skills", "technical_skills"),
    ("Tools", "gold_tools", "tools"),
    ("Soft skills", "gold_soft_skills", "soft_skills"),
    ("Education", "gold_education", "education"),
    ("Experience years", "gold_experience_years", "experience_years"),
    ("Seniority", "gold_seniority", "seniority"),
    ("Work arrangement", "gold_work_arrangement", "work_arrangement"),
)


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _prediction(result: ExtractionResult, field: str) -> str:
    value = getattr(result, field)
    if field in {"technical_skills", "tools", "soft_skills"}:
        return "|".join(item.canonical for item in value)
    if field == "education":
        return "|".join(value)
    if field == "experience_years":
        return "" if value is None else f"{value:g}"
    return str(value)


def _normalized(value: str, field: str) -> object:
    if field in {"technical_skills", "tools", "soft_skills", "education"}:
        return tuple(sorted(part.strip().casefold() for part in value.split("|") if part.strip()))
    if field == "experience_years":
        try:
            return None if not value else float(value)
        except ValueError:
            return value.casefold()
    return value.casefold()


def _display(value: str) -> str:
    return escape(value) if value else '<span class="empty">empty</span>'


def build_annotation_review_pack(
    frame: pd.DataFrame,
    extractor: EntityExtractor | None = None,
    status: str = "ai_reviewed",
) -> str:
    """Return a self-contained, read-only HTML verification pack."""
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Unsupported review status: {status}")
    required = {"source_row", "text", "review_status", "annotator", "notes"} | {
        column for _, column, _ in FIELD_SPECS
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Missing annotation columns: {', '.join(missing)}")

    selected = frame[frame["review_status"].fillna("").str.strip().eq(status)]
    engine = extractor or EntityExtractor()
    cards: list[str] = []
    disagreement_fields = 0
    documents_with_disagreement = 0

    for _, row in selected.iterrows():
        result = engine.extract(str(row["text"]))
        comparisons: list[str] = []
        row_has_disagreement = False
        for label, gold_column, result_field in FIELD_SPECS:
            current = _clean(row[gold_column])
            predicted = _prediction(result, result_field)
            agrees = _normalized(current, result_field) == _normalized(predicted, result_field)
            if not agrees:
                disagreement_fields += 1
                row_has_disagreement = True
            badge = '<span class="ok">AGREE</span>' if agrees else '<span class="review">REVIEW</span>'
            comparisons.append(
                "<tr>"
                f"<th>{escape(label)}</th>"
                f"<td>{_display(current)}</td>"
                f"<td>{_display(predicted)}</td>"
                f"<td>{badge}</td>"
                "</tr>"
            )
        documents_with_disagreement += int(row_has_disagreement)
        cards.append(
            '<article class="card">'
            f'<h2>Source row {escape(_clean(row["source_row"]))}</h2>'
            '<div class="meta">'
            f'Status: <code>{escape(status)}</code> · '
            f'Annotator: <code>{escape(_clean(row["annotator"]) or "unassigned")}</code>'
            "</div>"
            f'<pre class="text">{escape(str(row["text"]))}</pre>'
            "<table><thead><tr><th>Field</th><th>Current annotation</th>"
            "<th>Extractor prediction</th><th>Check</th></tr></thead>"
            f'<tbody>{"".join(comparisons)}</tbody></table>'
            f'<p class="notes"><strong>Notes:</strong> {_display(_clean(row["notes"]))}</p>'
            "</article>"
        )

    summary = (
        f"{len(selected)} documents · {documents_with_disagreement} documents with disagreements · "
        f"{disagreement_fields} fields to inspect"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SkillPulse annotation review pack</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0; background: #f4f7fb; color: #172033; }}
    main {{ max-width: 1120px; margin: auto; padding: 32px 20px 64px; }}
    header, .card {{ background: white; border: 1px solid #dce4ef; border-radius: 14px; padding: 22px; }}
    header {{ position: sticky; top: 8px; z-index: 1; box-shadow: 0 8px 24px #17203312; }}
    .card {{ margin-top: 20px; }}
    h1, h2 {{ margin: 0 0 10px; }} .meta, .notes {{ color: #526079; }}
    .warning {{ border-left: 4px solid #d97706; padding-left: 12px; }}
    .text {{ white-space: pre-wrap; max-height: 320px; overflow: auto; background: #f8fafc; padding: 14px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border-bottom: 1px solid #e5eaf1; padding: 9px; text-align: left; vertical-align: top; }}
    .ok {{ color: #067647; font-weight: 700; }} .review {{ color: #b42318; font-weight: 700; }}
    .empty {{ color: #7c879d; font-style: italic; }} code {{ overflow-wrap: anywhere; }}
  </style>
</head>
<body><main>
  <header>
    <h1>SkillPulse annotation review pack</h1>
    <p><strong>{escape(summary)}</strong></p>
    <p class="warning">Read-only decision aid. Compare every field with the source text. Edit the CSV directly and
    change <code>review_status</code> to <code>reviewed</code> only after human verification; extractor agreement is
    not proof of correctness.</p>
  </header>
  {''.join(cards) if cards else '<p class="card">No rows match this review status.</p>'}
</main></body>
</html>
"""


def write_annotation_review_pack(
    frame: pd.DataFrame,
    output: Path,
    extractor: EntityExtractor | None = None,
    status: str = "ai_reviewed",
) -> int:
    """Write a review pack and return the number of included documents."""
    html = build_annotation_review_pack(frame, extractor, status)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return int(frame["review_status"].fillna("").str.strip().eq(status).sum())
