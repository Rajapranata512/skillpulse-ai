# ML quality-gate remediation

**Verified:** 2026-08-10  
**Scope:** ML-QG-2 annotation reliability and ML-QG-3 matching relevance  
**Decision:** continue engineering under explicit non-human-evidence labels; do not claim either gate passed.

## Why remediation is necessary

The project owner requested the maximum safe automatic path. Automation cannot create an
independent second human annotator or an independent human relevance judgment. Filling those
fields with project code or an AI would invalidate the stated quality gates. The project
therefore keeps the original human-review files untouched and produces separate challenger
artifacts with explicit provenance.

## ML-QG-2 — annotation reliability

- Primary set: 100 AI-assisted, project-owner-confirmed rows; suitable as development evidence
  with the existing validation caveat.
- Independent blind set: still 0/100 human-reviewed; ML-QG-2 remains open.
- External workbook remediation: 100 source texts restored, all fingerprints aligned, labels
  normalized to taxonomy v0.2, and output validation passed.
- The remediated workbook is `ai_reviewed`, not human gold. Its AI-versus-primary metrics are
  descriptive error-analysis evidence only. It is not Cohen's Kappa between two humans.
- Unsupported workbook labels were logged rather than silently added to the taxonomy. The
  largest technical/tool drops should inform later human taxonomy review.

**Closure trigger:** a different human independently reviews the 100 blind rows, followed by
field-level agreement and adjudication for every field below 0.75.

## ML-QG-3 — matching relevance

- Human relevance file: remains 0/50; its label columns are unchanged.
- Separate synthetic-oracle labels cover all 50 public-safe pairs and all five designed
  scenarios. They support deterministic regression and architecture comparison only.
- Exact-taxonomy baseline on synthetic labels: Spearman 0.9345, MAE 8.29/100, verdict accuracy
  0.80, and explanation completeness 1.00.
- Multilingual MiniLM hybrid at 20% semantic weight: Spearman 0.9320, MAE 9.92/100, verdict
  accuracy 0.80, explanation completeness 1.00, and p50 latency about 83 ms.
- The challenger was not promoted because it slightly reduced rank agreement, increased error,
  and materially increased latency on this diagnostic set. No weight tuning was performed on
  the pseudo-label benchmark.

**Closure trigger:** freeze 50 independent human scores/rationales, rerun both models without
tuning on the evaluation set, then require Spearman at least 0.60 and a measurable user-relevant
gain before replacing the baseline.

## Engineering continuation allowed

The remediation permits domain-contract and product-service engineering to continue so the
portfolio is not idle. Public documentation must continue to say:

- ML-QG-2 and ML-QG-3 are not met;
- AI/synthetic metrics are development diagnostics, not independent validation;
- the system is decision support and must not automatically rank or reject candidates.

Portfolio-ready release remains blocked until the human gates are completed or the public scope
is explicitly reduced to an engineering prototype with no independent-performance claim.
