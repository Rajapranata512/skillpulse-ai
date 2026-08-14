# SkillPulse AI Architecture

**Architecture version:** 1.1
**Last verified:** 11 August 2026

## System view

```mermaid
flowchart LR
    S[Kaggle v1 source\n555 job postings] --> P[Reproducible data pipeline\nschema, cleaning, provenance]
    P --> T[Bilingual taxonomy v0.2]
    P --> A[Aggregate-only 30-day snapshot\n555 listings / 542 unique descriptions]
    T --> E[Rule extraction\ntaxonomy-rules-0.2.0]
    E --> M[Explainable matcher\nexact-taxonomy-0.1.0]
    E -. canonical requirement counts .-> A

    U[User-pasted CV and job text] --> API[FastAPI v1\nstrict stateless contract]
    API --> E
    API --> M
    API --> R[Versioned JSON response\nevidence, gaps, disclaimer]
    UI[Streamlit portfolio UI] --> API
    R --> UI
    A --> UI

    E -. aggregate evaluation .-> G[Gold and diagnostic reports]
    M -. synthetic evaluation .-> G
    G -. release evidence .-> D[Model card and portfolio report]

    H1[Blind second human\n0/100] -. human gate .-> G
    H2[Human relevance rater\n0/50] -. human gate .-> G
```

The runtime path is deliberately small: the UI calls a versioned API, the API converts
transport contracts to domain calls, and scoring logic remains inside extraction and
matching modules. Evaluation and documentation consume aggregate evidence rather than
becoming runtime dependencies.

## Component responsibilities

| Layer | Repository location | Responsibility |
|---|---|---|
| Data and provenance | `src/skillpulse/data/` | Validate source identity, normalize records, and emit quality evidence |
| Taxonomy | `configs/` | Store canonical bilingual labels and aliases once |
| Extraction | `src/skillpulse/extraction/` | Extract only explicit supported requirements and run annotation workflows |
| Matching | `src/skillpulse/matching/` | Score detected job requirements against CV evidence and explain gaps |
| Market snapshot | `src/skillpulse/market/`, `configs/market_snapshot.json` | Generate deterministic aggregate metrics and safe location/role slices from private cleaned rows |
| Domain contract | `src/skillpulse/domain/` | Enforce versioned strict request/response schemas and privacy metadata |
| API | `src/skillpulse/api/` | Expose health, model metadata, extraction, and matching endpoints |
| UI | `src/skillpulse/ui/` | Provide a public-safe bilingual demo without duplicating model logic |
| Evidence | `reports/` | Preserve aggregate evaluations, smoke tests, and release decisions |
| Release review | `src/skillpulse/release/` | Validate a private human accessibility/media record without creating reviewer judgments |

## Runtime contract

The API exposes four endpoints:

- `GET /health`
- `GET /v1/models`
- `POST /v1/extract`
- `POST /v1/match`

Contract version 1.0.0 rejects unknown fields, caps each text input at 50,000 characters,
and returns taxonomy/model versions with outputs. OpenAPI is available at `/docs` when the
service is running.

## Trust boundaries

```text
Browser session
  -> pasted text over localhost HTTP
  -> stateless FastAPI process
  -> in-memory extraction and matching
  -> structured response
  -> browser rendering
  -> optional redacted canonical-feedback JSON download
```

Raw CV/job text is not written by the application. The market tab loads only the committed
aggregate JSON; company names, job IDs, raw descriptions, and salary values never enter that
runtime path. The portfolio container excludes raw data, annotations, notebooks, reports, CSV,
and XLSX files from its build context. Access
logging is disabled by the packaged API command. Production deployment would still need
TLS, rate limiting, abuse controls, retention verification, and operational monitoring.

The extraction feedback path is browser-download-only and adds no API endpoint or database.
Its in-session context contains model/taxonomy versions and canonical labels only. Export is
disabled until explicit review confirmation and excludes source text, matched text, spans,
free-form notes, and identity.

## Evaluation boundaries

Three evidence classes must remain distinct:

1. **Human-confirmed development evidence:** 100 primary extraction annotations.
2. **AI/synthetic diagnostics:** external AI challenger and 50 scenario-oracle matching
   pairs; useful for regression, not human validation.
3. **Independent human evidence:** blind second annotation and relevance judgments; both
   are still pending and cannot be automated without invalidating their purpose.

The semantic challenger is isolated behind an optional dependency. Because it did not
improve the current diagnostic, the default API and UI keep the deterministic exact
matcher. A bounded single-window market snapshot is active, but salary prediction,
time-series change detection, and whole-market/global claims remain outside the runtime until
their data and comparability gates are met.

## Deployment shape

The API has a non-root Docker image with a health check. The Streamlit UI currently runs
as a local process and targets `SKILLPULSE_API_URL`. This is enough for a reproducible local
portfolio walkthrough, but a public release still needs an explicit hosting design,
environment configuration, browser QA, monitoring, and rollback evidence. Human M5c observations
remain in a Git-ignored local record; the release validator checks completeness and fail-closed
conditions but cannot attest that an accessibility or privacy judgment is true.

For physical-device review, `scripts/run_demo.ps1 -AllowLan` is an explicit temporary boundary:
Streamlit may bind to private IPv4 interfaces, while FastAPI remains on `127.0.0.1`. The mode is
not used by automation, has no TLS/authentication, accepts synthetic samples only, and must be
stopped immediately after review; it is not a public deployment design.
