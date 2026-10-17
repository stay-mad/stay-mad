# A. Arsitektur Produk — Stay Mad §53-A

> **Urutan otoritas**: ADR/decisions.md > Addendum > Master Spec > asumsi mandiri.
> Dokumen ini adalah output wajib §53-A. Tidak ada application code di sini.

---

## 1. Gambaran Sistem

Stay Mad adalah platform **Event Intelligence** berbasis AI yang mengubah berita yang terfragmentasi menjadi representasi peristiwa nyata yang terstruktur, berprovenans, dan dapat diverifikasi.

```
SUMBER TERPERCAYA (allowlist docs/sources.md)
        │  RSS / API / Official Gov
        ▼
┌──────────────────────────────────────────────────────────────┐
│  LAPISAN INGEST                                              │
│  - Adapter per sumber (RSS, API, Gov)                        │
│  - Validasi domain allowlist                                 │
│  - Normalisasi artikel → ArticleVersion (immutable)          │
│  - Deduplikasi content-hash                                  │
│  - Rate-limit & robots.txt compliance                        │
└───────────────────────┬──────────────────────────────────────┘
                        │ ArticleVersion (immutable record)
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  LAPISAN EKSTRAKSI  [Gemini Call Type 1: Extract]            │
│  - Klaim atomik + kutipan verbatim sumber                    │
│  - Entitas: lokasi, org, orang, infrastruktur                │
│  - Kualifikasi temporal (event_time, precision, timezone)    │
│  - Kategori artikel (3 bounded MVP categories)               │
│  - Anti-injection: teks = data, bukan instruksi sistem       │
└───────────────────────┬──────────────────────────────────────┘
                        │ Claim[] + Entity[] + TemporalRef[]
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  EVENT RESOLUTION ENGINE                                     │
│                                                              │
│  Tier 1 — Deterministic                                      │
│    - Hard constraints: lokasi, waktu, kategori               │
│    - Content-hash deduplication                              │
│    - Source family grouping (anti-corroboration inflation)   │
│                                                              │
│  Tier 2 — Embedding Retrieval                                │
│    - pgvector cosine top-K candidates                        │
│    - Score: location overlap, time delta, entity match       │
│                                                              │
│  Tier 3 — Gemini Adjudication [Call Type 2: Adjudicate]      │
│    - Hanya kandidat lolos Tier 1+2 yang dikirim ke Gemini    │
│    - Output: SAME_EVENT|RELATED|SEPARATE|NEEDS_REVIEW        │
│    - Decision reason codes + evidence_claim_ids disimpan     │
└───────────────────────┬──────────────────────────────────────┘
                        │ EventMembership + AuditRecord
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  INTELLIGENCE LAYER                                          │
│  - Timeline reconstruction (temporal normalization)          │
│  - Conflict detection (nilai, satuan, scope, sumber)         │
│  - EventSnapshot generation (material changes only)          │
│  - EventChange / change-set computation                      │
│  - Confidence score (numerik + evidence_status +             │
│    verification_level → bucket HIGH/MEDIUM/LOW)              │
│  - Importance score (5 komponen; TERPISAH dari confidence)   │
│  - Actionability classification (source-gating ketat)        │
│                                                              │
│  [Gemini Call Type 3: Synthesize]                            │
│    - Narasi final WHAT HAPPENED, WHY IT MATTERS, WHO, WHAT   │
│    - Conflict summary + action text (hanya bila sumber resmi)│
└───────────────────────┬──────────────────────────────────────┘
                        │ EventSnapshot (validated + versioned)
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  PERSISTENCE — PostgreSQL + pgvector (Cloud SQL)             │
│  - Semua entity: append-only / immutable record              │
│  - Embedding store: klaim + event summary                    │
│  - ProcessingRun: provenance metadata per pipeline run       │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  REST API (FastAPI + OpenAPI)                                │
│  - Membaca data yang sudah dipersist & divalidasi            │
│  - Page load TIDAK menunggu Gemini (async processing)        │
│  - Endpoint: lihat docs/contracts/openapi.yaml               │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js / React / TypeScript)                     │
│  - Screen 1: Daily Overview (Jakarta / Indonesia)            │
│  - Screen 2: Event Detail (WHAT HAPPENED → WHAT UNKNOWN)     │
│  - Screen 3: Processing & Evidence (BUKAN "AI Reasoning")    │
│  - Label mode: live | demo                                   │
│  - Empty / loading / error states dari API nyata             │
└──────────────────────────────────────────────────────────────┘
                        │
              ┌─────────────────────┐
              │    Cloud Run        │
              │  backend + frontend │
              └─────────────────────┘
```

---

## 2. Modul Backend (Modular Monolith)

| Modul | Tanggung Jawab | ADR Ref |
|---|---|---|
| `ingest` | Adapter per sumber, normalisasi artikel, dedup, rate-limit | ADR-001 |
| `extraction` | Gemini Extract call, claim atomisasi, entity/temporal extraction | ADR-001, ADR-007 |
| `resolver` | Tier 1-3 resolution pipeline, EventMembershipAudit, decision records | ADR-001, ADR-005 |
| `timeline` | Temporal normalization, precision preservation, chronological ordering | ADR-001 |
| `intelligence` | Confidence, importance, actionability, conflict detection | ADR-001, ADR-004, ADR-006 |
| `synthesis` | Gemini Synthesize call, narasi final, caching | ADR-001, ADR-007 |
| `jobs` | Async job state machine, idempotency key, retry/backoff, dead-letter | ADR-001 |
| `api` | FastAPI routes, OpenAPI schema, middleware keamanan | ADR-001, ADR-002 |
| `llm` | Gemini client abstraction, prompt versioning, schema version, cache | ADR-007 |
| `db` | SQLAlchemy models, Alembic migrations, pgvector | ADR-003 |
| `eval` | Evaluation runner (blind run; tidak membaca/memodifikasi gold labels) | ADR-008 |

---

## 3. Batasan Penting (Hard Rules)

| # | Aturan | Sumber |
|---|---|---|
| H1 | Startup gagal jika `GEMINI_FIXTURE_MODE` aktif di environment `production` | DEC-0006 |
| H2 | Seluruh teks artikel/RSS adalah data pasif; tidak pernah dieksekusi sebagai instruksi | DEC-0004 |
| H3 | Semua angka pada UI harus berasal dari query dengan `processing_run_id` yang valid | DEC-0006 |
| H4 | Klaim, ArticleVersion, EventSnapshot adalah immutable record (append-only) | DEC-0005 |
| H5 | API membaca dari persisted store; page load ≠ fresh Gemini call | Addendum §9 |
| H6 | Domain di luar `config/sources.yaml` ditolak saat ingest | DEC-0003 |
| H7 | `importance_score` tidak boleh memasukkan `confidence_score` sebagai komponen | DEC-0001→Conflict #1 |
| H8 | `ACTION REQUIRED` hanya dari sumber resmi (BMKG/BPBD/BNPB/Pemerintah) | DEC-0004, Addendum §5.6 |
| H9 | Screen 3 bernama "Processing & Evidence"; chain-of-thought Gemini tidak boleh tampil | Addendum §5.8 |
| H10 | Gemini model dipilih saat implementasi dan dikonfigurasi via `GEMINI_MODEL` env var | ADR-007 |

---

## 4. Referensi Silang

| Dokumen | Path |
|---|---|
| Data Model | [`B-data-model.md`](./B-data-model.md) |
| Gemini Architecture | [`C-gemini-architecture.md`](./C-gemini-architecture.md) |
| Event Resolution | [`D-event-resolution-algorithm.md`](./D-event-resolution-algorithm.md) |
| Timeline Algorithm | [`E-timeline-algorithm.md`](./E-timeline-algorithm.md) |
| Confidence Algorithm | [`F-confidence-algorithm.md`](./F-confidence-algorithm.md) |
| Importance Algorithm | [`G-importance-algorithm.md`](./G-importance-algorithm.md) |
| Actionability Algorithm | [`H-actionability-algorithm.md`](./H-actionability-algorithm.md) |
| Evaluation Framework | [`I-evaluation-framework.md`](./I-evaluation-framework.md) |
| Cloud Run Architecture | [`J-cloud-run-architecture.md`](./J-cloud-run-architecture.md) |
| Risk Register | [`K-risk-register.md`](./K-risk-register.md) |
| OpenAPI contract | [`../contracts/openapi.yaml`](../contracts/openapi.yaml) |
