# Matching Relevance Annotation Rubric v0.1

Use this rubric to rate synthetic CV–job pairs independently from the model score. Read the
complete CV and job text. Do not inspect SkillPulse output before recording the human score.

## Score

| Score | Label | Decision rule |
|---:|---|---|
| 4 | Excellent match | Meets nearly all explicit core requirements with no material core gap. |
| 3 | Good match | Meets most core requirements; remaining gaps are limited and learnable. |
| 2 | Partial match | Relevant background exists, but several material requirements are missing. |
| 1 | Weak match | Limited explicit overlap; major technical or experience gaps dominate. |
| 0 | Not relevant | Little or no explicit evidence for the stated role requirements. |

## Review procedure

1. Compare only explicit evidence; do not infer skills from titles, prestige, age, gender,
   school, employer, or other protected/proxy attributes.
2. Consider technical skills, named tools, experience, education, seniority, work
   arrangement, and explicitly requested soft skills.
3. Treat technical/tool gaps as more material than optional soft-skill gaps, but do not use
   the model's internal weights.
4. Enter one integer `human_relevance_score` from 0 to 4 and a concise
   `human_rationale` naming the most important matches and gaps.
5. Add an independent `annotator`, retain ambiguity in `notes`, and set
   `review_status=reviewed` only after completing the pair.
6. Keep all 50 labels frozen before running `skillpulse-relevance evaluate` or inspecting
   baseline/challenger outputs.

## Agreement and adjudication

For a later multi-rater extension, two raters should score the same pairs independently.
Discuss scores differing by two or more points, preserve the original decisions, and store
an adjudicated score separately rather than overwriting individual judgments.

The synthetic set measures controlled requirement coverage. It does not establish hiring
fitness, candidate quality, fairness, or performance on natural CV distributions.
