# Stay Mad — Operations & Cloud Run Deployment Runbook

> **Target Deployment**: Google Cloud Run + Cloud SQL PostgreSQL (`pgvector`)  
> **Region**: `asia-southeast1` (Jakarta)  
> **Otoritas**: `docs/architecture/J-cloud-run-architecture.md` (§53-J), `docs/decisions.md` (DEC-0006)

---

## 1. Prasyarat Lingkungan & Alat

Sebelum menjalankan deployment atau operasional sistem, pastikan perangkat lokal atau CI worker telah memiliki:
- **Google Cloud SDK (`gcloud`)** v450.0.0+ terautentikasi (`gcloud auth login`).
- **Docker Engine** 24.0+ & **Docker Compose** v2.20+.
- **Python 3.11+** dan virtualenv terpasang.
- **Node.js 20+** (untuk pengujian frontend lokal).
- Akses ke Google Cloud Project dengan peran minimal:
  - `roles/run.admin`
  - `roles/secretmanager.admin`
  - `roles/artifactregistry.admin`
  - `roles/iam.serviceAccountUser`

---

## 2. Secrets & Konfigurasi Google Secret Manager

Sesuai **Addendum §9** & **DEC-0006**, kredensial, connection strings, dan API keys **DILARANG KERAS** disimpan di dalam Dockerfile, image container, atau commit git. Semua rahasia wajib bersumber dari Google Secret Manager:

| Secret Name | Deskripsi | Format / Contoh Nilai |
|---|---|---|
| `stay-mad-gemini-api-key` | Google Gemini API Key | `AIzaSy...` |
| `stay-mad-database-url` | PostgreSQL Connection String | `postgresql://staymad:PASS@/staymad_db?host=/cloudsql/PROJECT:REGION:INSTANCE` |
| `stay-mad-embedding-model` | Nama Model Embedding Vertex/Gemini | `text-embedding-004` |
| `stay-mad-gemini-model` | Nama Model Inferensi Gemini | `gemini-2.0-flash` |

### Membuat Secret Baru di Secret Manager:
```bash
# 1. Gemini API Key
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create stay-mad-gemini-api-key \
    --data-file=- --replication-policy="automatic"

# 2. Database Connection String
echo -n "postgresql://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE" | \
    gcloud secrets create stay-mad-database-url --data-file=- --replication-policy="automatic"
```

---

## 3. Deployment Otomatis ke Google Cloud Run

Gunakan skrip terotomatisasi `deploy/deploy_gcp.sh`:

```bash
# Set GCP Project dan jalankan deployment
export PROJECT_ID="my-staymad-production"
export REGION="asia-southeast1" # Jakarta
bash deploy/deploy_gcp.sh
```

Skrip di atas secara otomatis melakukan:
1. Validasi dan pengaktifan API Cloud Run, Secret Manager, Artifact Registry, dan Cloud SQL.
2. Penyediaan Service Accounts `stay-mad-backend` dan `stay-mad-frontend` dengan prinsip Least Privilege.
3. Multi-stage container build untuk Backend (`python:3.11-slim`) dan Frontend Next.js (`node:20-alpine` standalone).
4. Push container image ke Artifact Registry (`asia-southeast1-docker.pkg.dev/...`).
5. Deployment Cloud Run Backend dengan port `8080`, CPU 1, RAM 1Gi, auto-scaling 0–10 instances, mounting Secret Manager.
6. Auto-migrasi schema database Alembic saat container booting (`RUN_MIGRATIONS=true`).
7. Deployment Cloud Run Frontend dengan pointing dinamis ke Backend URL.
8. Verifikasi kesiapan sistem via healthcheck.

---

## 4. Pengujian Lokal Terpadu (Docker Compose)

Untuk mereplikasi lingkungan produksi secara penuh di mesin lokal:

```bash
# 1. Jalankan seluruh stack (Database pgvector, Backend FastAPI, Frontend Next.js)
make up
# atau: docker compose up -d --build

# 2. Pantau status container & healthcheck
docker compose ps

# 3. Jalankan automated smoke test
make smoke-test
# atau: API_URL=http://localhost:8080 bash deploy/smoke_test.sh

# 4. Hentikan stack
make down
```

---

## 5. Observabilitas & Google Cloud Logging

Backend Stay Mad mengimplementasikan **Structured JSON Logging** yang otomatis diurai oleh Google Cloud Logging.

### Query Cloud Logging di GCP Console:
Untuk menelusuri alur pemrosesan klaim, latency API, atau error per correlation ID:

```sql
resource.type="cloud_run_revision"
resource.labels.service_name="stay-mad-backend"
jsonPayload.stage="api_request"
jsonPayload.latency_ms > 200
```

Untuk melacak siklus event extraction berdasarkan `processing_run_id`:
```sql
resource.type="cloud_run_revision"
jsonPayload.processing_run_id="c0a80101-0000-0000-0000-000000000001"
```

---

## 6. Prosedur Rollback & Penanganan Insiden

Bila terjadi anomali atau kegagalan versi baru di Cloud Run:

1. **Traffic Migration Instan (Zero-Downtime Rollback)**:
   ```bash
   # Arahkan 100% traffic ke revisi sebelumnya yang stabil
   gcloud run services update-traffic stay-mad-backend \
       --region=asia-southeast1 \
       --to-revisions=PREVIOUS_REVISION_NAME=100
   ```
2. **Database Rollback (Bila Perlu)**:
   ```bash
   alembic downgrade -1
   ```
3. **Verifikasi Kesehatan Pasca-Rollback**:
   ```bash
   bash deploy/smoke_test.sh
   ```
