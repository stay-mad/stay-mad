# J. Cloud Run Architecture — Stay Mad §53-J

> Deployment target: Google Cloud Run + Cloud SQL PostgreSQL.
> Setiap keputusan Cloud service non-trivial memerlukan ADR.

---

## 1. Arsitektur Deployment

```
                         ┌─────────────────────────┐
                         │   GitHub / Artifact      │
                         │   Registry               │
                         │   (Container Images)     │
                         └────────────┬────────────┘
                                      │ deploy
                         ┌────────────▼────────────┐
              ┌──────────┤   Cloud Run (Backend)   ├────────────┐
              │          │   Python / FastAPI       │            │
   HTTPS      │          │   Port 8080              │            │
   Requests   │          └────────────┬────────────┘            │
──────────────►                       │                          │
              │          ┌────────────▼────────────┐            │
              └──────────┤   Cloud Run (Frontend)  │            │
                         │   Next.js / SSR          │            │
                         │   Port 3000              │            │
                         └─────────────────────────┘            │
                                                                 │
                 ┌───────────────────────────────────────────────┘
                 │
    ┌────────────▼────────────┐     ┌────────────────────────┐
    │   Cloud SQL             │     │   Secret Manager       │
    │   PostgreSQL + pgvector │     │   - GEMINI_API_KEY      │
    │   Private IP            │     │   - DATABASE_URL        │
    └─────────────────────────┘     │   - EMBEDDING_MODEL    │
                                    └────────────────────────┘
    ┌─────────────────────────┐
    │   Cloud Logging         │     ┌────────────────────────┐
    │   (structured logs)     │     │   Artifact Registry    │
    │   + Cloud Monitoring    │     │   Docker images        │
    └─────────────────────────┘     └────────────────────────┘
```

---

## 2. Cloud Run Services

### 2.1 Backend Service

| Parameter | Nilai |
|---|---|
| Image | `REGION-docker.pkg.dev/PROJECT/stay-mad/backend:TAG` |
| Port | 8080 |
| Memory | 1Gi (min); scale up ke 2Gi jika Gemini calls berat |
| CPU | 1 (min); scale up ke 2 untuk Gemini-heavy stages |
| Min instances | 0 (cost saving; cold start acceptable) |
| Max instances | 10 |
| Timeout | 300s (untuk long-running processing jobs) |
| Concurrency | 80 |
| Service account | `stay-mad-backend@PROJECT.iam.gserviceaccount.com` |
| VPC | Private IP ke Cloud SQL (Cloud SQL Auth Proxy) |

### 2.2 Frontend Service

| Parameter | Nilai |
|---|---|
| Image | `REGION-docker.pkg.dev/PROJECT/stay-mad/frontend:TAG` |
| Port | 3000 |
| Memory | 512Mi |
| CPU | 1 |
| Min instances | 0 |
| Max instances | 5 |
| Service account | `stay-mad-frontend@PROJECT.iam.gserviceaccount.com` |

---

## 3. Cloud SQL PostgreSQL

| Parameter | Nilai |
|---|---|
| Database type | PostgreSQL 15 |
| Extensions | `uuid-ossp`, `pgvector` |
| Tier | `db-f1-micro` (MVP); upgrade sesuai load |
| Region | `asia-southeast1` (Jakarta) |
| Connection | Cloud SQL Auth Proxy via Unix socket |
| Backup | Automated daily backup, retain 7 days |
| Private IP | Ya; tidak expose public endpoint |
| Migration | Alembic (run saat deployment) |

---

## 4. IAM & Secret Management

### 4.1 Service Accounts

```
stay-mad-backend@PROJECT.iam.gserviceaccount.com
  Roles:
  - roles/cloudsql.client
  - roles/secretmanager.secretAccessor
  - roles/logging.logWriter

stay-mad-frontend@PROJECT.iam.gserviceaccount.com
  Roles:
  - roles/logging.logWriter
```

### 4.2 Secrets (Cloud Secret Manager)

| Secret Name | Isi |
|---|---|
| `stay-mad-gemini-api-key` | Gemini API key |
| `stay-mad-database-url` | PostgreSQL connection string |
| `stay-mad-embedding-model` | Embedding model name |
| `stay-mad-gemini-model` | Gemini model name |

Kredensial **tidak pernah** di-hardcode atau dikemas dalam image Docker.

---

## 5. Environment Variables per Service

### Backend

```env
GEMINI_API_KEY=<dari Secret Manager>
GEMINI_MODEL=<dari Secret Manager>
EMBEDDING_MODEL=<dari Secret Manager>
DATABASE_URL=<dari Secret Manager>
ENVIRONMENT=production          # trigger startup check: fixture mode harus off
GEMINI_FIXTURE_MODE=false       # startup gagal jika true di production
LOG_LEVEL=INFO
DATA_MODE=live                  # atau demo untuk deployment demo
```

### Frontend

```env
NEXT_PUBLIC_API_URL=https://backend-HASH-REGION.run.app
NEXT_PUBLIC_DATA_MODE=live
```

---

## 6. Deployment Pipeline (CI/CD Sketch)

```
git push main
    │
    ▼
GitHub Actions
    ├── lint (ruff, mypy, eslint)
    ├── test (pytest, jest)
    ├── build Docker images
    ├── push ke Artifact Registry
    └── deploy ke Cloud Run
          ├── run Alembic migrations (backend init container)
          └── health check: GET /health → 200 OK
```

> Detail pipeline CI/CD didefinisikan di Stage 07. Sketsa ini untuk arsitektur reference saja.

---

## 7. Health & Observability

### 7.1 Health Endpoint

`GET /health` — dikembalikan 200 dengan payload:

```json
{
  "status": "ok",
  "database": "connected",
  "gemini": "reachable",
  "fixture_mode": false,
  "version": "0.1.0",
  "environment": "production"
}
```

Jika `fixture_mode = true` di environment `production`: startup failure, health endpoint tidak pernah menjawab 200.

### 7.2 Structured Logging (Cloud Logging)

Setiap pipeline stage menghasilkan log event terstruktur:

```json
{
  "severity": "INFO",
  "stage": "claim_extracted",
  "article_version_id": "uuid",
  "claim_count": 8,
  "processing_run_id": "uuid",
  "duration_ms": 1250,
  "model_version": "gemini-2.0-flash"
}
```

Correlation ID (`processing_run_id`) menyambungkan log lintas stage.

---

## 8. Scaling Path

| Scale Level | Perubahan Infrastruktur |
|---|---|
| MVP (10–20 sumber, ratusan artikel/hari) | Setup saat ini; db-f1-micro |
| Growth (50+ sumber, ribuan artikel/hari) | Upgrade Cloud SQL tier; tambah Cloud Tasks untuk job queue |
| Regional (Asia, jutaan artikel) | Pisahkan ingestion service; tambah Pub/Sub + Worker pool |

Arsitektur modular monolith saat ini mendukung ekstraksi modul ke service terpisah tanpa rewrite schema.

---

## 9. Checklist Deployment Pre-launch

- [ ] `GEMINI_FIXTURE_MODE=false` di production
- [ ] Semua secret di Secret Manager, bukan env vars hardcoded
- [ ] Alembic migration sukses
- [ ] `GET /health` mengembalikan 200
- [ ] `GET /events` mengembalikan data dari `processing_run_id` valid
- [ ] Frontend berhasil load data dari backend API
- [ ] Smoke test `deploy/smoke_test.sh` lulus
- [ ] Cloud Logging aktif dengan structured logs
