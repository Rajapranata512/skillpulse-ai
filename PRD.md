# SkillPulse AI — Product Requirements Document

**Product:** SkillPulse AI
**Tagline:** Indonesian and Global Job Intelligence Platform
**Status:** Active product direction
**Version:** 1.1
**Owner:** Portfolio project
**Last updated:** 2026-08-10

## 0. Auto-Sync Delivery Snapshot

Blok ini disinkronkan otomatis oleh agent setelah setiap sesi yang mengubah repository.
Ini adalah ringkasan delivery, bukan pengganti requirement detail atau Project State.
Timpa isi di antara marker; jangan append session log.

<!-- AUTO-SYNC:START -->
**Last synchronized:** 2026-08-10
**Current phase:** Phase 3 complete locally; Phase 4 functional demo is at a visual-QA gate;
Phase 5 public source/story/security evidence is complete and application deployment remains gated
**Status:** Working portfolio product published at `https://github.com/Rajapranata512/skillpulse-ai`
with clean history, green CI, privacy/security publication controls, verified extraction/matching
baselines, contract v1, FastAPI, non-root container, Streamlit demo, model card, architecture, and
case study. It is not portfolio-ready because responsive media, independent annotation/relevance,
and public application deployment remain open.
**Completed this session:** created a parentless 97-file public product history, preserved research
history locally only, configured GitHub noreply identity, added deny-by-default ignores, staged/commit
publication guard, executable pre-push hook, six security tests, CI guard/read-only permissions,
SECURITY/PRIVACY policies, and Dependabot. Pushed `main`, verified CI success, then applied the
official checkout v7 update after green bot checks.
**Verified baseline:** 94 tests and Ruff passed. Complete HEAD publication guard scanned 97 files /
456,168 bytes. Public `main` matched local `0f6a741`; CI run `31403489015` succeeded. Raw/processed
row-level data, annotations, AI workbooks/labels, academic artifacts, stale internal reports,
credentials, PII patterns, and local paths are absent from the public tree.
**Selected next task:** `M5b — responsive browser QA and public-safe demo media (HUMAN/ENV-GATE)`.
**Next completion check:** a working browser is used to review desktop/mobile plus loading, error,
empty, extraction, and matching states; a 2-4 minute walkthrough contains only synthetic/redacted
text and no crash page or unverified artifact.
**Other gates:** ML-QG-2 is 0/100, ML-QG-3 is 0/50, and salary is 77/555. The public repository is
not a deployed application; hosting/privacy/monitoring/rollback decisions remain owner-gated. The
portable report JSON is valid, but shared renderer overflow still blocks verified HTML.
<!-- AUTO-SYNC:END -->
## 1. Executive summary

SkillPulse AI membantu pencari kerja memahami kecocokan antara CV dan lowongan,
menemukan skill gap, serta menentukan keterampilan yang perlu dipelajari lebih dahulu.
Dalam tahap berikutnya, data lowongan teragregasi juga digunakan untuk menunjukkan tren
permintaan skill di Indonesia dan pasar global.

Nilai utama proyek ini bukan sekadar “menggunakan AI”, melainkan menunjukkan satu sistem
end-to-end yang dapat dipertanggungjawabkan: data provenance, bilingual NLP, human
annotation, statistik evaluasi, explainable matching, API, UI, MLOps, dan product
thinking. Produk harus jujur terhadap keterbatasan data dan tidak menjadi mesin seleksi
otomatis.

### Portfolio pitch

> SkillPulse AI mengekstrak kebutuhan terstruktur dari job description Indonesia/Inggris,
> membandingkannya dengan CV, menjelaskan kecocokan dan skill gap, lalu mengubah bukti
> pasar kerja menjadi learning priorities yang dapat ditindaklanjuti.

## 2. Problem statement

Pencari kerja dan fresh graduate sering tidak mengetahui:

- skill apa yang benar-benar dibutuhkan untuk posisi tertentu;
- perbedaan kebutuhan antara Indonesia dan pasar global;
- skill apa yang belum terlihat di CV mereka;
- posisi mana yang paling sesuai dengan kemampuan saat ini;
- keterampilan mana yang memberi dampak belajar paling besar.

Career center, universitas, dan lembaga pelatihan juga membutuhkan bukti yang lebih cepat
untuk menyesuaikan kurikulum dengan perubahan kebutuhan industri.

Solusi yang ada sering memakai keyword matching tanpa penjelasan, menyajikan salary
estimate tanpa data cukup, atau memberi skor yang tampak presisi tetapi sulit diaudit.

## 3. Product principles — keputusan yang dikunci

1. **Decision support, not automated hiring.** Skor membantu eksplorasi, tidak menentukan
   kelayakan manusia atau menggantikan recruiter.
2. **Evidence before complexity.** Baseline harus dievaluasi pada human gold set sebelum
   transformer, embedding, atau recommendation model diklaim lebih baik.
3. **Explain every score.** Pengguna harus melihat kebutuhan, kecocokan, gap, bobot, dan
   keterbatasan yang membentuk skor.
4. **Bilingual by design.** Bahasa Indonesia, Inggris, dan teks campuran adalah kasus
   utama, bukan edge case.
5. **Privacy by default.** CV tidak disimpan secara default; data pribadi dan atribut
   terlindungi tidak boleh menjadi feature scoring.
6. **Legal data acquisition.** Gunakan open dataset, company career pages yang memberi
   izin, input manual, atau user-submitted job descriptions. Tidak ada scraping agresif.
7. **Uncertainty is a feature.** Sistem harus menolak atau menandai output yang tidak
   didukung data, khususnya salary prediction.
8. **One coherent product.** Notebook riset, pipeline, model, API, dan UI harus menunjuk
   taxonomy serta domain contract yang sama.

## 4. Goals dan non-goals

### Goals

- Mengekstrak skill, tools, soft skills, pendidikan, pengalaman, seniority, dan work
  arrangement dari CV/job description Indonesia dan Inggris.
- Memberikan explainable CV-to-job matching serta skill-gap analysis.
- Menghasilkan learning priorities yang berasal dari gap dan demand evidence.
- Menampilkan tren skill berdasarkan lokasi, role family, dan periode jika metadata
  mencukupi.
- Menyediakan API dan demo UI yang mudah dievaluasi recruiter/hiring manager.
- Menunjukkan reproducibility melalui versioning, tests, CI, data/model documentation,
  serta experiment evidence.

### Non-goals untuk MVP

- Menentukan siapa yang harus diterima/ditolak dalam proses rekrutmen.
- Personality, gender, umur, agama, ras, foto, nama, alamat, atau protected-attribute
  inference.
- Scraping massal LinkedIn/JobStreet atau redistribusi data tanpa hak.
- Salary prediction production-grade dengan dataset saat ini.
- Generative learning roadmap yang mengarang course, sertifikasi, atau demand evidence.
- Mengklaim cakupan seluruh profesi sebelum taxonomy dan dataset mendukungnya.

## 5. Target users dan jobs to be done

### P0 — primary personas

**Job seeker / fresh graduate**
Ketika melihat lowongan, saya ingin mengetahui requirement yang dapat diverifikasi,
kecocokan CV, dan gap prioritas agar saya dapat memilih pekerjaan serta rencana belajar.

**Portfolio reviewer / recruiter teknis**
Ketika menilai proyek, saya ingin melihat data-to-product flow, metodologi evaluasi, dan
trade-off agar kemampuan engineering, ML, statistik, serta product thinking terbukti.

### P1 — secondary personas

**University career center / training provider**
Ingin melihat tren skill per role dan lokasi untuk menentukan intervensi kurikulum.

**Recruiter / platform partner**
Ingin API extraction dan structured requirements yang dapat diaudit, bukan black-box
candidate rejection.

## 6. Core user journey

```text
Paste/upload CV + job description
          ↓
Privacy notice and input validation
          ↓
Bilingual entity extraction with source evidence
          ↓
Explainable category-level matching
          ↓
Matched skills + missing skills + uncertainty
          ↓
Prioritized learning actions and market context
          ↓
Export/share a non-sensitive report
```

Demo harus tetap bekerja memakai example text tanpa CV pribadi.

## 7. Product scope dan priority

### P0 — portfolio MVP

1. Reproducible job-data pipeline dan data-quality report.
2. Versioned bilingual skill taxonomy.
3. Human-reviewed gold set dan extraction evaluation.
4. Explainable CV-to-job matching baseline.
5. Skill-gap list dan deterministic learning priorities.
6. FastAPI endpoints untuk extraction, matching, health, dan model metadata.
7. Responsive demo UI dengan example mode dan privacy-safe input.
8. CI, Docker, documentation, model card, data card, dan reproducible demo.

### P1 — differentiation

1. Sentence-embedding semantic matcher sebagai challenger terhadap rule baseline.
2. Multi-label job-family classifier.
3. Market skill dashboard dengan location/role filters.
4. User feedback untuk “correct/incorrect extraction” tanpa menyimpan CV mentah.
5. Learning roadmap menggunakan curated skill prerequisites dan demand ranking.
6. Indonesian versus global comparison setelah dataset provenance sebanding.

### P2 — data-gated research

1. Salary quantile regression dan prediction intervals.
2. Time-series trend/change detection.
3. Job clustering dan emerging role discovery.
4. Organization dashboard/API commercialization concepts.

## 8. Functional requirements dan acceptance criteria

### FR-01 — Job/CV text ingestion (P0)

- Menerima UTF-8 plain text Indonesia, Inggris, atau campuran.
- Menolak input kosong, terlalu besar, atau format yang tidak didukung dengan pesan jelas.
- File PDF/DOCX parsing boleh ditambahkan setelah text flow stabil.
- CV tidak disimpan secara default.

**Accept:** example text berhasil diproses end-to-end; invalid input mempunyai automated
test; privacy behavior terdokumentasi.

### FR-02 — Entity extraction (P0)

Entity minimum:

| Entity | Contoh canonical |
|---|---|
| Technical Skill | Python, SQL, Statistics, Machine Learning |
| Tool | Power BI, Tableau, Docker, PostgreSQL |
| Soft Skill | Communication, Leadership, Problem Solving |
| Education | High School, Diploma, Bachelor, Master, Doctorate |
| Experience | minimum years explicitly stated |
| Seniority | entry, mid, senior, unknown |
| Work Arrangement | remote, hybrid, onsite, unknown |

Setiap dictionary entity mengembalikan canonical value, matched text, start, dan end.
- Experience hanya diambil dari candidate-requirement context; company age, contract/
  program duration, dan graduation window bukan pengalaman kandidat.
- Seniority berasal dari explicit target-role title/level. Jumlah tahun tidak boleh
  menginfer seniority karena experience sudah dinilai sebagai kategori terpisah.
- Short/ambiguous mentions memakai conservative context guards: lokasi Java bukan skill,
  Statistics pada degree-major context bukan capability, dan standalone R hanya diterima
  pada list/skill context yang aman.
- Contextual bilingual patterns dan aliases wajib versioned serta dilindungi regression
  tests; jangan menyesuaikan rule hanya untuk memaksa agreement dengan anotasi AI.

**Accept:** schema stabil, taxonomy versioned, gold evaluation memenuhi ML-QG-1, dan
source-span demo terlihat.

### FR-03 — Explainable matching (P0)

- Bandingkan CV dan job requirements per category.
- Bobot default: technical skills 30%, tools 25%, soft skills 10%, education 10%,
  experience 15%, seniority 5%, work arrangement 5%.
- Re-normalize bobot hanya pada requirement yang terdeteksi.
- Partial credit untuk experience gap dan adjacent seniority harus eksplisit.
- Keluarkan overall score 0–100, verdict, category score, matched/missing list, evidence,
  dan disclaimer.

**Accept:** deterministic, unit-tested, tidak memakai protected attributes, tidak ada
hidden factor, dan gagal dengan jelas bila job requirement tidak dapat diekstrak.

### FR-04 — Skill-gap and learning priorities (P0)

- Technical skill/tool gap memiliki prioritas awal `high`; soft skill `medium`.
- Rekomendasi menjelaskan hubungan langsung dengan lowongan.
- Jangan menyatakan kandidat tidak memiliki skill; gunakan “belum terdeteksi di CV”.
- Course/provider recommendation hanya boleh berasal dari curated catalog dengan URL,
  provider, language, level, dan freshness metadata.

**Accept:** tidak ada invented course; setiap priority traceable ke requirement.

### FR-05 — Market insight (P1)

- Tampilkan top skills/tools berdasarkan role, location, dan observation period.
- Setiap chart menampilkan denominator, sample size, source, dan filter aktif.
- Perbandingan Indonesia/global hanya untuk data dengan definisi dan periode sebanding.

**Accept:** metric definitions konsisten, no double-counted jobs, dan dashboard numbers
reconcile dengan processed dataset.

### FR-06 — Salary estimate (P2, blocked)

- Gunakan range/quantiles, bukan false-precision point estimate.
- Tampilkan currency, period, sample size, interval, missingness, serta feature limits.
- Sistem menolak memberi estimate bila input keluar dari training support.

**Accept:** data gate dan ML-QG-4 terpenuhi. Sampai saat itu UI hanya menunjukkan
“insufficient data”; fitur tidak dipasarkan sebagai capability aktif.

### FR-07 — API (P0 setelah model contract stabil)

Minimum endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | liveness/readiness dan version |
| GET | `/metadata` | taxonomy/model/data version dan limitations |
| POST | `/v1/extract` | structured entity extraction |
| POST | `/v1/match` | explainable CV–job match |

**Accept:** Pydantic schemas, request limits, safe error handling, OpenAPI examples,
contract tests, no text logging by default.

### FR-08 — UI demo (P0)

Minimum screens:

1. Landing/product explanation.
2. CV and job input with sample-data button.
3. Results: score, category contributions, matched/gap chips, learning priorities.
4. Methodology/data/model limitations.
5. Market dashboard after FR-05 is ready.

**Accept:** recruiter can complete sample journey in <3 minutes; mobile-readable;
loading/error/empty states present; no sign-in needed for demo.

## 9. Data requirements and governance

### Current dataset

- Kaggle: `raflirizkya/indonesian-data-and-analytics-jobs-in-jobstreet`, version 1.
- Creator: Rafli Rizkya Sakti Nugraha; license: CC-BY-4.0 with attribution required.
- 555 Indonesian data/analytics vacancies; 542 unique job-description texts.
- Observation window: 25 August–24 September 2025; one JobStreet snapshot, not a time series.
- Salary disclosed in 77 rows (13.9%).
- Local file exactly matches Kaggle v1 by byte size and SHA-256; manifest is
  `data/provenance/sources.yaml`.
- Raw CSV, annotation working CSVs, and review HTML are excluded from public Git by default;
  reproduction downloads from Kaggle and verifies the pinned identity because third-party
  posting rights/terms may still apply. Public evidence is aggregate or redacted.

### Target dataset

- 2,000–5,000 job descriptions for descriptive market analysis.
- 800–1,500 documents annotated over project lifetime if resources allow.
- First reliable portfolio gate: >=100 fully reviewed documents.
- Agreement subset: 100–200 samples with at least two independent annotators.

### Annotation rules

- Annotation unit: complete job description.
- Explicit text only; no skill inferred from title/industry.
- Canonical labels come from versioned taxonomy.
- Minimum experience means the minimum explicitly stated.
- `unknown` for unmentioned scalar categories; empty set for no set-valued entity.
- Ambiguities recorded in notes and used to revise guidelines.
- Train/dev/test split is document-level and frozen before supervised model tuning.

### Provenance record required per source

- source name and URL/reference;
- acquisition method and permission/license;
- collection date/observation window;
- geography/language;
- transformations and deduplication;
- publication/redistribution constraints.

## 10. AI/ML strategy

### Baseline-first ladder

1. Dictionary/pattern extraction baseline.
2. Error-driven taxonomy and pattern improvement.
3. Multilingual sentence embedding for semantic skill alignment.
4. IndoBERT/multilingual transformer NER only if enough labels exist.
5. Multi-label classifier, clustering, and recommendation models after core evaluation.

Setiap challenger harus dibandingkan dengan incumbent pada split gold yang sama. Model
baru tidak menggantikan baseline bila gain kecil, latency/cost jauh lebih buruk, atau
explainability turun tanpa manfaat pengguna.

### Quality gates

**ML-QG-1 — Extraction portfolio baseline**

- >=100 human-reviewed documents.
- Technical skill + tool micro F1 target >=0.80.
- Recall target >=0.80 karena missed requirement merusak gap analysis.
- Laporkan per-category precision/recall/F1 dan exact match; jangan aggregate saja.
- Tidak ada known systematic false positive berisiko tinggi yang tidak didokumentasikan.

**ML-QG-2 — Annotation reliability**

- >=2 annotators pada 100–200 samples.
- Cohen’s Kappa untuk label categorical sederhana atau Krippendorff’s Alpha untuk setup
  yang mendukung missing/multiple annotators.
- Target agreement >=0.75; bila lebih rendah, revisi guidelines dan adjudicate.

**ML-QG-3 — Matching challenger**

- >=50 CV–job pairs yang dinilai manusia dengan rubric yang sama.
- Bandingkan category-level error, ranking/relevance agreement, latency, dan explanation.
- Target awal: Spearman correlation >=0.60 dengan human relevance dan improvement yang
  terukur terhadap exact taxonomy baseline.

**ML-QG-4 — Salary research gate**

- Minimum 300 clean, comparable disclosed salary observations setelah filtering.
- Currency/period normalization tervalidasi; role/location/seniority coverage memadai.
- Evaluasi temporal holdout, MAE baseline, pinball loss, interval coverage, dan subgroup
  error. Bila gate gagal, fitur tetap experimental/off.

## 11. System architecture target

```text
Allowed data sources / user input
              ↓
Validation → normalization → deduplication → versioned processed data
              ↓
Taxonomy + extraction service → structured requirements + evidence spans
              ↓
Explainable matcher → skill gap → learning priority rules
              ↓
FastAPI domain layer → Next.js/Streamlit demo + optional analytics consumers
              ↓
Metrics, data/model cards, CI, container, versioned reports
```

Target technology:

- Python, Pandas/Polars, scikit-learn/PyTorch, Hugging Face/Sentence Transformers.
- FastAPI and Pydantic.
- PostgreSQL only when persistent market data/API requires it.
- Next.js for polished portfolio UI; Streamlit acceptable for a faster internal demo.
- Docker and GitHub Actions.
- DVC when processed datasets/model artifacts exceed normal Git workflow.
- MLflow when experiments/models lebih dari satu baseline dan tracking memberi nilai.

Tooling tidak ditambahkan hanya untuk checklist. Setiap tool harus mempunyai artifact,
workflow, atau decision yang nyata.

## 12. Non-functional requirements

### Privacy and security

- No CV persistence or request-body logging by default.
- Redact/avoid PII in reports, tests, screenshots, and telemetry.
- Explicit consent before any saved analysis.
- File size/type limits, safe parsing, dependency scanning, and secrets outside Git.

### Reliability and performance

- Deterministic baseline output for the same versions/input.
- Health/readiness endpoints and structured non-sensitive logs.
- Initial API target: p95 <500 ms for rule extraction/matching on typical plain text on
  local CPU; semantic model target set after profiling.
- Graceful failure when taxonomy/model/data artifacts are missing.

### Reproducibility

- Pinned compatible dependency ranges and Python version.
- Tests and lint on each push/PR.
- Version in metadata for taxonomy, model, code release, and dataset/report.
- Every public metric maps to a reproducible command and artifact.

### Accessibility and language

- UI copy supports Indonesian first with clear English-ready structure.
- Do not communicate score using color alone.
- Plain-language explanation for statistical/model limitations.

## 13. Product and portfolio success metrics

### Product-quality metrics

- Gold extraction precision/recall/F1 and document coverage.
- Human agreement score and adjudication rate.
- Match explanation completeness rate.
- Example-journey completion and error rate.
- API latency/failure rate after deployment.

### Portfolio evidence

- One public-safe reproducible dataset sample or documented acquisition procedure.
- Data card, model card, annotation guide, PRD, architecture, and evaluation report.
- CI badge with lint/tests passing.
- Live demo or reproducible local Docker demo.
- 2–4 minute demo video/GIF and screenshots.
- README answer-first: problem, architecture, metrics, limitations, setup, demo.
- Case-study narrative: research → baseline → error evidence → product decision.

Vanity metrics seperti jumlah model, library, atau baris kode bukan success metric.

## 14. Roadmap and exit gates

### Phase 0 — Foundation (done)

- Package layout, data pipeline, CI, test, data-quality report.
- Exit: reproducible clean data and passing CI.

### Phase 1 — Extraction evidence (exited via remediation; human gate open)

- Primary gold is frozen at 100 project-owner-confirmed rows with complete notes and audit
  coverage. ML-QG-1 is met as an AI-assisted development baseline, not an independent
  generalization estimate; publish `reports/extraction_gold_validation.md` with the metrics.
- The blind second-annotator file remains unfilled and leakage-free. A different human is still
  required to close ML-QG-2.
- The supplied external XLSX is repaired only as an `ai_reviewed` challenger. Unsupported labels,
  source restoration, and descriptive AI-versus-primary metrics are audited; it is not second-
  human agreement.
- `reports/ml_quality_gate_remediation.md` explicitly permits engineering continuation while
  forbidding an ML-QG-2 pass claim.
- Exit status: remediation route complete; independent reliability evidence remains a human gate.
### Phase 2 — Matching validation (experimental comparison complete; human gate open)

- Matcher v0.1 contract remains frozen and explainable.
- Fifty synthetic, public-safe CV–job pairs across 10 job groups remain unchanged with zero human
  relevance labels. Separate synthetic-oracle labels support regression only.
- Exact-taxonomy baseline diagnostic: Spearman 0.9345, MAE 8.29/100, explanation completeness 1.00.
- A 20% `paraphrase-multilingual-MiniLM-L12-v2` hybrid was compared on the same synthetic labels
  and not promoted because rank agreement fell slightly, MAE increased to 9.92, and latency rose.
- Exit status: stable JSON contract achieved; ML-QG-3 remains open until an independent human
  freezes 50 scores/rationales and both models are rerun without evaluation-set tuning.
### Phase 3 — Product service (done locally)

- Domain contract v1 uses strict, versioned Pydantic request/response schemas and a 50,000-character
  input limit.
- FastAPI exposes `/health`, `/v1/models`, `/v1/extract`, and `/v1/match`; contract and error-path
  tests pass without request-body persistence.
- The non-root API image excludes raw data, annotations, reports, notebooks, CSV, and XLSX files;
  local health/extract/match smoke passed.
- Exit: complete for local product-service scope; public deployment verification belongs to Phase 5.
### Phase 4 — Portfolio experience (functional local demo; visual gate open)

- API-backed Streamlit demo includes bilingual example mode, match score, matched/missing evidence,
  deterministic learning priorities, extraction, methodology, privacy, and open-gate disclosures.
- The one-command PowerShell launcher starts API/UI together; smoke mode verified both health
  endpoints and cleaned both processes without leaving listeners.
- Market dashboard remains gated until aggregate trend metrics reconcile.
- Exit remains open: browser-responsive/loading/error/empty-state visual QA and valid demo media are
  pending because local headless Edge/Chrome rendered crash pages; invalid screenshots were removed.
### Phase 5 — Release and storytelling (public source complete; deployment/media gates open)

- Model card, architecture diagram, demo checklist, answer-first README, recruiter case study, release
  checklist/audit, and source-backed portfolio report JSON are complete and reconciled with evidence.
- Public `origin/main` has a parentless 97-file product history, green CI, a staged/commit publication
  guard, executable pre-push hook, deny-by-default data/private-file policy, read-only CI permissions,
  SECURITY/PRIVACY policies, Dependabot, and official checkout v7.
- Historical research is local-only and absent from public history. The portable report passed package-
  contract validation but shared browser verification still reports desktop overflow; no unverified HTML
  is delivered.
- API container evidence is complete locally. Responsive demo media, public application hosting,
  monitoring, rollback, and independent human evidence remain open.
- Exit: all Portfolio-ready Definition below is satisfied.
### Phase 6 — Optional research expansion

- Larger/global dataset, trends, classification/clustering, salary only after gates.

## 15. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Sparse salary disclosure | Misleading prediction | Keep feature blocked until ML-QG-4 |
| Weak labels mistaken for truth | Inflated metrics | Human gold set and explicit report naming |
| Java/R/short alias ambiguity | False positives/negatives | Gold error analysis, contextual patterns |
| Dataset limited to one source/time | Poor generalization | Provenance, scope label, new allowed sources |
| CV contains sensitive data | Privacy harm | No persistence/logging; public-safe examples |
| Score interpreted as hiring decision | Fairness harm | Explainability, disclaimer, no auto-rejection |
| Feature/tool checklist bloat | Unfinished product | Phase gates and one vertical slice at a time |
| Annotation inconsistency | Invalid evaluation | Guidelines, second annotator, agreement/adjudication |

## 16. Current decisions and open questions

### Decided

- Rule/taxonomy baseline remains incumbent; the 20% multilingual semantic challenger was evaluated
  on synthetic diagnostics and not promoted because error and latency worsened.
- Automated AI/synthetic artifacts never satisfy human quality gates; remediation allows engineering
  continuation only with explicit non-human claim labels.
- Domain contract v1 is frozen for extraction/matching transport; breaking changes require a version bump.
- FastAPI is the service boundary and Streamlit is the v1 portfolio UI; presentation logic does not
  import or duplicate scoring logic.
- Public source repository is `Rajapranata512/skillpulse-ai` on clean `main`; automatic pushes require
  staged/commit guard, passing tests, explicit product paths, no force, and no research-history refs.
- Current salary data is insufficient for an active feature.
- Matching score is requirement coverage, not candidate worth.
- UI/API follow extraction evaluation and domain-contract stabilization.
- `RM.ipynb` remains preserved as research history.
- Extraction ML-QG-1 is met as a 100-row AI-assisted, human-confirmed development baseline;
  the validation caveat must accompany every public metric.
- Annotation reliability remains open until a different human completes the 100-row blind
  batch and field-level agreement is reported; AI challenger metrics are descriptive only.
- Matching relevance rubric v0.1 and 50 synthetic pairs are frozen as the human-review contract;
  pseudo-label and semantic results are diagnostics, not ML-QG-3 evidence.
- Kaggle v1 provenance and CC-BY-4.0 attribution are verified; raw descriptions remain Git-ignored and reproducible by pinned download/hash.

### Open, to resolve with evidence

- Which API/UI hosting targets meet privacy, monitoring, rollback, region, and cost constraints.

- Which job families beyond data/analytics enter taxonomy v0.2?
- Which licensed global source is comparable to the verified 30-day Indonesian snapshot?
- Whether a later Next.js rewrite adds enough value after Streamlit usability and reviewer feedback?
- Which curated learning catalog can be legally and reliably referenced?
- Whether relevance rubric v0.1 produces stable human judgments and useful per-job rankings?

## 17. Portfolio-ready Definition of Done

SkillPulse AI boleh disebut portfolio-ready hanya jika semuanya terpenuhi:

- P0 requirements selesai dan demonstrated end-to-end.
- Gold extraction evaluation memakai >=100 reviewed documents dengan honest metrics.
- Annotation agreement atau keterbatasannya dilaporkan.
- Matching mempunyai public-safe evaluation dataset dan explainable output.
- CI lint/tests hijau; Docker/local setup reproducible.
- Demo UI/API berjalan dan mempunyai sample mode tanpa data pribadi.
- Data provenance, redistribution decision, privacy, bias, dan limitations terdokumentasi.
- README berisi problem, solution, architecture, dataset, evaluation, demo, dan setup.
- Model card/data card/evaluation report sinkron dengan versi release.
- Tidak ada secret, PII, copyrighted raw data tanpa izin, atau unsupported performance
  claim dalam repository/public demo.
- Demo media dan satu case-study narrative siap ditunjukkan saat melamar.

Jika satu gate belum terpenuhi, sebut proyek sebagai **working portfolio project** dan
tampilkan roadmap/evidence yang jujur.

