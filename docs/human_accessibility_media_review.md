# M5c Human Accessibility and Demo-Media Review

This pack turns the remaining human gate into a repeatable review. Automation may validate
the record, but it must never fill reviewer judgments or claim that the gate passed.

## Keep the review private by default

Copy the blank public template into the Git-ignored `artifacts/` directory. Use only a
pseudonymous reviewer code; do not enter a name, email, local user path, CV text, or job
description into the record.

```powershell
New-Item -ItemType Directory -Force artifacts | Out-Null
Copy-Item configs/human_accessibility_review.template.json `
  artifacts/human_accessibility_media_review.json
```

The completed JSON and video/GIF stay local until a person separately checks them for
privacy and authorizes publication. Do not stage either file automatically.

## Review environments

Run the local demo using `docs/demo_checklist.md`, then record all three environments:

1. `screen_reader`: name the operating system, browser, and assistive technology used.
2. `mobile_real_device`: use a physical phone or tablet and record its class and browser.
3. `real_safari`: use Safari on Apple hardware when available. If it is unavailable, set
   only this environment to `not_applicable` and explain why in `notes`; Playwright WebKit
   evidence is useful context but is not a human Safari claim.

`screen_reader` and `mobile_real_device` cannot be waived.

## Required human checks

For every check, set `status` to `pass` or `fail` and write a short `evidence_note` that
states what the reviewer observed. The review cannot pass with an empty note.

- `keyboard_focus_order`: all controls are reachable in a logical sequence without a mouse.
- `visible_focus`: the active control is visually identifiable throughout the journey.
- `contrast`: text, controls, focus indicators, and chart labels remain distinguishable.
- `screen_reader_structure`: page title, headings, tabs, forms, buttons, and tables are understandable.
- `status_announcements`: loading, success, and API availability changes are perceivable.
- `error_identification`: blank-input and API-offline errors are located and explained without echoing input.
- `chart_text_alternatives`: KPI values, denominators, table data, and caveats communicate the chart meaning.
- `mobile_responsiveness`: extraction, matching, and market journeys remain usable on the physical device.
- `data_table_readability`: columns, sorting context, values, and active filters are understandable.

Log defects in `findings` with a unique ID, severity, status, and non-sensitive summary.
Any open `blocker` or `high` finding prevents completion.

## Narrated walkthrough gate

Record a 120-240 second walkthrough following `docs/demo_checklist.md`. Use only the
built-in synthetic examples or text that has been manually redacted. Before marking media
as passed, a human must confirm:

- no real name, email, phone number, CV, raw source row, annotation, local path, token, or credential is visible;
- narration covers the problem, extraction, explainable matching, aggregate market scope,
  evaluation limitations, and decision-support disclaimer;
- `duration_seconds`, all three media booleans, and a non-sensitive `artifact_reference` are filled.

An artifact reference may be a neutral local identifier such as `m5c-walkthrough-v1`; do
not put a user directory or private sharing URL in the JSON.

## Validate without creating evidence

Check structure while the review is in progress:

```powershell
skillpulse-release-review artifacts/human_accessibility_media_review.json
```

After the human has set `review_status` to `complete` and signed
`human_attestation=true`, enforce the completion gate:

```powershell
skillpulse-release-review artifacts/human_accessibility_media_review.json --require-complete
```

Exit code `0` means the record is structurally valid and, with `--require-complete`, all
machine-checkable completion rules pass. Exit code `1` means human evidence is incomplete;
exit code `2` means the document is malformed. This validator does not prove the truth of
the observations, accessibility conformance, or publication safety; the human reviewer
remains accountable for those judgments.
