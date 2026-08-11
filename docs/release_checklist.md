# SkillPulse AI Portfolio Release Checklist

**Audit date:** 11 August 2026
**Current decision:** no-go for public release; local portfolio demo is reproducible

## What is ready

- Ruff passes and 103 Python tests pass.
- The one-command launcher starts FastAPI and Streamlit, verifies both health endpoints,
  and removes both processes in smoke mode.
- Three privacy-safe Streamlit AppTest scenarios cover sample loading, empty input,
  extraction/matching success, and domain-error presentation without external networking.
- CI Playwright verifies four Chromium 1440px/390px states plus a Firefox desktop keyboard-match
  smoke without horizontal overflow; three synthetic screenshots were reviewed and published with pinned hashes.
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
The public tree is a parentless product history containing 105 allowlisted product files;
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
### 2. Human accessibility, WebKit, loading/offline media, and narration remain open

CI-hosted Playwright Chromium passes desktop/mobile overflow assertions and keyboard activation;
Firefox independently passes the keyboard-triggered desktop match at 1440px. Reviewed empty,
matching, and mobile-extraction screenshots are published with exact SHA-256 pins; invalid local
crash pages remain excluded.
The unrelated portable-report renderer still blocks its own unverified HTML output.

Remaining completion evidence:

- human focus/contrast review, screen-reader validation, and WebKit/Safari coverage where available;
- real-browser loading and API-offline states, beyond existing widget/API-client automation;
- a 2-4 minute public-safe video/GIF following `docs/demo_checklist.md`;
- no real CV or third-party raw description in any additional media.

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
