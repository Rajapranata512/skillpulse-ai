# Market Snapshot Metric Contract

## Decision and audience

The public dashboard answers one bounded question for job seekers and portfolio reviewers:
**what requirements, titles, locations, and seniority labels appear most often in this specific
30-day Indonesian data-and-analytics dataset?** It is descriptive decision support, not a census,
forecast, hiring score, or salary model.

## Source and observation window

- Source: *Indonesian Data & Analytics Jobs in Jobstreet*, Rafli Rizkya Sakti Nugraha, Kaggle
  version 1, CC BY 4.0.
- Window: 25 August–24 September 2025 (30 days).
- Scope: 555 cleaned posting rows from one source portal; Indonesian, English, and mixed text.
- Public runtime data: `configs/market_snapshot.json`, an aggregate-only derivative. Raw rows,
  companies, descriptions, identifiers, and salary values are excluded.

## Metric definitions

| Metric | Definition | Denominator / grain | Intended use |
|---|---|---|---|
| Listings | Cleaned posting rows after the existing composite-key deduplication | 555 posting rows | Snapshot size |
| Unique descriptions | Exact-unique normalized full descriptions | 542 descriptions | Skill-demand denominator |
| Reported provinces | Distinct non-missing source province labels | Posting rows | Coverage context, not geographic representativeness |
| Salary disclosed | Rows with a parseable positive salary | 555 posting rows | Data-quality guardrail only |
| Requirement demand | Unique descriptions containing at least one canonical taxonomy match | 542 unique descriptions | Relative explicit-text frequency |
| Title frequency | Case-insensitive title count after whitespace normalization | 555 posting rows | Descriptive title mix |
| Location / seniority mix | Source-provided label count; missing values are `Unknown` | 555 posting rows | Dataset composition |

Percentages are rounded to four decimal places in the public artifact. Requirement matches are
deduplicated within each description, so repeated aliases do not inflate the count. Exact duplicate
descriptions are counted once for requirement demand but remain separate listing rows for the other
composition metrics.

## Suppression and privacy

Title and extracted-requirement groups with fewer than three observations are omitted from the public
artifact. Location and normalized-role filter slices require at least ten exact-unique descriptions;
filters are independent one-dimensional slices rather than sparse cross-combinations. The artifact
contains no row-level data, company names, raw descriptions, contact details,
or salary amounts. A SHA-256 fingerprint links it to the private cleaned input without publishing that
input.

## Valid and invalid claims

Valid: “SQL appears in X of 542 unique descriptions in this dataset and window.”

Invalid: “SQL demand is growing,” “this represents every Indonesian employer,” “these are global
trends,” or “the disclosed salaries support a production salary prediction.” There is only one
observation window and only 77 of 555 rows disclose salary, so time-series and salary modelling remain
data-gated.
