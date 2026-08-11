# SkillPulse AI — From Job-Description Research to an Explainable Product

## Outcome

SkillPulse AI turns Indonesian-English CV and job-description text into structured job
requirements, an explainable match score, missing-skill evidence, and learning priorities.
The repository now demonstrates an end-to-end local product: reproducible data provenance,
annotation governance, evaluated NLP baselines, a strict API contract, a non-root container,
a Streamlit UI, automated tests, and honest release gates.

It is a working portfolio project, not yet an independently validated production service.
That distinction is intentional and visible throughout the product.

## The problem

Job seekers often see a long list of requirements but cannot answer three practical
questions:

1. Which skills and tools are explicitly required?
2. Which requirements are already evidenced in their CV, and which are missing?
3. What should they learn first?

Keyword-only tools can hide how a score was produced. Salary estimates and market-trend
claims can also look authoritative even when the source is sparse or covers only a short
period. SkillPulse was designed around evidence before complexity: each result must be
traceable, and unsupported features remain blocked.

## Why this project

The work extends prior Computer Science and Statistics research on job-description text
mining and salary determinants into a coherent product. Instead of discarding the research
notebook or wrapping it directly in a UI, the project preserves it as history and creates
separate production-style data, domain, evaluation, API, and presentation layers.

## Data foundation

The current source is Kaggle version 1 of *Indonesian Data & Analytics Jobs in Jobstreet*:
555 postings from 25 August to 24 September 2025 with a declared CC BY 4.0 license. A fresh
download matched the local raw file byte-for-byte and by SHA-256.

This supports a bounded Indonesian data-and-analytics snapshot. It does not support a
whole-market or global comparison. Raw descriptions are excluded from Git; reproducibility
uses attribution, a pinned source version, an acquisition script, and a hash check.

Only 77/555 rows disclose salary, so salary modelling remains blocked rather than producing
a fragile portfolio metric.

## Baseline-first NLP

A bilingual taxonomy normalizes explicit Indonesian-English mentions of technical skills,
tools, soft skills, education, experience, seniority, and work arrangement. The extraction
engine uses deterministic contextual rules so a reviewer can trace why an entity was
returned.

The primary 100-document evaluation produced:

| Field | Result |
|---|---:|
| Technical skills F1 | 1.0000 |
| Tools F1 | 1.0000 |
| Soft skills F1 | 0.9969 |
| Education F1 | 1.0000 |
| Experience exact match | 1.0000 |
| Seniority exact match | 0.9900 |
| Work arrangement exact match | 1.0000 |

These are strong development metrics, but the labels were AI-assisted and
project-owner-reviewed. They are not an untouched holdout. A blind 100-row batch exists
for a different human, and independent agreement remains 0/100 until that work is actually
completed.

## Explainable matching

The matcher scores only requirement categories detected in the job description. It
re-normalizes component weights over those categories and returns:

- matched and missing evidence;
- category-level scores and weights;
- an overall score and verdict;
- prioritized learning gaps;
- model/taxonomy versions and a decision-support disclaimer.

This makes the score inspectable and prevents an unstated category from silently reducing
the result.

## A model that was not promoted

A 20% hybrid using `paraphrase-multilingual-MiniLM-L12-v2` was compared with the exact
matcher on the same 50 synthetic scenario-oracle pairs.

| Model | Spearman | MAE (0-100) | p50 | p95 |
|---|---:|---:|---:|---:|
| Exact taxonomy | 0.9345 | 8.29 | 5.995 ms | 9.361 ms |
| Semantic hybrid | 0.9320 | 9.92 | 83.287 ms | 203.096 ms |

The hybrid slightly reduced rank agreement, increased error, and added substantial local
latency. It was therefore not promoted. This is the most important modelling decision in
the project: adding a transformer is not treated as progress unless it produces better
evidence on a frozen evaluation contract.

The 50 relevance targets are synthetic diagnostics, not human judgments. Human relevance
remains 0/50, so neither score is presented as real-user validation.

## Product architecture

The application separates responsibilities:

```text
pinned source -> data/provenance -> bilingual taxonomy -> extraction -> matching
                                                            ^             ^
user text -> Streamlit UI -> FastAPI v1 -> strict domain contract ----------+

evaluation reports -> model card / case study / release decisions
```

FastAPI exposes four endpoints and returns contract/model/taxonomy versions. The UI calls
that API instead of importing model logic. The API container runs as a non-root user,
disables access logs, and excludes raw data, annotation files, notebooks, and reports from
the build context.

## Product proof

| Area | Evidence |
|---|---|
| Reproducibility | Pinned dataset identity, deterministic pipeline, CI commands |
| NLP | Bilingual taxonomy, explicit extraction, gold-development report |
| Statistics | Precision/recall/F1, exact match, Cohen's Kappa workflow, rank correlation, MAE, latency |
| ML engineering | Frozen contracts, incumbent/challenger comparison, optional semantic dependency |
| API | Strict FastAPI v1 schemas and four documented endpoints |
| Deployment | Healthy non-root local Docker smoke |
| Product/UI | API-backed Streamlit journey, Chromium responsive QA, reviewed static media, and launcher |
| Governance | No CV persistence, protected attributes excluded, open human/data gates |

Latest engineering verification: Ruff passed and 102 tests passed. API container and
Streamlit health checks passed locally; widget-state tests plus CI Chromium cover empty,
match, validation-error, and mobile extraction states without horizontal overflow.

## What did not work

- Treating an AI-authored workbook as a second human annotation would have invalidated the
  independence claim. It was repaired into a separate AI challenger instead.
- The semantic hybrid did not improve the frozen synthetic diagnostic and was not shipped.
- Local headless browser tooling produced crash pages; CI-hosted Playwright Chromium later produced reviewed media.
- The shared portable-report renderer still reports horizontal overflow at desktop width,
  even after a targeted table-width correction. The canonical JSON is retained, but no
  unverified HTML report is published.

Recording these failures makes the portfolio more credible: each one produced a bounded
decision instead of a hidden exception or inflated claim.

## Privacy and responsible use

SkillPulse is decision support, not an automated hiring authority. It does not persist raw
CV text, does not accept file uploads in UI v1, and does not score protected attributes.
Inputs are capped at 50,000 characters. A public deployment would still require TLS, rate
limits, abuse controls, accessibility checks, monitoring, and a verified retention policy.

## Current limitations

- One data source, one job family, one 30-day window.
- Primary extraction results are development-set evidence.
- No independent annotation agreement yet.
- No independent human matching relevance yet.
- No public deployment, load test, independent usability study, accessibility audit, or cross-browser QA.
- No market-trend or salary feature supported by current evidence.

## Next evidence milestones

1. Complete keyboard/accessibility and cross-browser review, then record a public-safe narrated walkthrough.
2. Have a different human complete the 100-row blind annotation and publish agreement.
3. Freeze 50 independent human relevance judgments and rerun both matchers without tuning
   on the evaluation set.
4. Document hosting, monitoring, privacy, and rollback decisions before public deployment.

## Review the project

- Start the demo: `powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -Install`
- Follow the walkthrough: `docs/demo_checklist.md`
- Inspect the architecture: `docs/architecture.md`
- Inspect model claims: `docs/model_card.md`
- Inspect the release evidence: `reports/portfolio_release_metrics.json`
