# SkillPulse AI Portfolio Report QA

**Verified:** 10 August 2026  
**Canonical artifact:** `reports/portfolio_report_artifact.json`  
**Delivery status:** blocked by shared portable renderer; no HTML delivered

## Checks completed

- JSON parsing and source-metric reconciliation passed.
- The portable report package contract passed after declaring visible table sort fields
  and attaching exact SQL source metadata to every metric/chart/table source.
- The title and first visible `Executive Summary` block match the executive-report
  contract.
- Both quantitative charts use zero-based grouped bars, a categorical model palette,
  compatible units, visible legends/labels, adjacent interpretation, and source metadata.
- The gate table preserves exact current/minimum counts and does not convert missing human
  work into model scores.

## Browser verification blocker

The official portable builder reached browser verification but reported
`horizontal_overflow` at the 1440px desktop viewport. One targeted correction removed the
wide seven-column model table and shortened the gate table, but the shared renderer still
reported the same overflow. This matches the existing renderer limitation recorded for
the provenance report.

Per the report workflow, no unverified HTML file is delivered and no hand-authored HTML
fallback is substituted. The canonical JSON, source metadata, metric snapshot, and chart
map are retained so packaging can be retried only after the shared renderer changes.

Temporary verifier screenshots were removed because they are failure artifacts, not
portfolio deliverables, and can be regenerated from the canonical JSON.
