# SkillPulse AI Portfolio Report Notes

## Audience and decision

The report is designed for hiring managers, technical reviewers, and product stakeholders
deciding whether SkillPulse AI demonstrates a credible end-to-end portfolio project and
which evidence must still be completed before a public release claim.

## Metric definitions

- **Source rows:** cleaned job postings in the pinned Kaggle v1 snapshot.
- **Primary reviewed:** job descriptions in the AI-assisted, project-owner-reviewed
  extraction development set.
- **Spearman:** global rank correlation against 50 synthetic scenario-oracle relevance
  targets; not a human relevance score.
- **MAE:** mean absolute difference between matcher score and the scenario-oracle target
  mapped to 0-100.
- **Verdict accuracy:** agreement between matcher verdict bucket and scenario-oracle bucket.
- **Explanation completeness:** share of responses containing the required explainability
  fields.
- **Latency:** local evaluation runtime per pair from the same challenger comparison run.

## Chart map

| Chart | Question | Comparison | Encoding | Why this visual |
|---|---|---|---|---|
| Model quality comparison | Did the semantic hybrid improve unit-scale quality metrics? | Exact taxonomy vs semantic hybrid across Spearman, verdict accuracy, and explanation completeness | Grouped vertical bars; metric on x, value on y, model by color | Three comparable 0-1 measures make differences and ties visible without mixing incompatible units |
| Local latency comparison | What latency trade-off did the semantic hybrid introduce? | p50 and p95 milliseconds for both models | Grouped vertical bars; percentile on x, milliseconds on y, model by color | Same-unit comparison makes the runtime cost immediately visible |

The quality-gate section uses a table because exact current/minimum counts, status text,
and limitations are audit values. A zero-progress chart would add decoration without
insight.

## Visual QA intent

Both charts use a hard two-root palette because model identity is a meaningful second
dimension. Bars use a zero baseline. Each chart is preceded by a narrative paragraph that
states the denominator and interpretation. Exact values remain available through tooltips
and the adjacent comparison table.
