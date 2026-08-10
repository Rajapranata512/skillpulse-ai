# SkillPulse AI Demo Checklist

Use this checklist to run a repeatable five-minute portfolio demonstration without raw
CV files, unpublished annotations, or salary claims.

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

## Pre-demo gate

Before recording or sharing:

- `ruff check src tests` passes.
- `pytest -q` passes.
- `reports/api_container_smoke.json` still reports a healthy non-root container.
- `reports/ui_smoke.json` still reports API and Streamlit health `ok`.
- `docs/model_card.md` still matches the latest aggregate evaluation reports.
- No real CV, raw annotation, CSV, or XLSX file is staged for publication.

## Five-minute walkthrough

1. **Problem and scope — 30 seconds.** Explain that Indonesian job seekers need explicit,
   evidence-backed skill-gap guidance. State that this snapshot covers 555 data and
   analytics postings, not the whole labour market.
2. **Extraction — 60 seconds.** Open the included bilingual example. Run extraction and
   point to canonical technical skills, tools, education, experience, seniority, and work
   arrangement. Emphasize that only explicit text is extracted.
3. **Matching — 90 seconds.** Run the example match. Show the overall verdict, component
   weights, matched evidence, missing evidence, and learning priorities. Explain that an
   absent requirement category is not silently scored as a failure.
4. **Engineering — 60 seconds.** Open `http://127.0.0.1:8000/docs`. Show the four versioned
   endpoints, strict schemas, model/taxonomy versions, and 50,000-character limit.
5. **Evaluation and honesty — 60 seconds.** Open the portfolio report and model card.
   Distinguish the 100-row AI-assisted primary evaluation from the pending independent
   0/100 annotation and 0/50 human relevance gates. State why the semantic challenger was
   not promoted.

## Expected observations

- The UI displays API status and contract version.
- Extraction returns structured canonical entities and a disclaimer.
- Matching exposes the score calculation instead of only a final number.
- The included example identifies at least one realistic learning gap.
- No file upload, raw CV retention, or protected-attribute input is present.

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
and a functional UI. Do not call it independently validated, production deployed, a
salary predictor, a market-trend platform, or an automated hiring system.
