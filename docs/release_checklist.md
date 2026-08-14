# SkillPulse AI Portfolio Release Checklist

**Audit date:** 11 August 2026
**Current decision:** no-go for public release; local portfolio demo is reproducible

## What is ready

- Ruff passes and 138 Python tests pass.
- The one-command launcher starts FastAPI and Streamlit, verifies both health endpoints,
  and removes both processes in smoke mode.
- Four privacy-safe Streamlit AppTest scenarios cover sample loading, empty input,
  extraction/matching success, market filters, and domain-error presentation without external networking.
- The public aggregate reconciles 555 listings and 542 unique descriptions, provides four location
  and four normalized-role slices, and excludes company/job/raw-description/salary-value fields.
- Playwright verifies seven Chromium responsive/loading states, safe API-offline handling, and
  Firefox plus WebKit keyboard matches without horizontal overflow; three reviewed screenshots remain SHA-pinned.
- The API container has a verified healthy, non-root local smoke result.
- Raw source data, primary/blind annotations, AI challenger workbooks, processed CSV, and
  review-pack HTML are covered by explicit Git ignore rules.
- Model card, data card, architecture, annotation guide, case study, API contract, demo
  checklist, and aggregate evaluation evidence exist.
- A strict, privacy-minimizing M5c JSON template and validator reject premature accessibility/media
  completion, missing human attestation, unsafe media flags, and unresolved high-severity findings.
- The explicit `-AllowLan` review mode enables a physical device on a trusted Private network while
  keeping FastAPI loopback-only; automation cannot combine this mode with `-SmokeTest`.
- Unsupported human-agreement, human-relevance, salary, and global-market claims are
  explicitly blocked.
- Recruiter-facing local links and documented API endpoints are protected by regression tests.

## Release blockers

### 1. Repository publication is complete

The clean product history is public at
`https://github.com/Rajapranata512/skillpulse-ai` with `main` as the default branch.
The public tree is a parentless product history containing only allowlisted product files;
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
### 2. Human accessibility, real-device review, and narration remain open

CI-hosted Chromium passes desktop/mobile overflow, loading, keyboard, validation, extraction, and
safe API-offline assertions. Firefox and Playwright WebKit independently pass the keyboard-triggered
desktop match at 1440px. Eight synthetic captures are retained as CI artifacts; three recruiter-facing
screenshots remain published with exact SHA-256 pins. Desktop/mobile market captures stay in
short-lived QA artifacts, and invalid local crash pages stay excluded.
The unrelated portable-report renderer still blocks its own unverified HTML output.

Remaining completion evidence:

- a human completes the private-by-default [M5c review pack](human_accessibility_media_review.md),
  including focus/contrast, screen-reader, mobile real-device, and real Safari evidence where available;
- physical-device review uses `scripts/run_demo.ps1 -AllowLan -NoBrowser` with synthetic samples on
  a trusted Private network, never public Wi-Fi, port forwarding, or a public tunnel;
- `skillpulse-release-review artifacts/human_accessibility_media_review.json --require-complete` returns `0`;
- a 2-4 minute public-safe video/GIF follows the condensed journey in `docs/demo_checklist.md`;
- no real CV, third-party raw description, PII, credential, or local path appears in review evidence or media.

### 3. Independent ML evidence requires humans

- ML-QG-2: 0/100 blind second-human annotation.
- ML-QG-3: 0/50 independent human relevance judgments.

Agents and AI tools must not fill those labels because automation would invalidate the
independence claim. The local demo may proceed with visible caveats; an independently
validated claim may not.

### 4. Public deployment target is frozen; provisioning evidence is open

The owner approved a Render Free service in Singapore with a zero-cost ceiling. The checked-in
Blueprint defines one non-root container: Streamlit is public through managed TLS, FastAPI remains
loopback-only, and no database, disk, or secret is provisioned. Request-body access logging and
usage telemetry are disabled; a process-wide 30-analysis/minute budget collects no identifiers.

The target decision, health checks, free-tier limitations, smoke command, monitoring, and rollback
procedure are documented in the Render deployment runbook. Portfolio-ready status still requires an
authenticated owner to provision the service, run the HTTPS/loopback smoke test, confirm operational
logs contain no submitted content, and capture a successful rollback check.

## Pre-publication commands

```powershell
ruff check src tests
pytest -q
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -SmokeTest
python scripts/publication_guard.py --commit HEAD
python -m skillpulse.release.human_review configs/human_accessibility_review.template.json
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
