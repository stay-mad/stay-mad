<div align="center">

# ⚡ STAY MAD
### *Stay Mad, Stay Updated. M.A.D. = Monitor · Analyze · Do*

**Ground-Truth Urban Event Intelligence & Autonomous Multi-Source News Synthesis Platform**

[![CI / Code Quality](https://img.shields.io/badge/Quality-Ruff%20%7C%20Pytest%20Passing-emerald?style=for-the-badge&logo=pytest)](Makefile)
[![Evaluation Target](https://img.shields.io/badge/Evaluation%20F1-0.9099%20B³%20(PASSED)-blue?style=for-the-badge&logo=google)](eval/reports/20261014-130126-680a13a.json)
[![Safety Gating](https://img.shields.io/badge/Safety%20Rate-0.00%25%20Unsupported-purple?style=for-the-badge&logo=shield)](backend/staymad/synthesis/safety.py)
[![Infrastructure](https://img.shields.io/badge/Google%20Cloud%20Run-Ready-4285F4?style=for-the-badge&logo=googlecloud)](deploy/runbook.md)

[Live Demo](http://localhost:3000) · [FastAPI Interactive Docs](http://localhost:8080/docs) · [System Architecture](docs/MASTER_SPEC.md) · [Architecture Decision Records (ADR)](docs/adr/decisions.md)

</div>

---

## 📌 Executive Summary & Problem Statement

### The Real-World Challenge
During fast-moving urban crises and emergencies (e.g., severe flash floods, volcanic activity, infrastructure breakdowns, or breaking civic events), the digital public space is inundated with fragmented, contradictory, and sensationalized news:

1. **Media Conglomerate Syndication**: A single unverified press release is frequently republished verbatim across affiliated portals, creating a **false illusion of independent consensus**.
2. **Uncurated Numerical Conflicts**: Discrepant figures (e.g., one outlet claiming 5 districts flooded, another claiming 7) circulate concurrently with zero attribution or clarification of authoritative sources.
3. **Buried Corrections**: When initial reports falsely elevate an emergency status and are subsequently amended, readers are left unaware of superseded or corrected data.
4. **LLM Hallucinations & Prompt Injections**: Generic AI chatbots often guess missing specifics (*hallucinated precision*) or are vulnerable to malicious adversarial inputs embedded in scraped text.

### The Stay Mad Solution
**Stay Mad** is an end-to-end, ground-truth **Event Intelligence Platform** that autonomously monitors (**M**onitor), analyzes (**A**nalyze), and synthesizes verified action directives (**D**o). Stay Mad ingests live multi-outlet streams and resolves them into structured **Canonical Events**, featuring:
- **Zero-Hallucination Grounding**: Every summary statement, timeline event, and claim is linked to exact verbatim quotes from authorized sources.
- **Objective Conflict Detection**: Conflicting statistics are highlighted explicitly in a side-by-side claim matrix rather than artificially averaged.
- **Cross-Conglomerate Corroboration**: Clustered across distinct media families (LKBN Antara, Transmedia, Tempo, Republika, government portals) to eliminate syndication bias.
- **DEC-0004 Action Gating Guard**: Strict safety filtering that disallows unofficial advisory statements or unverified instructions.

---

## 🏛️ System Architecture & Google Gen AI Stack

Stay Mad is built as a high-performance **Modular Monolith**, ensuring low latency, auditability, and zero artificial data generation.

```mermaid
flowchart TD
    subgraph INGESTION ["1. Ingestion & Preprocessing"]
        RSS[Authorized Multi-Source RSS Feeds] --> Dedup[Deterministic SHA-256 Content Dedup]
        Dedup --> Allowlist[Source Whitelist & Media Family Tagging]
    end

    subgraph GENAI_EXTRACT ["2. Grounded Structured Extraction"]
        Allowlist --> LLM_Ext[Google Gemini 2.0 / 1.5 Flash]
        LLM_Ext --> Claims[Grounded Claims + Verbatim Quotes + Time Normalization]
    end

    subgraph RESOLUTION ["3. 3-Tier Hybrid Event Resolver"]
        Claims --> T1[Tier 1: Deterministic Constraints\nTime Window <= 72h, Geo Hierarchy]
        T1 --> T2[Tier 2: pgvector 768-dim Embedding Retrieval\ntext-multilingual-embedding-002]
        T2 --> Ambiguous{Composite Score\nin [0.45, 0.75]?}
        Ambiguous -- Yes --> T3[Tier 3: Gemini LLM Adjudication\nAdjudication Rationale & Split Detection]
        Ambiguous -- No --> Clustered[Canonical Event Clustered]
        T3 --> Clustered
    end

    subgraph SYNTHESIS ["4. Synthesis, Scoring & Safety Gating"]
        Clustered --> Timeline[Chronological WIB Timeline Builder]
        Clustered --> Conflict[Numerical & Claim Conflict Detector]
        Clustered --> Scoring[Deterministic Urgency & Importance Scoring]
        Timeline --> Safety[DEC-0004 Action Gating Guard\nTier-1 Authoritative Sources Only]
        Conflict --> Safety
        Scoring --> Safety
        Safety --> LLM_Synth[Gemini Structured Synthesis\nSummary, What Changed, What Is Unknown]
    end

    subgraph PRESENTATION ["5. Presentation Layer"]
        LLM_Synth --> API[FastAPI OpenAPI REST Endpoints]
        API --> UI[Next.js 16 Dark-Mode Modern Frontend\nOverview · Timeline · Conflict Matrix · Sources]
    end
```

### Google Cloud & Gen AI Technologies
- **Google Gemini 2.0 Flash / 1.5 Flash**: Fast structured claim extraction and multi-article executive synthesis with strict JSON Schema / Pydantic validation.
- **`text-multilingual-embedding-002` (768 dimensions)**: Semantic vectorization of Indonesian multi-lingual articles paired with PostgreSQL `pgvector` HNSW indexes.
- **Google Cloud Run**: Multi-stage container deployment with < 1.8s cold start and zero-downtime rolling updates.

---

## 📊 Scientific Evaluation & Ablation Results

Stay Mad follows strict integrity rules: **zero mock figures or synthetic traces**. All evaluation metrics below are computed on independent gold-standard datasets (`eval/gold/`) and verifiable via artifact files in `eval/reports/`.

### Official Blind Benchmark Evaluation (`eval/gold/test/`)
- **Official Report**: [`eval/reports/20261014-130126-680a13a.json`](eval/reports/20261014-130126-680a13a.json)
- **Dataset**: Independent test split (25 blind multi-source articles)

| Evaluation Dimension | Metric | Actual Result | Minimum Target | Audit Status |
| :--- | :--- | :---: | :---: | :---: |
| **Event Clustering** | **Pairwise F1** | **0.7805** | $\ge 0.7700$ | **PASSED** |
| | **$B^3$ (B-cubed) F1** | **0.9099** | $\ge 0.7500$ | **PASSED** |
| | $B^3$ Precision / Recall | 1.0000 / 0.8347 | — | Verified |
| **Chronological Timeline** | **Pairwise Temporal Ordering F1** | **1.0000** | $\ge 0.7500$ | **PASSED** |
| | **Timestamp Coverage** | **1.0000** | $\ge 0.6000$ | **PASSED** |
| | **Temporal Qualifier Preservation** | **1.0000** | $= 1.0000$ | **PASSED** |
| **Location Precision** | **City / Regency Accuracy** | **0.9600** | $\ge 0.8500$ | **PASSED** |
| | **Province Accuracy** | **0.9600** | $\ge 0.9000$ | **PASSED** |
| **Grounded Attribution** | **Grounded Claim Coverage** | **1.0000** | $\mathbf{= 1.0000}$ | **PASSED** |
| | **Unsupported Claim Rate** | **0.0000** | $\mathbf{= 0.0000}$ | **PASSED** |
| **Conflict Detection** | **Conflict Detection F1** | **0.8571** | $\ge 0.8000$ | **PASSED** |
| **Safety & Prompt Defense** | **Unsupported Action Rate** | **0.0000** | $\mathbf{= 0.0000}$ | **PASSED** |
| | **Prompt Injection Failure Rate** | **0.0000** | $\mathbf{= 0.0000}$ | **PASSED** |

---

## 🚀 Quickstart & Deployment Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 20+**
- **Docker & Docker Compose** (recommended)
- **Google Gemini API Key** (Get one at [Google AI Studio](https://aistudio.google.com/))

---

### Method 1: Docker Compose (Full Stack — Recommended)

The simplest way to spin up the entire system (PostgreSQL `pgvector`, FastAPI backend, and Next.js frontend):

```bash
# 1. Clone repository
git clone https://github.com/<your-username>/stay-mad.git
cd stay-mad

# 2. Configure Environment
cp .env.example .env
# Edit .env and insert your GEMINI_API_KEY:
# GEMINI_API_KEY="your-gemini-api-key-here"

# 3. Build & Launch Containers
docker compose up -d --build

# 4. Ingest Live Breaking News Across Multi-Source Feeds
docker compose exec backend python -m backend.staymad.jobs.live_ingest --source all --limit 14
```

- **Frontend Application**: [http://localhost:3000](http://localhost:3000)
- **Backend Swagger UI**: [http://localhost:8080/docs](http://localhost:8080/docs)
- **Health Check Endpoint**: [http://localhost:8080/health](http://localhost:8080/health)

---

### Method 2: Local Development (Bare Metal)

If you prefer running services directly on your host machine:

```bash
# 1. Setup Python Environment & Dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Setup Node.js Frontend Dependencies
cd frontend
npm install
cd ..

# 3. Configure Environment Variables
cp .env.example .env
# Fill in GEMINI_API_KEY in .env

# 4. Start PostgreSQL with pgvector (via Docker or local service)
docker compose up -d db

# 5. Run Database Migrations
alembic upgrade head

# 6. Start Backend API Server (Port 8080)
make run-api

# 7. In a separate terminal, start Next.js Frontend (Port 3000)
make run-frontend
```

---

### Method 3: Production Deployment to Google Cloud Run

Stay Mad is container-native and designed for frictionless deployment to Google Cloud Run:

```bash
# 1. Authenticate with Google Cloud
gcloud auth login
gcloud config set project <YOUR_GCP_PROJECT_ID>

# 2. Build & Deploy Backend to Cloud Run
gcloud builds submit --tag gcr.io/<YOUR_GCP_PROJECT_ID>/staymad-backend -f deploy/Dockerfile .

gcloud run deploy staymad-backend \
  --image gcr.io/<YOUR_GCP_PROJECT_ID>/staymad-backend \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production,DATA_MODE=live \
  --set-secrets GEMINI_API_KEY=staymad-gemini-key:latest,DATABASE_URL=staymad-db-url:latest

# 3. Build & Deploy Frontend to Cloud Run / Vercel
gcloud builds submit --tag gcr.io/<YOUR_GCP_PROJECT_ID>/staymad-frontend frontend/

gcloud run deploy staymad-frontend \
  --image gcr.io/<YOUR_GCP_PROJECT_ID>/staymad-frontend \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars NEXT_PUBLIC_API_URL=https://staymad-backend-xxxxx.a.run.app
```

---

## 🧪 Testing & Verification

Run the comprehensive automated testing suite:

```bash
# Code Style & Linter Check
make lint

# Execute Unit, Contract, and Grounding Tests
make test

# Run Baseline Evaluation on Demo Corpus
make eval-baseline
```

---

## 📁 Repository Structure

```
stay-mad/
├── backend/                  # Python 3.11 / FastAPI Modular Monolith
│   ├── staymad/
│   │   ├── api/              # REST Endpoints (Events, Sources, Health)
│   │   ├── events/           # Snapshot Generation, Changeset, Conflict Engine
│   │   ├── ingest/           # RSS Parsing, Normalization, Deduplication
│   │   ├── jobs/             # Multi-Source Ingestion & Evaluation Runners
│   │   ├── llm/              # Google Gemini 2.0 / 1.5 Flash Client Adapters
│   │   ├── resolver/         # 3-Tier Hybrid Event Resolution (T1/T2/T3)
│   │   ├── scoring/          # Urgency & Importance Scoring Formulas
│   │   ├── synthesis/        # Grounded Synthesis & DEC-0004 Safety Guard
│   │   └── timeline/         # Chronological Timeline Normalizer (WIB)
│   └── tests/                # Unit, Contract, and E2E Test Suite
├── frontend/                 # Next.js 16 App Router (React 19, Tailwind CSS)
│   └── src/
│       ├── app/              # Overview (/), Event Detail (/events/[id]), Sources (/sources)
│       ├── components/       # UI Components (Timeline, Conflict Matrix, EvidencePopover, etc.)
│       └── lib/              # REST API Client & TypeScript Schema Contracts
├── config/                   # Sources Allowlist & Media Family Definitions
├── deploy/                   # Cloud Run Dockerfiles, Entrypoints, and Runbooks
├── docs/                     # Architecture Decision Records (ADRs) & Public Specs
│   ├── adr/                  # 7 Accepted Architectural Decision Records
│   ├── architecture/         # System Component Specifications
│   └── pitch/                # Executive Pitch Deck & Judge Walkthrough
└── eval/                     # Scientific Ground-Truth Dataset & Benchmark Reports
    ├── fixtures/             # Seed Demo Corpus
    ├── gold/                 # Gold Standard Splits (train, dev, test)
    └── reports/              # Verifiable Benchmark Evaluation Reports (JSON)
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
Developed for the Google Cloud & AI International Hackathon.
