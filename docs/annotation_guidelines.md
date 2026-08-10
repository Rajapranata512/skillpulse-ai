# SkillPulse Annotation Guidelines v0.2

Annotate only information explicitly present in the text. Do not infer a skill from a
job title or company industry. Use the canonical names in `configs/skill_taxonomy.yaml`
and separate multiple labels with `|`.

## Labels

- `technical_skills`: methods and capabilities such as SQL, statistics, ETL, or machine learning.
- `tools`: named software, platforms, libraries, databases, and cloud services.
- `soft_skills`: explicitly requested interpersonal or working behaviours.
- `education`: High School, Diploma, Bachelor, Master, or Doctorate.
- `experience_years`: minimum explicitly requested years; use `0` for explicit fresh-graduate eligibility.
- `seniority`: entry, mid, senior, or unknown.
- `work_arrangement`: remote, hybrid, onsite, or unknown.

## Boundary decisions

- Label canonical skills that are explicitly mentioned even when optional or “a plus”;
  requirement strength is not represented in schema v0.2 and must be noted when material.
- Do not label a technical skill when the term occurs only as a degree/major field.
- Geographic names such as Java and company/product names are not programming skills.
- Map generic software only when a canonical tool is named; generic “MS Office”, ERP,
  analytics software, or BI tools are not silently converted into a specific product.
- Seniority requires an explicit title/level signal: intern, fresh graduate, or junior map
  to `entry`; mid-level maps to `mid`; senior, lead, manager, head, or supervisor map to
  `senior`. Do not infer seniority from experience years alone.
- Experience is the minimum candidate experience explicitly requested. Company age,
  program duration, time since graduation, and employment contract duration are not
  candidate experience.
- Work arrangement requires explicit remote/WFH, hybrid, onsite/WFO wording. A city,
  office placement, internet requirement, or willingness to relocate is not sufficient.
- When D3/S1 or another alternative is accepted, label every explicitly accepted
  canonical education level.
- Responsibilities may contain skills, but organization names, audience names, and
  department labels must not be converted into candidate skills.
- AI-assisted rows use `review_status=ai_reviewed`; only a human-verified row may use
  `review_status=reviewed` and count toward human gold claims.

## Review procedure

1. Read the complete text, not the weak labels alone.
2. Treat every `suggested_*` field in an exported review batch as an AI suggestion, not
   ground truth; correct omissions and false labels in every editable `gold_*` column.
3. Use `unknown` when seniority or work arrangement is not stated.
4. Add a human `annotator` identifier and a non-empty `notes` entry recording the review
   outcome or ambiguity.
5. Set `review_status` to `reviewed` only after all columns are checked. Leave incomplete
   rows as `needs_review`; the importer will not promote them.
6. Import through `skillpulse-extract review-import --confirm-human-review` so source
   fingerprints, canonical labels, workflow status, and the audit trail are validated.
7. Update these guidelines when the same ambiguity recurs.

## Blind second-annotator procedure

1. Use `data/annotations/second_annotator_blind.csv`; it intentionally contains no primary
   labels, weak labels, or extractor suggestions.
2. The second annotator must be a different human and must not inspect the primary gold,
   review packs, model output, or evaluation report before finishing all assigned rows.
3. Fill every `gold_*` field from the complete text, add an independent `annotator` ID and
   non-empty `notes`, then set completed rows to `reviewed`.
4. Do not copy primary decisions into the blind file. Preserve disagreements until the
   agreement report has been generated.
5. Run `skillpulse-extract agreement` only after labels are frozen. If field-level Kappa is
   below 0.75, document recurring ambiguity, revise guidelines, and adjudicate separately.

The existing `tools`, `pengalaman`, and `level` columns are weak labels. They must not be
reported as a human-validated gold standard.
