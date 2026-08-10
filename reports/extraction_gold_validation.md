# Extraction Gold Evaluation Validation

## Overall Assessment: Share with caveats

The 100-document human-confirmed extraction baseline satisfies the numerical requirements
of ML-QG-1, but it is not an independent estimate of generalization. The primary gold set
was AI-assisted: the first 30 documents informed rule development, and the remaining 70
were pre-labelled by the same extractor before the project owner reviewed and approved
them. These metrics are suitable as a transparent portfolio baseline, not as a production
performance claim.

## Question and Evidence Scope

- Question: does extractor v0.2 meet the portfolio baseline on the frozen, human-confirmed
  100-document sample?
- Source: Kaggle dataset version 1, 555 Indonesian data/analytics vacancies from a single
  JobStreet snapshot covering 25 August–24 September 2025.
- Evaluation grain: one complete job-description text per row.
- Canonical artifact: `reports/extraction_gold_eval.json`.
- Validation date: 2026-08-10 (Asia/Jakarta project context).

## Methodology Review

The evaluator includes only rows with `review_status=reviewed`. Set-valued fields report
micro precision, recall, F1, document exact match, and TP/FP/FN. Experience, seniority, and
work arrangement report exact match. The denominator is 100 unique reviewed source rows;
all have annotator IDs, non-empty notes, and corresponding audit records.

ML-QG-1 requires at least 100 human-reviewed documents, technical/tool F1 and recall of at
least 0.80, and per-category metrics. Those mechanical requirements are met. The evidence
does not establish performance on unseen job families, sources, countries, or time periods.

## Issues Found

1. **High — evaluation dependence.** The same rule extractor produced the 70 pre-labels
   that were approved, and the first 30 rows guided tuning. Near-perfect results may reflect
   confirmation/selection effects and development-set reuse. Impact: do not describe the
   metrics as independent test performance.
2. **Medium — limited population.** The 100 rows come from one Indonesian portal, one role
   family, and a 30-day snapshot. Impact: no Indonesia-wide, global, or temporal claim.
3. **Blocker for ML-QG-2 — no independent second labels yet.** A blind 100-row batch is
   ready, but agreement cannot be claimed until a different human completes it.

## Calculation Spot-Checks

- Population: verified — 100 rows, 100 unique `source_row` values, 100 `reviewed`.
- Workflow completeness: verified — 100 rows with notes; 30 attributed to
  `project_owner_v1`, 70 to `project_owner_v2`; 100 unique audit rows.
- Technical skills: 120 labels across 53 documents; precision/recall/F1 1.0000.
- Tools: 94 labels across 47 documents; precision/recall/F1 1.0000.
- Soft skills: 162 labels across 75 documents; precision 0.9939, recall 1.0000,
  F1 0.9969, document exact match 0.9900.
- Education: 86 labels across 70 documents; precision/recall/F1 1.0000.
- Experience exact match: 1.0000; seniority: 0.9900; work arrangement: 1.0000.
- ML-QG-1 threshold check: pass as a human-confirmed development baseline.

## Visualization Review

Not applicable. The canonical artifact is a structured JSON metric report without charts.

## Suggested Improvements

1. Complete the blind second-annotator batch and publish field-level Cohen's Kappa plus
   adjudication notes.
2. Freeze extractor v0.2 until the blind annotations are complete.
3. Build a genuinely unseen holdout from another permitted source/time window before any
   broader generalization claim.

## Required Caveats for Stakeholders

- These are AI-assisted, human-confirmed development metrics, not independent holdout
  performance.
- The dataset is limited to Indonesian data/analytics vacancies in one 30-day snapshot.
- SkillPulse is decision support and must not be used for automated hiring or rejection.
