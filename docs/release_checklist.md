# SkillPulse AI Portfolio Release Checklist

**Audit date:** 10 August 2026
**Current decision:** no-go for public release; local portfolio demo is reproducible

## What is ready

- Ruff passes and 94 Python tests pass.
- The one-command launcher starts FastAPI and Streamlit, verifies both health endpoints,
  and removes both processes in smoke mode.
- The API container has a verified healthy, non-root local smoke result.
- Raw source data, primary/blind annotations, AI challenger workbooks, processed CSV, and
  review-pack HTML are covered by explicit Git ignore rules.
- Model card, data card, architecture, annotation guide, case study, API contract, demo
  checklist, and aggregate evaluation evidence exist.
- Unsupported human-agreement, human-relevance, salary, and global-market claims are
  explicitly blocked.

## Release blockers

### 1. Repository publication is complete

The clean product history is public at
`https://github.com/Rajapranata512/skillpulse-ai` with `main` as the default branch.
The first public tree is a parentless root commit containing 97 allowlisted product files;
it has no relationship to the historical research commits.

The former research history remains local only on `research-history-local-20260810` and
`research-origin`. `RM.ipynb`, both academic PDFs, raw/processed row-level data, annotations,
AI workbooks/labels, and stale internal reports are absent from the public tree. Every push
runs `.githooks/pre-push`, and CI runs the same committed-snapshot guard.

Future publication completion evidence:

- stage only intended product paths;
- run full tests plus the publication guard;
- use a GitHub noreply commit identity;
- push only `origin main`, never `--all`, `--mirror`, tags, or the research branch;
- record the remote SHA and CI result in the handoff.
### 2. Visual and media evidence needs a working browser environment

API/UI functional smoke is complete, but local headless Edge/Chrome returned browser crash
pages. The shared portable-report renderer also reports desktop horizontal overflow. No
invalid screenshot or unverified HTML is published.

Completion evidence:

- desktop and mobile layouts are reviewed in a working browser;
- loading, empty, API-offline, validation-error, extraction, and matching states are
  captured;
- a 2-4 minute public-safe video/GIF follows `docs/demo_checklist.md`;
- no real CV or third-party raw description appears in the media.

### 3. Independent ML evidence requires humans

- ML-QG-2: 0/100 blind second-human annotation.
- ML-QG-3: 0/50 independent human relevance judgments.

Agents and AI tools must not fill those labels because automation would invalidate the
independence claim. The local demo may proceed with visible caveats; an independently
validated claim may not.

### 4. Public deployment needs a hosting decision

The local container and UI are ready for target selection, but no public infrastructure is
authorized. Before deployment, document:

- API and UI hosting targets, region, and cost ceiling;
- TLS, allowed origins, rate limits, abuse controls, and secret handling;
- retention/logging behavior that preserves the no-raw-CV-persistence contract;
- health, latency, failure-rate, and availability monitoring;
- rollback procedure and ownership.

## Pre-publication commands

```powershell
ruff check src tests
pytest -q
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -SmokeTest
python scripts/publication_guard.py --commit HEAD
git status --short
```

Inspect ignored sensitive working files without adding them:

```powershell
git check-ignore -v -- `
  "lowongan data dan analytics jobstreet.csv" `
  "data/annotations/gold_sample.csv" `
  "data/annotations/second_annotator_blind.csv" `
  "data/annotations/SkillPulse_AI_Annotation_Challenger_FIXED.xlsx"
```

## Final go/no-go

Only label the project **portfolio-ready** when the PRD Definition of Done is satisfied.
Until then, use **working portfolio project with a reproducible local demo** and link the
model card, case study, and open-gate evidence.
