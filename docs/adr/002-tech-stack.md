# ADR-002: Tech Stack

**Tanggal**: 2026-10-11
**Status**: Accepted
**Penulis**: Architecture Agent

---

## Konteks

Master Spec §34 mendefinisikan stack yang diinginkan. Perlu konfirmasi bahwa stack ini kompatibel dengan Addendum §9 (async processing, OpenAPI) dan deployment target Cloud Run.

## Keputusan

### Backend

| Komponen | Pilihan | Versi Target |
|---|---|---|
| Bahasa | Python | 3.11+ |
| Framework | FastAPI | ≥ 0.110 |
| ORM | SQLAlchemy | 2.x (async) |
| Migration | Alembic | ≥ 1.13 |
| Validation | Pydantic | v2 |
| Job processing | Background tasks (FastAPI) → Cloud Tasks di Growth stage | — |
| HTTP client | httpx (async) | ≥ 0.27 |

### Frontend

| Komponen | Pilihan |
|---|---|
| Framework | Next.js 14+ (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| State | React Query (server state) |

### AI

| Komponen | Pilihan |
|---|---|
| Model | Dikonfigurasi via `GEMINI_MODEL` env var (lihat ADR-007) |
| SDK | `google-generativeai` Python SDK |
| Embedding | Dikonfigurasi via `EMBEDDING_MODEL` env var (lihat ADR-007) |

### Database

| Komponen | Pilihan |
|---|---|
| RDBMS | PostgreSQL 15 |
| Extension | pgvector 0.7+ |
| Cloud service | Cloud SQL |
| Cache | Redis opsional (Stage 04+) via ADR terpisah |

### Deployment

| Komponen | Pilihan |
|---|---|
| Kontainerisasi | Docker |
| Registry | Artifact Registry |
| Deployment | Cloud Run |
| CI/CD | GitHub Actions (dikonfigurasi Stage 07) |
| Secrets | Google Cloud Secret Manager |

## Konsekuensi

**Positif**:
- Stack well-supported dengan dokumentasi lengkap.
- Python ecosystem kaya untuk NLP/AI tooling.
- Next.js SSR kompatibel dengan Cloud Run.

**Negatif**:
- Python async dengan SQLAlchemy memerlukan perhatian pada connection pooling.
- Next.js di Cloud Run memerlukan cold start tuning.

**Risiko**: RSK-14 (deployment cold start).
