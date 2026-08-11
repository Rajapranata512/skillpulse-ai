# SkillPulse AI System Model Card

**Version:** 0.1.0  
**Last verified:** 10 August 2026  
**Status:** local portfolio candidate; human validation gates remain open

## Summary

SkillPulse AI is a bilingual Indonesian-English job-intelligence system. It extracts
explicit requirements from CV and job-description text, then produces an explainable
CV-to-job match with matched evidence, missing requirements, component scores, and
learning priorities.

The public demo uses two deterministic production candidates:

- taxonomy/rule extraction `taxonomy-rules-0.2.0`;
- exact-taxonomy matching `exact-taxonomy-0.1.0`.

A multilingual sentence-transformer hybrid exists only as an experimental challenger.
It was not promoted because it did not improve the current synthetic diagnostic and was
substantially slower.

## Intended use

- Help job seekers inspect requirements that are explicit in a job description.
- Explain which supported skills or tools are present or missing from supplied CV text.
- Demonstrate reproducible NLP, evaluation, API, UI, and ML-governance engineering.
- Support analyst review and career exploration, not make hiring decisions.

## Out-of-scope use

- Automatic applicant ranking, rejection, or employment decisions.
- Inferring skills, experience, education, seniority, or work arrangement that are not
  explicitly stated.
- Scoring protected personal attributes or using them as proxies.
- Claiming Indonesia-wide or global labour-market trends from one 30-day dataset.
- Production salary prediction. Only 77 of 555 source rows disclose salary.
- Treating the current matching relevance results as human validation.

## Components and versions

| Component | Version | Role | Release status |
|---|---|---|---|
| Bilingual taxonomy | `0.2.0` | Canonical skills, tools, aliases, and labels | Active baseline |
| Extraction engine | `taxonomy-rules-0.2.0` | Deterministic explicit-entity extraction | Active baseline |
| Exact matcher | `exact-taxonomy-0.1.0` | Explainable requirement coverage and gaps | Active baseline |
| Semantic challenger | `paraphrase-multilingual-MiniLM-L12-v2`, weight 0.20 | Experimental semantic similarity | Not promoted |
| API contract | `1.0.0` | Strict request/response boundary | Frozen local contract |

## Data

The source snapshot contains 555 Indonesian Data & Analytics vacancies from Kaggle
version 1, covering JobStreet Indonesia postings from 25 August to 24 September 2025.
The declared license is CC BY 4.0. The local raw file is pinned by byte size and SHA-256,
but is excluded from Git because descriptions originate from third-party postings.

The primary extraction set contains 100 project-owner-reviewed documents. These labels
were AI-assisted and used during development, so they are development evidence rather
than an independent generalization estimate. The matching diagnostic contains 50
synthetic, public-safe CV-job pairs across 10 job groups. Their relevance targets are
scenario-oracle pseudo-labels, not independent human judgments.

## Evaluation results

### Extraction development baseline

| Field | Metric | Result |
|---|---:|---:|
| Technical skills | F1 | 1.0000 |
| Tools | F1 | 1.0000 |
| Soft skills | F1 | 0.9969 |
| Education | F1 | 1.0000 |
| Experience | Exact match | 1.0000 |
| Seniority | Exact match | 0.9900 |
| Work arrangement | Exact match | 1.0000 |

Denominator: 100 AI-assisted, project-owner-reviewed job descriptions. These values must
always be published with the development-set caveat. Independent field-level agreement
is still 0/100 because a different human has not completed the blind batch.

### Matching diagnostic

| Model | Spearman | MAE (0-100) | Verdict accuracy | Explanation completeness | p50 latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| Exact-taxonomy baseline | 0.9345 | 8.29 | 0.8000 | 1.0000 | 5.995 ms | 9.361 ms |
| Semantic hybrid | 0.9320 | 9.92 | 0.8000 | 1.0000 | 83.287 ms | 203.096 ms |

Denominator: the same 50 synthetic scenario-oracle pairs. The semantic hybrid changed
Spearman by -0.0025 and increased MAE by 1.63 points. The exact matcher therefore remains
the incumbent. Neither result satisfies the human relevance gate.

## Quality-gate status

- **ML-QG-1:** conditional pass on 100 reviewed development documents; caveat required.
- **ML-QG-2:** open, 0/100 independent blind second annotations.
- **ML-QG-3:** open, 0/50 independent human relevance judgments.
- **Salary data gate:** blocked, 77/555 disclosed salary rows versus a 300-row minimum.
- **Visual release QA:** functional/widget automation plus CI Chromium responsive, loading, validation,
  extraction, and API-offline checks passed; Firefox and Playwright WebKit keyboard-match smokes and
  three reviewed static screenshots passed. Human screen-reader/real-device review and narration remain open.

## Explainability

Every match response exposes the overall score, verdict, weights, category-level scores,
matched and missing evidence, and prioritized learning gaps. Weights are re-normalized
over requirements detected in the job description so an absent requirement category does
not silently penalize a candidate.

## Privacy, fairness, and safety

- API v1 is stateless and does not persist request text.
- The UI accepts pasted text only; file upload is disabled.
- Inputs are capped at 50,000 characters and unknown contract fields are rejected.
- Container access logging is disabled, and raw CSV/XLSX/report/notebook files are
  excluded from its build context.
- Protected attributes are not inputs to the score.
- Results include decision-support disclaimers and must remain reviewable by a human.

Deterministic rules improve auditability but do not eliminate bias. Taxonomy coverage,
wording style, language variety, and unequal access to credential terminology can affect
what is detected. Before any real hiring use, evaluate performance across consented and
appropriately governed language and user segments.

## Known limitations

- Taxonomy-supported explicit mentions are stronger than paraphrases outside the taxonomy.
- The source is one Indonesian role family and one 30-day window.
- Primary extraction evaluation is not an untouched holdout.
- No independent inter-annotator agreement is available.
- Matching relevance has synthetic pseudo-labels only.
- The semantic model may require a first-run model download and is not part of the default
  API/UI runtime.
- No public load/security test, screen-reader audit, real Safari/device check, or human usability study has been completed.

## Reproducibility and evidence

- Data provenance: `data/provenance/sources.yaml` and `reports/data_card.md`
- Extraction: `reports/extraction_gold_eval.json` and
  `reports/extraction_gold_validation.md`
- Matching: `reports/matching_relevance_ai_baseline.json` and
  `reports/matching_semantic_challenger.json`
- Runtime: `reports/api_container_smoke.json` and `reports/ui_smoke.json`
- Contract: `docs/api_contract_v1.json`
- Local demo: `docs/demo_checklist.md` and `scripts/run_demo.ps1`

Run `ruff check src tests` and `pytest -q` before publishing any new metric. Re-run only
the dependent evaluations when taxonomy, labels, matcher behavior, or source identity
changes.

## Release criteria

The system may be shown as a transparent local portfolio demo now, provided the caveats
above remain visible. It must not be presented as independently validated or production
ready until blind annotation, human relevance, human accessibility/usability, narrated media, public
deployment, and monitoring gates are completed.
