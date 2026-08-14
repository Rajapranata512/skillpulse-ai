# SkillPulse AI Demo Checklist

Use this checklist to run a repeatable five-minute portfolio demonstration without raw
CV files, unpublished annotations, or salary claims. For the separate 2-4 minute narrated
release artifact, use a condensed version of this journey and complete
`docs/human_accessibility_media_review.md`; the live walkthrough is not itself human evidence.

## One-command start

From the repository root on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -Install
```

`-Install` installs only the API and UI extras into the active Python environment. Omit it
on later runs. The launcher starts FastAPI on `127.0.0.1:8000`, waits for `/health`, then
starts Streamlit on `127.0.0.1:8501`. Stop the demo with `Ctrl+C`; the launcher also stops
the API process it created.

Optional port and browser controls:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 `
  -ApiPort 8010 -UiPort 8510 -NoBrowser
```

Run a headless start-health-stop check without leaving either service running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -SmokeTest
```

For the human physical-device gate only, `-AllowLan` explicitly binds the Streamlit UI
to the computer's private LAN while keeping FastAPI on loopback:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -AllowLan -NoBrowser
```

Use the printed physical-device URL only on a trusted Private network with synthetic
samples, then stop with `Ctrl+C`. Do not use public Wi-Fi, port forwarding, or a public
tunnel. See `docs/human_accessibility_media_review.md` for the required human evidence.

## Pre-demo gate

Before recording or sharing:

- `ruff check src tests` passes.
- `pytest -q` passes.
- `reports/api_container_smoke.json` still reports a healthy non-root container.
- `reports/ui_smoke.json` still reports API and Streamlit health `ok`.
- `reports/ui_automated_qa.json` still reports sample, empty, success, and safe-error journeys passed.
- `reports/ui_browser_qa.json` records three dashboard charts on desktop/mobile Chromium and
  desktop Firefox/WebKit, while still matching the three pinned screenshots in `docs/assets/`.
- `reports/market_snapshot_quality.json` has verdict `pass` and all reconciliation checks are true.
- `docs/model_card.md` still matches the latest aggregate evaluation reports.
- No real CV, raw annotation, CSV, or XLSX file is staged for publication.

## Five-minute walkthrough

1. **Problem and scope — 30 seconds.** Explain that Indonesian job seekers need explicit,
   evidence-backed skill-gap guidance. State that this snapshot covers 555 data and
   analytics postings, not the whole labour market.
2. **Extraction — 60 seconds.** Open the included bilingual example. Run extraction and
   point to canonical technical skills, tools, education, experience, seniority, and work
   arrangement. Mark one entity as incorrect, confirm review, and show that the downloadable
   feedback contains canonical labels/verdicts without source text or server submission.
3. **Matching — 75 seconds.** Run the example match. Show the overall verdict, component
   weights, matched evidence, missing evidence, and learning priorities. Explain that an
   absent requirement category is not silently scored as a failure.
4. **Market snapshot — 45 seconds.** Open the market tab. Change the segment from all listings
   to a safe location or normalized-role slice, then filter requirements by category. Point out
   the active denominator, 30-day window, Jakarta concentration, suppression threshold, and why
   salary/trend claims are disabled.
5. **Engineering — 45 seconds.** Open `http://127.0.0.1:8000/docs`. Show the four versioned
   endpoints, strict schemas, model/taxonomy versions, and 50,000-character limit.
6. **Evaluation and honesty — 45 seconds.** Open the portfolio report and model card.
   Distinguish the 100-row AI-assisted primary evaluation from the pending independent
   0/100 annotation and 0/50 human relevance gates. State why the semantic challenger was
   not promoted.

## Condensed 2-4 minute recording

Keep the problem/scope, extraction, matching, and market sections to roughly 30-40 seconds each.
Use the remaining time for evaluation caveats, privacy, and the decision-support disclaimer; API
internals can remain in the five-minute live version. Record only built-in synthetic examples, then
complete the private media checks and human attestation in the M5c review pack.

## Expected observations

- The UI displays API status and contract version.
- Extraction returns structured canonical entities and a disclaimer.
- Matching exposes the score calculation instead of only a final number.
- Desktop and mobile layouts, including the market KPI cards and charts, have no horizontal overflow.
- The included example identifies at least one realistic learning gap.
- No file upload, raw CV retention, or protected-attribute input is present.
- Blank input is stopped before an API request and API errors do not echo submitted text.

Exact demo scores may change after an intentionally versioned taxonomy or matcher update.
When that happens, regenerate the dependent evidence and update the model card before
recording new media.

## Stop and cleanup

Press `Ctrl+C` in the launcher terminal. It terminates the Streamlit foreground process
and the exact API process it started. If the terminal is forcibly closed, inspect only the
configured ports and stop the corresponding Python processes manually; do not terminate
unrelated Python sessions.

## Troubleshooting

- **Dependency check fails:** activate the intended Python 3.11+ environment and rerun with
  `-Install`.
- **API port is occupied:** choose another `-ApiPort`; the launcher automatically passes
  the matching URL to Streamlit.
- **UI port is occupied:** choose another `-UiPort`.
- **API health times out:** run `skillpulse-api` directly to inspect the startup exception.
- **Browser does not open:** navigate to the printed UI URL or use `-NoBrowser` in remote
  environments.

## Claims permitted in the demo

You may describe the application as a tested local portfolio system with reproducible
data provenance, deterministic bilingual extraction, explainable matching, a strict API,
and a filterable aggregate 30-day market snapshot. Do not call it independently validated,
production deployed, a salary predictor, a market-trend platform, a whole-market census,
or an automated hiring system.
