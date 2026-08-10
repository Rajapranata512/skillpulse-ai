# SkillPulse AI — Agent Operating Manual

Dokumen ini adalah memori operasional utama untuk semua coding agent yang bekerja di
repository ini. Baca seluruh file ini sebelum melakukan perubahan. Baca `PRD.md` hanya
untuk bagian yang dirujuk oleh tugas aktif, lalu perbarui bagian **Project State** di
akhir pekerjaan bila status milestone benar-benar berubah.

Tujuan dokumen ini: mencegah pekerjaan berulang, menjaga keputusan tetap konsisten,
dan membuat agent dapat melanjutkan milestone berikutnya dengan aman tanpa meminta
pengguna mengulang konteks.

## 1. Source of truth dan urutan otoritas

1. Instruksi terbaru pengguna.
2. `AGENTS.md` untuk cara bekerja dan status proyek.
3. `PRD.md` untuk arah produk, scope, quality gates, dan acceptance criteria.
4. Kode, test, konfigurasi, dan laporan yang benar-benar ada di repository.
5. Notebook riset lama hanya sebagai sumber historis, bukan arsitektur aplikasi.

Jika dokumen bertentangan dengan implementasi teruji, catat selisihnya dan perbarui
dokumen pada pekerjaan yang sama. Jangan menyatakan fitur selesai hanya dari dokumen.

## 2. Startup protocol — wajib, satu kali per sesi

1. Baca `AGENTS.md` secara lengkap satu kali pada awal sesi. Fokus pertama pada
   **Session Handoff Snapshot**, **Project State**, **Do Not Repeat**, dan **Next Task
   Selection**.
2. Jalankan `git status --short`; lindungi semua perubahan yang bukan milik agent.
3. Baca blok **Auto-Sync Delivery Snapshot** di `PRD.md`, lalu hanya bagian requirement,
   quality gate, atau roadmap yang dirujuk oleh task aktif. Jangan membaca ulang seluruh
   PRD, dataset, report, atau notebook tanpa dependency yang berubah.
4. Cocokkan `Selected next task` pada PRD dengan `Active next task` pada AGENTS. Jika
   berbeda, gunakan evidence repository untuk memperbaiki keduanya sebelum implementasi.
5. Periksa artefak/evidence yang tercatat. Jangan membangun ulang komponen `DONE` kecuali
   input, kontrak, dependency, atau acceptance criteria berubah.
6. Pilih satu vertical slice terkecil yang menggerakkan milestone aktif sampai kondisi
   selesai yang dapat diuji.

Jika pengguna hanya berkata “lanjutkan”, “continue”, atau “kerjakan berikutnya”, langsung
ambil **Auto-selected next task** pada Session Handoff Snapshot. Jika task itu terblokir,
ambil rekomendasi berikutnya yang tidak terblokir. Tidak perlu meminta konfirmasi untuk
perubahan lokal, reversible, dan sesuai PRD.

### Context/token budget rules

- Jangan meminta pengguna mengulang konteks yang sudah ada di AGENTS/PRD/evidence.
- Jangan membaca ulang file besar yang sudah dibaca dalam sesi yang sama kecuali berubah.
- Gunakan pencarian terarah (`rg`, nama simbol, atau heading) sebelum membaca file penuh.
- Periksa hanya dependency chain task aktif; jangan melakukan audit repository penuh pada
  setiap sesi.
- Jalankan targeted test selama implementasi dan full suite sekali pada handoff bila scope
  perubahan memerlukannya.
- Jangan meregenerasi report/data yang input dan implementasinya tidak berubah.
- Session Handoff Snapshot harus ditimpa, bukan ditambah terus, agar context tetap kecil.
## 3. End-of-work protocol — wajib dan otomatis

Sebelum menyerahkan hasil, agent wajib melakukan urutan ini tanpa menunggu perintah baru:

1. Verifikasi perubahan secara proporsional; untuk kode Python lintas modul jalankan
   `ruff check src tests` dan `pytest -q`.
2. Simpan evidence bermakna di `reports/` hanya jika ada metric/keputusan baru. Jangan
   membuat laporan yang menduplikasi evidence lama.
3. Perbarui **Project State** bila status, metric, test count, blocker, atau dependency
   milestone benar-benar berubah.
4. Timpa **Session Handoff Snapshot** dengan outcome terakhir dan maksimal tiga saran
   berikutnya. Setiap saran wajib memiliki ID milestone, alasan nilai, dependency, dan
   completion check. Tandai tepat satu sebagai **Auto-selected next task**.
5. Sinkronkan `PRD.md` secara otomatis:
   - selalu timpa blok **Auto-Sync Delivery Snapshot** untuk setiap sesi yang mengubah repo;
   - perbarui requirement, quality gate, roadmap, risk, atau keputusan lain hanya bila
     implementasi/evidence mengubah fakta produk;
   - jangan menyalin log terminal atau detail implementasi yang sudah ada di AGENTS;
   - pastikan selected-next ID, status, metric, dan blocker sama di kedua dokumen.
6. Perbarui tanggal hanya bila dokumen memang disinkronkan dan evidence diverifikasi.
7. Beri final handoff singkat: outcome, evidence, limitation, dan saran berikutnya.
8. Repository ini memiliki standing owner authorization untuk commit dan push perubahan produk
   yang selesai ke `https://github.com/Rajapranata512/skillpulse-ai.git`, mengikuti gate
   **Automatic GitHub publication** di bawah. PR, deployment, visibility change, dan upload data
   tetap memerlukan otorisasi eksplisit terpisah.

### Automatic GitHub publication — owner-authorized

Pemilik telah memberi standing authorization agar perubahan produk yang selesai otomatis di-commit
lalu di-push ke branch `main` pada `https://github.com/Rajapranata512/skillpulse-ai.git` tanpa
meminta perintah repetitif. Otorisasi ini hanya berlaku untuk file produk yang aman dan relevan.

Wajib sebelum setiap push:

1. Jalankan `git status --short` dan review exact staged paths/diff. Jangan gunakan `git add -A`
   pada worktree campuran; stage file produk secara eksplisit.
2. Jangan stage/publish `RM.ipynb`, PDF akademik, local branch `research-history-local-20260810`, raw/processed row-level
   data, human annotations, AI workbooks/labels, review HTML, `.env`, credentials, private keys,
   database lokal, PII, atau file agent/tool state.
3. Jalankan verification tier task aktif; untuk perubahan lintas repo wajib `ruff check src tests`
   dan `pytest -q`.
4. Jalankan `python scripts/publication_guard.py --staged`; commit hanya jika PASS. Setelah commit,
   jalankan `python scripts/publication_guard.py --commit HEAD`, lalu push non-force ke `origin main`.
5. Pastikan Git hook memakai `core.hooksPath=.githooks`. Jangan bypass hook dengan `--no-verify`.
6. Catat SHA commit, hasil guard/test, dan remote branch di Session Handoff Snapshot dan PRD sync.

Stop tanpa commit/push jika guard/test gagal, staged scope ambigu, ada perubahan user-owned yang tidak
terkait, remote berbeda, atau keamanan/privasi tidak dapat dibuktikan. Jangan force-push, rewrite
history, mengubah remote/visibility, membuka PR, membuat release, atau deploy tanpa instruksi baru.
History penelitian hanya disimpan pada local branch `research-history-local-20260810` dan remote
`research-origin`; jangan pernah push branch/remote itu, `--all`, `--mirror`, atau tags ke origin publik.
### Mandatory recommendation format

Gunakan format ringkas berikut di Session Handoff Snapshot dan final response:

```text
1. [NEXT][Milestone ID] <aksi> — nilai: <mengapa sekarang>;
   selesai jika: <bukti/acceptance check>.
2. [LATER][Milestone ID] <aksi> — dependency: <apa yang harus selesai dahulu>.
3. [HUMAN-GATE/BLOCKED][Milestone ID] <aksi manusia/keputusan>, bila ada.
```

Jika semua milestone portfolio selesai, rekomendasi berikutnya adalah release verification,
monitoring, dan maintenance; jangan menciptakan fitur baru tanpa kebutuhan PRD.
## 4. Do Not Repeat

Jangan ulangi pekerjaan berikut selama trigger pada kolom terakhir tidak terjadi:

| Area | Artefak/evidence yang sudah ada | Status | Ulangi hanya jika |
|---|---|---:|---|
| Data preparation | `src/skillpulse/data/pipeline.py`, `reports/data_quality.json` | DONE | raw data/schema/pipeline berubah |
| Dataset provenance | `data/provenance/sources.yaml`, `src/skillpulse/data/provenance.py` | VERIFIED v1 | source version/license/local hash berubah |
| Data-quality EDA | `notebooks/01_data_quality_eda.ipynb`, `reports/data_card.md` | DONE | dataset atau pertanyaan analisis berubah |
| Bilingual taxonomy | `configs/skill_taxonomy.yaml`, `configs/soft_skills.yaml` | DONE v0.2 | human-gold error analysis membuktikan alias/entitas kurang |
| Extraction baseline | `src/skillpulse/extraction/` | DONE v0.2 | taxonomy/requirements berubah atau model baru dibandingkan |
| Weak-label evaluation | `reports/extraction_baseline.json` | DONE | dataset/taxonomy/extractor berubah |
| Gold sample scaffold | data/annotations/gold_sample.csv | DONE | perlu menambah sampel, bukan membuat ulang |
| AI-assisted review batch 001 | `reports/extraction_ai_assisted_eval.json` | DONE | regenerate only after labels/extractor change |
| Scalar extraction hardening | `tests/test_extraction_regressions.py` | DONE | relevant rules or annotation decisions change |
| Contextual extraction hardening | `tests/test_contextual_extraction.py` | DONE v0.2 | human-gold errors or taxonomy change |
| Human review pack batch 001 | `reports/annotation_review_pack.html`, `data/annotations/review_log.csv` | DONE-HUMAN | batch-001 decisions change |
| Remaining review pack | `reports/annotation_review_pack_remaining.html` | DONE-HUMAN | primary decisions change |
| Safe review batch workflow | `src/skillpulse/extraction/review_batch.py`, `data/annotations/review_batch_remaining.csv` | DONE-HUMAN | annotation schema or primary decisions change |
| Primary 100-row gold evaluation | `reports/extraction_gold_eval.json`, `reports/extraction_gold_validation.md` | DONE-DEV-BASELINE | gold labels, taxonomy, or extractor change |
| Blind agreement workflow | `src/skillpulse/extraction/agreement.py`, `data/annotations/second_annotator_blind.csv` | READY-HUMAN-GATE | primary source set or agreement schema changes |
| Matching relevance scaffold | `src/skillpulse/matching/relevance.py`, `data/evaluation/matching_relevance_candidates.csv`, `docs/matching_relevance_rubric.md` | READY-HUMAN-GATE | rubric, pair schema, or matcher contract changes |
| Portable provenance HTML | `reports/data_provenance_artifact.json`, `data_provenance_report_qa.md` | BLOCKED-RENDERER | shared portable renderer changes |
| Portfolio release documentation | `docs/model_card.md`, `docs/architecture.md`, `docs/demo_checklist.md`, `scripts/run_demo.ps1` | DONE-LOCAL | domain contract, metrics, privacy, or demo command changes |
| Portfolio case study and release audit | `docs/case_study.md`, `docs/release_checklist.md`, `reports/release_readiness.json` | DONE-LOCAL | evidence, Git publication state, or deployment decision changes |
| Portable portfolio report | `reports/portfolio_report_artifact.json`, `reports/portfolio_report_qa.md` | BLOCKED-RENDERER | shared portable renderer changes |
| AI workbook challenger repair | `src/skillpulse/extraction/ai_challenger.py`, `reports/ai_challenger_*.json` | DONE-AI-DIAGNOSTIC | source workbook, taxonomy, or primary labels change |
| Synthetic relevance diagnostic | `data/evaluation/matching_relevance_ai_labels.csv`, `reports/matching_relevance_ai_baseline.json` | DONE-NON-HUMAN | candidate generator, rubric design, or matcher changes |
| Multilingual semantic challenger | `src/skillpulse/matching/semantic.py`, `reports/matching_semantic_challenger.json` | EVALUATED-NOT-PROMOTED | frozen human relevance labels become available |
| ML gate remediation | `reports/ml_quality_gate_remediation.md` | DONE | human labels close a gate or public claim scope changes |
| Domain contract v1 | `src/skillpulse/domain/`, `docs/api_contract_v1.json` | FROZEN v1 | breaking API requirement is approved |
| FastAPI service | `src/skillpulse/api/`, `tests/test_api.py` | DONE-LOCAL | contract or endpoint requirement changes |
| API container | `Dockerfile`, `.dockerignore`, `reports/api_container_smoke.json` | DONE-LOCAL | dependencies, service command, or deployment target changes |
| Streamlit demo slice | `src/skillpulse/ui/`, `reports/ui_smoke.json` | DONE-SMOKE | contract, journey, or visual QA finding changes |
| Annotation rules | `docs/annotation_guidelines.md` | DONE v0.2 | ambiguity berulang ditemukan |
| Explainable matcher | `src/skillpulse/matching/` | DONE v0.1 | gold labels atau matching requirements berubah |
| Match demo | `reports/cv_job_match_example.json` | DONE | matcher/demo scenario berubah |
| CI foundation | `.github/workflows/ci.yml`, `pyproject.toml` | DONE | dependency/commands/platform berubah |
| Publication privacy/security guard | `scripts/publication_guard.py`, `.githooks/pre-push`, `tests/test_publication_guard.py`, `SECURITY.md`, `PRIVACY.md` | DONE v1 | public-scope policy, secret/PII patterns, or Git layout changes |
| Clean public Git history | public `origin/main`, root `c9e2854`, local `research-history-local-20260810` | VERIFIED | owner changes repository/visibility or public-history policy |
| Original research notebook | `RM.ipynb` | USER-OWNED | pengguna secara eksplisit meminta perubahan |

Aturan tambahan:

- Jangan membuat taxonomy kedua, pipeline kedua, atau CLI paralel untuk fungsi yang sama.
- Extend modul yang ada dan pertahankan backward compatibility bila masuk akal.
- Jangan menganggap `weak_tools`, `pengalaman`, atau `level` sebagai gold labels.
- Jangan menjalankan salary modelling sebelum data gate di PRD terpenuhi.
- Jangan melakukan scraping agresif atau bypass ketentuan LinkedIn/JobStreet.
- Jangan menyimpan CV mentah secara default atau memasukkan atribut terlindungi ke skor.
- Jangan mengubah `RM.ipynb` hanya untuk merapikan atau menyelaraskan kode aplikasi.
- Jangan membuat FastAPI/UI sebelum kontrak domain dan gold evaluation baseline stabil.

## 5. Next Task Selection

Gunakan algoritme ini:

1. Selesaikan `NEXT` pada Project State.
2. Jika selesai, pilih requirement P0 dengan quality gate yang belum terpenuhi.
3. Jika seluruh P0 terpenuhi, kerjakan P1 berdasarkan urutan roadmap PRD.
4. Jangan mengambil P2 jika dependency atau data gate belum terpenuhi.
5. Jika tugas memerlukan keputusan produk yang belum ditetapkan dan akan mengubah scope,
   tandai `BLOCKED` serta minta keputusan pengguna. Kekurangan kecil boleh diselesaikan
   dengan asumsi konservatif dan dicatat.

Urutan default saat ini:

1. If a different human is available, complete all 100 blind annotations, run agreement, and
   adjudicate fields below 0.75; otherwise keep ML-QG-2 explicitly open.
2. If an independent relevance rater is available, freeze all 50 scores/rationales and rerun
   exact-taxonomy plus semantic evaluation without tuning; otherwise keep ML-QG-3 open.
3. Complete M6a portfolio release documentation, architecture evidence, and reproducible demo
   checklist using only verified reports.
4. Perform responsive visual QA and capture valid desktop/mobile demo media in an environment
   with a working browser renderer.
5. Add a market dashboard only after metric definitions and aggregate trend data reconcile.
6. Public release verification, monitoring, and maintenance; salary remains data-gated.
## 6. Engineering rules

### Repository boundaries

- Source: `src/skillpulse/`
- Test: `tests/`
- Configuration/taxonomy: `configs/`
- Human annotation: `data/annotations/`
- Generated/derived data: `data/processed/`
- Durable evidence: `reports/`
- Reproducible exploration: `notebooks/`
- Product/annotation docs: root and `docs/`

Raw data tidak boleh ditimpa. Generated output harus deterministik sejauh mungkin.

### Implementation

- Python >= 3.11, type hints, small modules, explicit errors, deterministic output.
- Gunakan canonical labels dari taxonomy; jangan hard-code daftar skill di banyak modul.
- Pisahkan extraction, matching, evaluation, transport/API, dan presentation/UI.
- Semua skor harus expose komponen, bobot, matched/missing evidence, dan disclaimer.
- Tambahkan unit test untuk happy path, edge case, dan failure path.
- Tidak boleh ada dependency baru tanpa alasan langsung terhadap milestone aktif.
- Jangan mengejar model kompleks sebelum baseline dan gold metric tersedia.

### Verification tiers

- Dokumen saja: link/path check dan consistency review.
- Taxonomy/annotation: schema validation + evaluation command.
- Satu modul Python: targeted test + Ruff untuk file terkait.
- Perubahan lintas modul/release: `ruff check src tests` dan `pytest -q`.
- Data/model berubah: regenerate hanya laporan yang dependensinya berubah.

Canonical commands:

```powershell
python -m pip install -e ".[dev]"
ruff check src tests
pytest -q
python scripts/publication_guard.py --staged
python scripts/publication_guard.py --commit HEAD
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -SmokeTest
skillpulse-prepare
skillpulse-extract gold --annotations data/annotations/gold_sample.csv
skillpulse-extract provisional --annotations data/annotations/gold_sample.csv
skillpulse-extract review-batch --annotations data/annotations/gold_sample.csv --status needs_review
skillpulse-extract review-import --annotations data/annotations/gold_sample.csv --batch data/annotations/review_batch_remaining.csv --output data/annotations/gold_sample.csv --confirm-human-review
skillpulse-extract agreement-batch --primary data/annotations/gold_sample.csv --output data/annotations/second_annotator_blind.csv
skillpulse-extract agreement --primary data/annotations/gold_sample.csv --secondary data/annotations/second_annotator_blind.csv --output reports/annotation_agreement.json
skillpulse-relevance create
skillpulse-relevance evaluate
skillpulse-match --cv-text "..." --job-text "..."
```

## 7. Data and ML governance

- Unit gold annotation adalah satu job description lengkap.
- Label hanya informasi eksplisit; title boleh digunakan hanya untuk `seniority` jika
  secara eksplisit mengandung junior/senior/lead, bukan untuk menginfer skill.
- Blank berarti tidak ada entity untuk set-valued labels; `unknown` dipakai untuk
  seniority/work arrangement yang tidak disebutkan.
- Setiap reviewed row harus berisi `annotator`, `review_status=reviewed`, dan `notes`
  untuk ambiguity atau known taxonomy limitation.
- Perubahan taxonomy setelah gold review harus diikuti rerun gold evaluation dan test.
- Laporkan precision, recall, F1, jumlah dokumen, dan cakupan per label. Jangan hanya
  menampilkan aggregate score.
- Salary prediction tetap experimental sampai data gate PRD terpenuhi.
- Sistem adalah decision support, bukan automatic hiring/ranking authority.

## 8. Definition of Done

Sebuah task hanya `DONE` jika:

- acceptance criteria terkait di PRD terpenuhi;
- implementasi/dokumen benar-benar ada;
- test/evidence yang proporsional lulus;
- limitation dan data provenance tidak disembunyikan;
- Project State diperbarui jika milestone berubah;
- Session Handoff Snapshot berisi 1–3 saran dan tepat satu auto-selected next task;
- PRD Auto-Sync Delivery Snapshot telah disinkronkan tanpa menunggu perintah pengguna;
- tidak ada pekerjaan pengguna yang tertimpa.

“Portfolio-ready” memiliki definisi khusus di PRD dan tidak boleh diklaim hanya karena
demo dapat dijalankan secara lokal.

## 9. Session Handoff Snapshot — overwrite, jangan append

Blok di antara marker berikut adalah satu-satunya handoff aktif. Agent wajib menimpanya
setelah pekerjaan selesai; jangan menambah riwayat sesi di sini. Evidence historis tetap
berada di Git/reports.

<!-- HANDOFF:START -->
**Last handoff:** 2026-08-10
**Completed:** Published SkillPulse AI to the owner-approved public repository
`https://github.com/Rajapranata512/skillpulse-ai` with a clean parentless product history.
Preserved the former research history locally only, added deny-by-default Git ignore rules,
a staged/commit publication guard, six security tests, an executable pre-push hook, CI guard,
read-only CI permissions, GitHub noreply commit identity, SECURITY/PRIVACY policies, and
Dependabot. Verified and applied official `actions/checkout` and `actions/setup-python` v7 updates after green bot checks.
**Evidence:** Ruff passed and `pytest -q` reports 94 passed. The root public snapshot contains
97 allowlisted text files and no parent; publication guard scanned the complete 456,168-byte
HEAD successfully. `RM.ipynb`, academic PDFs, raw/processed row-level data, human annotations,
AI workbooks/labels, review HTML, stale internal reports, credentials, PII patterns, and local
paths are absent. Local/remote `origin/main` equality was verified after each guarded push. CI run
`31404286936` succeeded on `d705238` with checkout/setup-python v7; both official updates had
green Dependabot checks before the same one-line changes were applied locally.
**Limitations/blockers:** Public source publication is complete, but the application is not
publicly deployed and the project is still a working portfolio project. Responsive browser QA
and demo media remain an environment-human gate. ML-QG-2 remains 0/100 and ML-QG-3 remains
0/50; agents cannot create independent human evidence. Salary modelling remains blocked by
77/555 disclosed rows. The portable HTML renderer remains blocked by shared desktop overflow.

**Recommended next actions:**

1. **[NEXT][HUMAN/ENV-GATE][M5b] Complete responsive browser QA and capture public-safe demo media** — value:
   closes the most visible recruiter-facing gap now that source and CI are public; dependency: a working interactive
   browser; complete when desktop/mobile plus loading, error, empty, extraction, and matching states are reviewed
   and a 2-4 minute walkthrough contains only synthetic/redacted text.
2. **[LATER][HUMAN-GATE][M2b/M3b] Obtain independent annotation and relevance judgments** — dependency:
   different human annotators use the frozen blind files/rubric; complete when 100 blind annotations and 50
   relevance scores are frozen, then agreement and both matcher evaluations are rerun without evaluation-set tuning.
3. **[LATER][HUMAN-GATE][M6f] Select and authorize a public deployment target** — dependency: owner decisions
   for hosting region/cost, logging/retention, rate limits, monitoring, and rollback; complete when privacy controls,
   health/latency monitoring, deployment smoke, and rollback evidence pass without retaining submitted CV text.

**Auto-selected next task:** `M5b — responsive browser QA and public-safe demo media (HUMAN/ENV-GATE)`
**PRD sync:** synchronized with public clean-history publication, automatic privacy/security push gate,
green GitHub CI, checkout/setup-python v7, and remaining visual/human/deployment blockers.
<!-- HANDOFF:END -->
## 10. Project State

Last materially verified: **2026-08-10**

| ID | Milestone | Status | Evidence / notes |
|---|---|---:|---|
| M0 | Research preservation and repo foundation | DONE | `RM.ipynb` preserved; package layout and CI exist |
| M1 | Reproducible data pipeline, provenance, and quality report | DONE | Kaggle v1 CC-BY-4.0; exact SHA-256; 555 rows |
| M2a | Bilingual taxonomy and rule extraction baseline | DONE | taxonomy v0.2; weak-label micro F1 0.8273; not a gold claim |
| M2b | Human gold evaluation | PRIMARY-DONE / AUTOMATED-REMEDIATION / HUMAN-GATE | ML-QG-1 dev baseline met with caveat; AI challenger valid but non-human; ML-QG-2 remains 0/100 |
| M2c1 | Seniority/experience extraction hardening | DONE | 27 tests; exact 1.0000/0.9667; report batch 001 |
| M2c2 | Contextual technical/soft-skill hardening | DONE | taxonomy v0.2; technical F1 1.0000, soft F1 0.9928 provisional |
| M3a | Explainable CV–job matcher baseline | DONE | CLI + report + unit tests |
| M3b | Matching relevance dataset and semantic challenger | AI-EXPERIMENTAL / HUMAN-GATE | 50 pseudo-label diagnostics; semantic challenger evaluated and not promoted; ML-QG-3 remains 0/50 human |
| M4 | FastAPI/domain service | DONE-LOCAL | contract v1; 4 endpoints; OpenAPI tests; healthy non-root container smoke |
| M5 | Portfolio UI and market dashboard | DEMO-LOCAL / VISUAL-QA-ENV-GATE | API-backed Streamlit journey and self-cleaning launcher smoke passed; browser QA/media pending; market metrics gated |
| M6 | Containerized public portfolio release | PUBLIC-SOURCE / APP-DEPLOYMENT-VISUAL-HUMAN-GATES | clean public repo, guard, CI, docs, story, and API container evidence complete; public app/media/human gates remain |
| M7 | Salary prediction | BLOCKED-DATA | only 77/555 salary rows (13.9%); below PRD gate |

Current verified engineering evidence:

- `ruff check src tests`: passed.
- `pytest -q`: 94 passed.
- Kaggle source: version 1, creator Rafli Rizkya Sakti Nugraha, CC-BY-4.0,
  observation window 2025-08-25 through 2025-09-24.
- Local raw identity: 1,059,991 bytes and SHA-256
  `a857603f6d8a2b0344f4a4f00747e037ecc4ca3aa6b760800560ad4fe906887c`; exact fresh-download match.
- Primary annotation quality: valid; 100 unique reviewed rows; notes and audit coverage 100/100.
- ML-QG-1 baseline: technical/tools/education F1 1.0000, soft-skill F1 0.9969,
  experience/work-arrangement exact 1.0000, seniority exact 0.9900; share only with the
  AI-assisted development-set caveat in `reports/extraction_gold_validation.md`.
- External XLSX repair: 100/100 source texts restored and hashes aligned; canonical output valid
  and `ai_reviewed`. Dropped unsupported labels are audited. AI comparison is not independent:
  technical macro Kappa 0.8003, tools 0.9309, soft skills 0.6634, education 0.7173,
  experience 0.8164, seniority 0.3790, and arrangement 0.8683; not an ML-QG-2 claim.
- ML-QG-2: blind kit remains 0/100 independently reviewed; remediation is documented, not pass.
- Synthetic relevance baseline on 50/50 pairs: Spearman 0.9345, MAE 8.29, verdict accuracy 0.80,
  explanation completeness 1.00. Human relevance remains 0/50, so ML-QG-3 is not met.
- 20% multilingual MiniLM hybrid was not promoted: Spearman 0.9320, MAE 9.92, p50 about 83 ms
  versus about 6 ms baseline; evidence is synthetic diagnostic only.
- Domain contract v1 is frozen in `docs/api_contract_v1.json`; strict request/response tests pass.
- FastAPI endpoints `/health`, `/v1/models`, `/v1/extract`, and `/v1/match` pass contract tests.
- Docker image `skillpulse-api:local` built from a 410,160-byte privacy-filtered context, became
  healthy, ran as UID 100, and passed health/extract/match smoke.
- Streamlit/API local health returned HTTP 200; example mode and error-aware API client exist.
  Headless browser screenshots crashed and were removed, so responsive visual QA remains open.
- One-command demo smoke started API/UI on ports 18080/18501, verified both health endpoints,
  stopped both processes, and left no listeners.
- Portfolio evidence is reconciled in `docs/model_card.md`, `docs/architecture.md`,
  `docs/case_study.md`, and `reports/portfolio_release_metrics.json`; JSON/link QA passed.
- Portable portfolio artifact passed package-contract checks but browser verification remains
  blocked by shared-renderer desktop overflow; `reports/portfolio_report_qa.md` records the failure
  and no unverified HTML is delivered.
- Public `origin/main` has a clean parentless 97-file product history; root `c9e2854`, security
  hardening `5a1f05d`, checkout-v7 `0f6a741`, and setup-python-v7 `d705238` were pushed without force.
- Publication guard scans staged and committed snapshots, is enforced by executable pre-push hook
  and CI, and passes on the complete 456,168-byte HEAD. Six guard tests cover allow/deny behavior.
- GitHub repository is PUBLIC with default `main`; CI run `31404286936` succeeded. Dependabot is
  enabled; official checkout/setup-python v7 passed bot checks before being applied locally and pushed.
- Historical research remains local only on `research-history-local-20260810`/`research-origin`;
  public commands must never push that branch, `--all`, `--mirror`, or tags.
- Weak-label report remains micro F1 0.8273 on 332/555 evaluable documents; weak labels are not gold.
- Raw CSV, human annotation CSVs, and repaired AI CSV/XLSX are Git-ignored. No commit, push, or
  deployment was performed.

Active next task: **M5b HUMAN/ENV-GATE — use a working interactive browser to review desktop/mobile
and loading/error/empty/extraction/matching states, then capture a 2-4 minute public-safe walkthrough.**
Known workspace condition: local `RM.ipynb` remains user-owned and is ignored by the clean public
repository; do not overwrite, revert, stage, normalize, or publish it. Historical research refs are
local-only and must never be pushed to `origin`.

