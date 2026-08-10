# SkillPulse AI Data Card

## Decision summary

The project source is now verified as **Indonesian Data & Analytics Jobs in Jobstreet**,
Kaggle version 1, published by Rafli Rizkya Sakti Nugraha under **CC BY 4.0**. A fresh
Kaggle download and the local CSV are an exact 1,059,991-byte and SHA-256 match. The data
is suitable for bounded exploratory NLP, taxonomy development, and human-reviewed
extraction evaluation. It is not sufficient for whole-market, time-series, or production
salary claims.

## Dataset and grain

- Unit: one cleaned job posting per row.
- Scope: Indonesian Data & Analytics vacancies from JobStreet Indonesia.
- Observation window: 25 August–24 September 2025 (30 days).
- Source rows: 555; source columns: 10.
- Complete job-description text: 555/555 rows.
- Salary disclosed: 77/555 rows (13.87%).
- Local pipeline duplicates on the documented composite key: 0.
- Annotation sample: 100 deterministic rows (`random_state=42`), of which 30 are
  human-confirmed and 70 still require review.

Machine-readable pipeline counts are stored in `reports/data_quality.json`. Provenance is
stored in `data/provenance/sources.yaml`.

## Verified provenance

| Property | Verified value |
|---|---|
| Dataset | Indonesian Data & Analytics Jobs in Jobstreet |
| Creator | Rafli Rizkya Sakti Nugraha |
| Platform | Kaggle |
| Version | 1, updated 28 September 2025 |
| License | Attribution 4.0 International (CC BY 4.0) |
| Source URL | https://www.kaggle.com/datasets/raflirizkya/indonesian-data-and-analytics-jobs-in-jobstreet |
| Source portal | JobStreet Indonesia public postings |
| Local bytes | 1,059,991 |
| SHA-256 | `a857603f6d8a2b0344f4a4f00747e037ecc4ca3aa6b760800560ad4fe906887c` |
| Identity check | exact match against a fresh Kaggle version-1 download |

The publisher describes this as a cleaned dataset: direct-link, short-description, and
tool-count columns were removed, and personal contact information was scrubbed from full
descriptions. The exact collection tooling or script is not documented.

## License and public-release decision

CC BY 4.0 permits sharing and adaptation when appropriate credit, a license link, and a
modification notice are provided. The raw CSV is nevertheless excluded from public Git by default because individual job
descriptions originate from third-party postings and may carry additional platform-term or
rights constraints. Human annotation CSVs, editable review batches, and HTML review packs
also contain copied descriptions and are excluded. Reproduction uses the Kaggle source, a
pinned hash, and `scripts/fetch_dataset.ps1`; public evidence remains aggregate or redacted.

Required attribution:

> Indonesian Data & Analytics Jobs in Jobstreet by Rafli Rizkya Sakti Nugraha, Kaggle
> dataset version 1, licensed under CC BY 4.0. Modified by SkillPulse AI through
> validation, sampling, normalization, annotation, and derived analysis.

## Checks performed

| Check | Evidence | Result |
|---|---:|---|
| Source schema | 10 required source columns | pass |
| Row grain | 555 rows; no pipeline duplicates | pass |
| Complete descriptions | 555/555 | pass |
| Pinned source identity | byte size + SHA-256 | exact match |
| License metadata | CC-BY-4.0 + canonical URL | verified |
| Annotation schema | 100 unique source rows | pass |
| Human-confirmed primary annotations | 100/100 | pass for ML-QG-1 baseline |
| Primary audit coverage | 100/100 | pass |
| Independent double annotation | 0/100 | blind batch ready; human gate |

## Findings and analytical risk

1. **Source identity is trustworthy for reproduction — pass, high confidence.** The local
   file matches Kaggle version 1 exactly. Automated validation fails on hash or size drift.
2. **Market representativeness is limited — high severity, high confidence.** One role
   family, one source portal, and one 30-day window cannot represent the full Indonesian
   labour market or a trend.
3. **Salary evidence is sparse — high severity for modelling, high confidence.** Only
   13.87% of rows disclose salary, so salary modelling remains blocked.
4. **Collection implementation is not auditable — medium severity, high confidence.** The
   publisher states the source and cleaning steps but does not provide the collection
   script/tooling.
5. **Human evaluation exists but is development-set evidence — medium-high severity for
   performance claims.** All 100 rows are project-owner-confirmed, but 70 were pre-labelled
   by the evaluated extractor and the first 30 guided rule improvement. ML-QG-1 is met as a
   transparent portfolio baseline, not independent generalization evidence. A fully blind
   second-annotator batch is ready; ML-QG-2 remains open.

No temporal anomaly analysis is possible because the dataset is one bounded snapshot and
does not retain posting-level observation dates suitable for a time series.

## Privacy and responsible AI

Do not add personal contact information, publish CV text, or retain uploaded CVs by
default. Exclude protected characteristics from scoring. Publish aggregate results only
when group sizes are sufficient. SkillPulse is decision support, not an automated hiring
or rejection system.

## Reproducibility

```powershell
powershell -ExecutionPolicy Bypass -File scripts/fetch_dataset.ps1
python -m skillpulse.data.provenance --require-local
skillpulse-prepare
skillpulse-evaluate --gold-report reports/extraction_gold_eval.json
ruff check src tests
pytest -q
```

The portable report artifact is stored in `reports/data_provenance_artifact.json`. The
current shared HTML renderer failed horizontal-overflow QA; details are recorded in
`reports/data_provenance_report_qa.md`, so no unverified HTML report is delivered.
