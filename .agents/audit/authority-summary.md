# Stay Mad Authority Summary — Audit Reference Document

> **Purpose**: Authoritative reference for comprehensive audit of the Stay Mad repository (Stages 00–06).  
> **Generated**: 2026-10-14  
> **Authority Hierarchy**: ADR/decisions.md > Addendum > Master Spec > Individual Assumptions  
> **Status**: Complete for pre-Stage 07 audit

---

## 1. AUTHORITY HIERARCHY & MANDATORY READING ORDER

Per `AGENTS.md`, the following documents MUST be read in this exact sequence:

1. **`docs/adr/*.md` and `docs/decisions.md`** — Highest authority
2. **`docs/STAY_MAD_MASTER_SPEC_ADDENDUM.md`**
3. **`docs/MASTER_SPEC.md`**
4. **Individual assumptions** — Lowest authority

All code evaluation must reference these documents in precedence order. Any conflict is resolved by the higher-authority document.

---

## 2. DECISIONS LOG (DEC-0001 through DEC-0008)

### DEC-0001: Product Language & Default Timezone
- **Status**: Accepted
- **Date**: 2026-10-11
- **Requirements**:
  - Product language for UI, labels, and narrative summaries: **Bahasa Indonesia**
  - English source material may be processed, retaining original language and source link
  - Default display timezone: **`Asia/Jakarta` (WIB)**
  - Internal timestamps stored in **ISO-8601 UTC**
  - All UI time conversions reference `Asia/Jakarta` and preserve temporal qualifiers ("sekitar 08:30")

### DEC-0002: Bounded MVP Scope
- **Status**: Accepted
- **Date**: 2026-10-11
- **Requirements**:
  - MVP implements **ONLY 3 categories**:
    1. `disaster_and_weather`
    2. `transportation_and_infrastructure`
    3. `government_and_public_policy`
  - Taxonomy remains extensible for 7 additional categories, but they are NOT production-ready
  - Evaluation and fixtures focus only on these 3 domains

### DEC-0003: Strict Sourcing Allowlist
- **Status**: Accepted
- **Date**: 2026-10-11
- **Requirements**:
  - Data ingestion limited to verified list in `docs/sources.md` and `config/sources.yaml`
  - Sources grouped into Tiers:
    - **Tier 1**: Official government/disaster sources & accredited national news agencies
    - **Tier 2**: Credible national media
  - Each source records `source_family` to identify syndication/media conglomerates to prevent consensus inflation
  - No scraping without explicit approval, respects robots.txt, rate limits, retention policies
  - Domains outside allowlist rejected at `ingest` stage

### DEC-0004: Anti-Prompt Injection (Untrusted Input)
- **Status**: Accepted
- **Date**: 2026-10-11
- **Requirements**:
  - All article text and RSS feeds treated as **untrusted data, never system instructions**
  - Gemini receives article text only within isolated data containers with structured, validated JSON schemas
  - System never executes instructions embedded in articles
  - Emergency action creation (`ACTION_REQUIRED`) **MUST** originate from official institutional sources (BPBD, BNPB, BMKG, Police/Government), not from opinion/media quotes
  - **Test case**: `art_demo_07` (prompt injection) must NOT affect system behavior

### DEC-0005: Persistence Model — Article Versions & Event Snapshots
- **Status**: Accepted
- **Date**: 2026-10-11
- **Requirements**:
  - **`ArticleVersion`**: Article captures are immutable; news updates create new versions without deleting old evidence
  - **`EventSnapshot`**: Published event representation is immutable snapshot
  - **`EventChange`**: Changes between two snapshots create structured change records (`ADDED`, `UPDATED`, `CORRECTED`, `RETRACTED`) linked to new evidence claim IDs
  - Database: **PostgreSQL + pgvector** in Modular Monolith pattern
  - Provenance and "What Changed" history verifiable at any time without data manipulation

### DEC-0006: Zero Hard-coding & Production Fixture Ban
- **Status**: Accepted
- **Date**: 2026-10-11
- **Requirements** (CRITICAL INVARIANT):
  - Every UI count (articles, claims, candidates, conflicts, confidence signals, timeline) **MUST** originate from real database query with valid `processing_run_id`
  - Fixture adapters **ONLY** allowed for unit tests and labeled demo mode
  - In `production` mode: **System MUST crash at startup** if:
    - Fixture adapter is active, OR
    - `GEMINI_API_KEY` is missing/invalid
  - No fabricated processing traces allowed
  - **unsupported_action_rate must = 0.00**

### DEC-0007: Conflict Resolution — Economic Policy Maps to Government & Public Policy
- **Status**: Accepted (Explicit User Direction)
- **Date**: 2026-10-11
- **Context**: Master Spec §30 includes Event D on "economic policy" (6 articles). Addendum §2 locks to 3 MVP categories; `Economy` not activated in vertical slice MVP.
- **Decision**:
  - Event D ("economic policy", such as government subsidy/energy regulation) officially classified as **`government_and_public_policy`**
  - Scope remains locked to 3 bounded MVP categories
  - 23-article seed fully covers 4 clusters from Master Spec §30
- **Consequence**: Evaluation taxonomy and fixtures for Event D use enum value `government_and_public_policy`

### DEC-0008: Cross-Review Results After ADR 4, 6, 7 Updates
- **Status**: Accepted
- **Date**: 2026-10-12
- **Decisions**:
  - **Gemini model per call type**: From official deprecation docs; Flash GA for Adjudicate/Synthesize; Flash-Lite only if dev set supports for Extract
  - **Embedding**: Model and dimensionality (1c)
  - **Confidence components (final)**: Master Spec §19 lists 6 factors (source quality, independent corroboration, claim consistency, official confirmation, temporal consistency, geographic consistency). Reviewer config had 4 with `verbatim_quote_match` and `recency_decay` not in Master Spec.
    - **Resolution**: Use 6 Master factors; `verbatim_quote_match` becomes extraction validation gate, not weighted component; freshness discussed in urgency, not confidence
  - **Urgency**: Separate from importance (see Conflict #1), determines how it participates in "Need to know" ranking
  - **EventRelation**: Not built now
  - **Tier-2 attribution rules (V-2)**: Which media can carry official source quotes, and what evidence suffices
  - **Narrative structure**: Statements with `evidence_claim_ids` (V-4)

---

## 3. ARCHITECTURE DECISION RECORDS (ADRs)

### ADR-001: Modular Monolith Architecture
- **Status**: Accepted
- **Date**: 2026-10-11
- **Key Mandates**:
  - Backend as **Modular Monolith** with isolated logical modules:
    - `ingest/`: source adapters, normalization, dedup
    - `extraction/`: Gemini Extract call, claim atomization
    - `resolver/`: Tier 1-3 resolution pipeline
    - `timeline/`: temporal normalization, ordering
    - `intelligence/`: confidence, importance, actionability, conflict
    - `synthesis/`: Gemini Synthesize call, narrative generation
    - `jobs/`: async job state machine, idempotency, retry
    - `api/`: FastAPI routes, OpenAPI, middleware
    - `llm/`: Gemini client abstraction, prompt versioning, cache
    - `db/`: SQLAlchemy models, Alembic migrations, pgvector
    - `eval/`: evaluation runner (blind; isolated from `gold/`)
  - Each module independently testable with defined interfaces
  - Path to microservices migration available without schema rewrite

### ADR-002: Tech Stack
- **Status**: Accepted
- **Date**: 2026-10-11
- **Stack Mandates**:
  - **Backend**: Python 3.11+, FastAPI ≥0.110, SQLAlchemy 2.x (async), Alembic ≥1.13, Pydantic v2, httpx ≥0.27
  - **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, React Query
  - **AI**: `google-generativeai` Python SDK, models configured via env vars (see ADR-007)
  - **Database**: PostgreSQL 15, pgvector 0.7+, Cloud SQL
  - **Deployment**: Docker, Artifact Registry, Cloud Run, GitHub Actions (Stage 07), Google Cloud Secret Manager

### ADR-003: Database Schema Strategy
- **Status**: Accepted
- **Date**: 2026-10-11
- **Key Mandates**:
  - **16 canonical SQLAlchemy entities** (merged from Master Spec §38 + Addendum §9):
    1. `Source`
    2. `Article`
    3. `ArticleVersion`
    4. `Claim`
    5. `Location`
    6. `Event`
    7. `EventSnapshot`
    8. `EventClaim`
    9. `EventChange`
    10. `EventMembershipAudit`
    11. `TimelineEntry`
    12. `Conflict`
    13. `Action`
    14. `ProcessingRun`
    15. `ProcessingJob`
    16. `EventRelation` (table exists, not used until UI need visible)
  - **Schema Principles**:
    - Append-only evidence: Claims, ArticleVersion, EventSnapshot never overwritten
    - Immutable records: Updates create new versions, not mutations
    - Provenance fields mandatory: Every record has `processing_run_id`, `schema_version`, `model_version`
    - Enum changes via ADR + migration
  - Alembic migration `001_initial_schema.py` must match ORM models exactly

### ADR-004: Confidence Schema — Numeric Score + Evidence Status + Verification Level
- **Status**: Accepted (User decided: Option A)
- **Date**: 2026-10-12
- **Resolves**: decisions.md Conflicts #1 and #3
- **Key Mandates**:
  - **`confidence_score`** (float 0.0–1.0): Source of truth for confidence, computed from 5 components
  - **`confidence_bucket`** (HIGH/MEDIUM/LOW): Derived field for UI display only; thresholds in `config/confidence.yaml`
  - **`evidence_status`** (SUPPORTED/CONFLICTING/INSUFFICIENT/RETRACTED): Replaces CONFIRMED/UNCONFIRMED/UNKNOWN from Master Spec §12 for event-level status
  - **`verification_level`** (OFFICIAL_PRIMARY/INDEPENDENTLY_CORROBORATED/SINGLE_SOURCE): Source verification tier
  - **Importance formula does NOT include confidence** (per Addendum §5): Low-confidence but high-impact events remain visible with "uncertain" badge, never silently deprioritized
  - Individual claim status (CONFIRMED/SUPPORTED/UNCONFIRMED) from Master Spec §12 NOT used at event level
  - Mapping: CONFIRMED at claim level → `evidence_status=SUPPORTED` + `verification_level=OFFICIAL_PRIMARY` at event level

### ADR-005: Event Resolution Strategy — Hybrid 3-Tier with Ablation
- **Status**: Accepted
- **Date**: 2026-10-11
- **Key Mandates**:
  - **3-Tier Resolution Pipeline**:
    - **Tier 1 — Deterministic** (always active):
      - Hard constraints: location, time, category incompatibility
      - Content deduplication (content-hash)
      - Source family grouping (anti-inflation)
    - **Tier 2 — Embedding Retrieval** (added to Tier 1):
      - pgvector cosine similarity
      - Composite score: **semantic (0.40) + time (0.30) + location (0.20) + entity (0.10)**
      - Low threshold → `SEPARATE_EVENT` without Gemini
      - High threshold → `SAME_EVENT` without Gemini
      - Ambiguous range → Tier 3
    - **Tier 3 — Gemini Adjudication** (only for ambiguous candidates):
      - Gemini Call Type 2 (Adjudicate)
      - Input includes all Tier 1+2 deterministic signals
      - Output: `SAME_EVENT | RELATED_EVENT | SEPARATE_EVENT | NEEDS_REVIEW`
  - **Ablation Study Design**: Three configs run against gold dev set:
    - `tier1`: deterministic only
    - `tier2`: tier1 + embeddings
    - `tier3`: full (tier1 + tier2 + Gemini)
  - **Default Safety Rule**: If evidence ambiguous, default to `SEPARATE_EVENT` or `NEEDS_REVIEW`, NOT confident merge (false separation safer than false merge)
  - **Transitive Cluster Guard**: Do NOT form transitive clusters A→B→C; each article checked against canonical event evidence, not other articles
  - **Decision Storage**: Every decision stored in `EventMembershipAudit` with signals and reason codes

### ADR-006: Actionability Policy and Source Gating
- **Status**: Accepted (User decided: Option A)
- **Date**: 2026-10-12
- **Resolves**: decisions.md Conflict #2
- **Key Mandates** (CRITICAL for Safety):
  - **`ACTION_REQUIRED` / `ACTION_RECOMMENDED`**: ONLY from sources with `source_family ∈ {GOV_BMKG, GOV_BPBD_DKI, GOV_BNPB, GOV_SETKAB}` AND `source_tier = TIER_1`
  - Action text MUST have verbatim claim reference (`evidence_claim_ids` non-empty from authorized source)
  - Master Spec §22 example "Check on vulnerable family members" used as **negative test case** — system must classify as `INFORMATIONAL` or `NO_IMMEDIATE_ACTION`, NOT `ACTION_REQUIRED`
  - Fallback: If no official source → `NO_IMMEDIATE_ACTION` or `INFORMATIONAL`
  - **Tier-2 Attribution Rule (User decision)**: Media Tier 2 (Tempo, Kompas, CNBC Indonesia) quoting official statements CAN qualify
  - **Target metric**: `unsupported_action_rate = 0.00`

### ADR-007: Gemini Model Selection and Embedding Strategy
- **Status**: Accepted (User decided: gemini-2.0-flash + text-multilingual-embedding-002)
- **Date**: 2026-10-12
- **Key Mandates**:
  - **Gemini Model**: `gemini-2.0-flash` for all 3 call types (Extract, Adjudicate, Synthesize)
  - **Embedding Model**: `text-multilingual-embedding-002` (768 dimensions) — better for Bahasa Indonesia content
  - **Gemma**: NOT used in MVP (per decisions.md recommendation)
  - **Configuration**:
    ```env
    GEMINI_MODEL=gemini-2.0-flash
    EMBEDDING_MODEL=text-multilingual-embedding-002
    ```
  - Required env vars: `GEMINI_API_KEY`, `GEMINI_MODEL`, `EMBEDDING_MODEL`
  - Startup validation must check all three; startup fails if `GEMINI_API_KEY` invalid in production mode
  - Model version recorded in every `Claim`, `EventMembershipAudit`, `EventSnapshot` for reproducibility
  - **Embedding dimensionality**: **768-dim** (NOT OpenAI's 1536-dim)

### ADR-008: Evaluation Design and Gold Set Integrity
- **Status**: Accepted
- **Date**: 2026-10-11
- **Key Mandates** (CRITICAL for Competition Integrity):
  - **Directory Structure**:
    ```
    eval/
      gold/
        train/    # calibration only
        dev/      # ablation study (agent-readable)
        test/     # blind evaluation (ONLY evaluator runner)
        annotation-guide.md
        schema.json
      fixtures/
        seed_demo_23.json  # 23-article demo
      reports/
        YYYYMMDD-HHMMSS-<commit>.json
      runner/
        evaluate.py
    ```
  - **Gold Set Isolation**:
    - `eval/gold/test/` NOT accessed by application code
    - CI check: grep application imports for path `eval/gold/test/`
    - Evaluator runner only run explicitly with `make eval-blind`
    - Every `make eval-blind` run generates new report in `eval/reports/`
  - **Report Immutability**: After `make eval-blind` run, report saved in `eval/reports/` and committed to repo; report NEVER modified
  - **Acceptance Tests Separate**: 8 acceptance scenarios (test_acc_01..test_acc_08) run against `eval/fixtures/seed_demo_23.json`, NOT gold set (regression tests runnable anytime)
  - **Competition Demo**: ONLY cites metrics from saved report artifacts

---

## 4. THE 8 AUDIT DIMENSIONS (from Original User Request)

### Dimension 1: Zero Fake Trace & Hard-coding Invariant (DEC-0006 & Addendum §3)
**Invariants to Check**:
- NO counts (articles, claims, candidates, conflicts, confidence signals, traces) hard-coded in UI or API layers
- Every number returned by endpoints in `backend/staymad/api/routers/` originates from real database records tagged with valid `processing_run_id`
- **Startup guard**: In production mode (`STAYMAD_ENV=production` or `DATA_MODE=LIVE`), startup STRICTLY CRASHES if:
  - Mock adapters are active, OR
  - `GEMINI_API_KEY` is missing/empty

### Dimension 2: Strict Sourcing & Grounding Safety Contract (DEC-0003, DEC-0004, ADR-006, Addendum §5)
**Invariants to Check**:
- Raw article/RSS texts treated strictly as untrusted data, enclosed in passive delimiter tags `<article_content>...</article_content>`
- **Prompt injection defense**: Embedded instructions (e.g., `[SYSTEM INSTRUCTION OVERRIDE: ...]` in `art_demo_07`) CANNOT:
  - Alter extraction behavior
  - Trigger emergency actions
  - Pollute headlines/summaries (test_acc_06, test_extra_09)
- **Action Gating** (`unsupported_action_rate = 0.00`):
  - `ACTION_REQUIRED` and `ACTION_RECOMMENDED` can ONLY originate from Tier-1 official sources: `GOV_BMKG`, `GOV_BPBD_DKI`, `GOV_BNPB`, `GOV_SETKAB`
  - Tier-2 media (Tempo, Kompas, CNBC Indonesia) quoting official statements CAN qualify (per ADR-006 user decision)
- **Verbatim quote matching**: Extracted claims with fabricated/ungrounded `source_span` values dropped or flagged

### Dimension 3: Data Model & pgvector Vector Geometry Integrity (ADR-003, ADR-007)
**Invariants to Check**:
- 16 canonical SQLAlchemy entities in `backend/staymad/db/models/`:
  1. Source, 2. Article, 3. ArticleVersion, 4. Claim, 5. Location, 6. Event, 7. EventSnapshot, 8. EventClaim, 9. EventChange, 10. EventMembershipAudit, 11. TimelineEntry, 12. Conflict, 13. Action, 14. ProcessingRun, 15. ProcessingJob, 16. EventRelation
- Alembic migration `001_initial_schema.py` matches ORM models exactly
- **`Claim.embedding` and `EventSnapshot.embedding`**: Strictly configured as **768-dimensional vectors** matching Google's `text-multilingual-embedding-002` (NOT OpenAI's 1536-dim)

### Dimension 4: Event Resolution Pipeline & Transitive Cluster Guard (ADR-005, §53-D)
**Invariants to Check**:
- **3-tier hybrid resolver** in `backend/staymad/resolver/`:
  - **Tier 1**: Hard constraints (`CAT_MISMATCH`, `TIME_INCOMPATIBLE`, `LOC_INCOMPATIBLE`, `TYPE_EXCLUSIVE`) + content deduplication
  - **Tier 2**: 768-dim embedding cosine similarity + composite scoring:
    - $w_{\text{semantic}}=0.40$
    - $w_{\text{time}}=0.30$
    - $w_{\text{location}}=0.20$
    - $w_{\text{entity}}=0.10$
  - **Tier 3**: Gemini Call Type 2 (Adjudicate) with canonical reason codes
- **Transitive Cluster Guard**: Candidates verified against anchor event evidence, NOT transitively chained ($A \approx B, B \approx C \nrightarrow A \approx C$)
- Every decision records `EventMembershipAudit` entry

### Dimension 5: Scoring Independence & Mathematical Correctness (DEC-0001, Conflicts #1 & #3, §53-F, §53-G)
**Invariants to Check**:
- **Confidence Formula** (`backend/staymad/confidence/` vs `config/confidence.yaml`):
  - 5 components: `source_quality (0.30) + corroboration (0.25) + claim_consistency (0.20) + official_confirmation (0.15) + temporal_consistency (0.10)`
  - **Weights sum to 1.00**
  - Correctly derives `evidence_status` and `verification_level`
- **Importance Formula** (`backend/staymad/intelligence/` vs `config/importance.yaml`):
  - 5 components: `impact (0.30) + urgency (0.20) + proximity (0.15) + public_importance (0.15) + momentum (0.20)`
  - **Weights sum to 1.00**
- **CRITICAL INVARIANT**: `confidence_score` is **NOT included** in `importance_score` calculation (resolves Conflict #1)
  - Low-confidence events remain visible with "uncertain" badge, never silently deprioritized

### Dimension 6: Timeline Reconstruction, Conflict Detection & Changesets (Addendum §4, §7, §53-E)
**Invariants to Check**:
- **Timeline** (`backend/staymad/timeline/`):
  - Chronological ordering
  - Timezone conversion to `Asia/Jakarta` (WIB)
  - Preservation of qualifiers ("sekitar", "diperkirakan")
- **Conflict Detection** (`backend/staymad/events/conflicts.py`):
  - Numeric conflict detection (e.g., 5 vs 7 subdistricts)
  - Resolution via official updates
- **Changesets** (`EventSnapshot` and `EventChange`):
  - Track semantic deltas: `ADDED`, `UPDATED`, `CORRECTED`, `RETRACTED`
  - Linked to `evidence_claim_ids`
  - Wording-only reprocessing produces **ZERO changesets** (test_acc_05b)

### Dimension 7: Gemini Synthesis & Structured Output Grounding (ADR-007, DEC-0008, §53-C)
**Invariants to Check**:
- **Gemini Call Type 3 (Synthesize)**: Narrative bullets (`what_happened`, `why_it_matters`, `who_is_affected`, `what_is_unknown`) STRICTLY link to valid `evidence_claim_ids`
- Gemini chain-of-thought is **NEVER requested or leaked**

### Dimension 8: OpenAPI 3.1 & Acceptance Matrix Verification (docs/contracts/openapi.yaml, docs/acceptance-matrix.md)
**Invariants to Check**:
- **9 REST endpoints** exist and match OpenAPI specification:
  1. `GET /events`
  2. `GET /events/{id}`
  3. `GET /events/{id}/timeline`
  4. `GET /events/{id}/sources`
  5. `GET /events/{id}/changes`
  6. `GET /events/{id}/analysis`
  7. `GET /events/{id}/processing`
  8. `GET /locations`
  9. `GET /health` (+ `/healthz`)
- **Asynchronous query design**: Page loads NEVER block on Gemini calls
- **Blind evaluation isolation**: `eval/gold/test/` NEVER imported or modified by application code
- **Standard verification command**: `make lint && make test && make eval-baseline` (all passing)

---

## 5. CONFIDENCE FORMULA (5 Components, Sum = 1.00)

From `config/confidence.yaml` and ADR-004:

```
confidence_score = w_source_quality        * source_quality_score       (0.30)
                 + w_corroboration         * corroboration_score        (0.25)
                 + w_claim_consistency     * claim_consistency_score    (0.20)
                 + w_official_confirmation * official_confirmation_score(0.15)
                 + w_temporal_consistency  * temporal_consistency_score (0.10)
```

**Sum**: 0.30 + 0.25 + 0.20 + 0.15 + 0.10 = **1.00** ✓

**Thresholds** (UNCALIBRATED — starting estimate):
- `high`: 0.70 (confidence_score ≥ 0.70 → bucket HIGH)
- `medium`: 0.45 (0.45 ≤ score < 0.70 → bucket MEDIUM)
- `low`: score < 0.45 → bucket LOW

**Note**: Per DEC-0008, `verbatim_quote_match` is extraction validation gate, NOT confidence component. `recency_decay` captured in urgency, NOT confidence.

---

## 6. IMPORTANCE FORMULA (5 Components, Sum = 1.00)

From `config/importance.yaml` and DEC-0008:

```
importance_score = w_impact          * impact_score              (0.30)
                 + w_urgency         * urgency_score             (0.20)
                 + w_proximity       * proximity_score           (0.15)
                 + w_public_importance * public_importance_score (0.15)
                 + w_momentum        * momentum_score            (0.20)
```

**Sum**: 0.30 + 0.20 + 0.15 + 0.15 + 0.20 = **1.00** ✓

**CRITICAL**: `confidence_score` is **NOT** a component (resolves decisions.md Conflict #1).

**Thresholds** (UNCALIBRATED):
- `high`: 0.70 (importance_score ≥ 0.70 → NEED TO KNOW)
- `medium`: 0.40 (0.40 ≤ score < 0.70 → MEDIUM)
- `informational`: score < 0.40 → INFORMATIONAL

---

## 7. RESOLVER TIER 2 WEIGHTS (Composite Score)

From ADR-005:

```
composite_score = w_semantic * semantic_similarity    (0.40)
                + w_time     * time_similarity        (0.30)
                + w_location * location_similarity    (0.20)
                + w_entity   * entity_overlap         (0.10)
```

**Sum**: 0.40 + 0.30 + 0.20 + 0.10 = **1.00** ✓

---

## 8. THE 16 CANONICAL SQLALCHEMY ENTITIES

From ADR-003 and `backend/staymad/db/models/__init__.py`:

1. **`Source`** — News source metadata, tier, family
2. **`Article`** — Article metadata container
3. **`ArticleVersion`** — Immutable article capture snapshot
4. **`Claim`** — Atomic source-grounded assertion with embedding (768-dim)
5. **`Location`** — Geographic entity (hierarchical: city/province/country/continent/world)
6. **`Event`** — Canonical event identity container
7. **`EventSnapshot`** — Immutable published event representation with embedding (768-dim)
8. **`EventClaim`** — Association: Event ↔ Claim with role
9. **`EventChange`** — Structured change record between snapshots
10. **`EventMembershipAudit`** — Resolution decision audit trail per article
11. **`TimelineEntry`** — Chronological event timeline item
12. **`Conflict`** — Explicit conflict record between claims
13. **`Action`** — Actionability recommendation with source gating
14. **`ProcessingRun`** — Provenance metadata record
15. **`ProcessingJob`** — Work queue unit (async job state machine)
16. **`EventRelation`** — Event-to-event relationships (table exists, not used until UI need visible)

---

## 9. THE 9 REST ENDPOINTS (OpenAPI 3.1)

From `docs/contracts/openapi.yaml`:

1. **`GET /events`** — List published events (EventSnapshot latest per event), filters: category, location, data_mode, pagination
2. **`GET /events/{id}`** — Event detail (summary narrative, confidence, importance, actions)
3. **`GET /events/{id}/timeline`** — Chronological timeline entries with WIB display + qualifiers
4. **`GET /events/{id}/sources`** — Source article list, grouped by `source_family`, with original URLs
5. **`GET /events/{id}/changes`** — Change set between snapshots (What Changed)
6. **`GET /events/{id}/analysis`** — Conflict records, confidence signals, claim summary
7. **`GET /events/{id}/processing`** — Screen 3 "Processing & Evidence" transparency view (NO chain-of-thought)
8. **`GET /locations`** — Geographic reference list for UI filters
9. **`GET /health`** (+ `/healthz`) — Health check, startup validation, mode status

**Async Query Design**: All endpoints read persisted, validated data. Page loads **NEVER** wait for Gemini.

---

## 10. ACCEPTANCE TEST SCENARIOS (test_acc_01 through test_acc_08b)

From `docs/acceptance-matrix.md` (Addendum §11):

| ID | Scenario | Description | Test Articles | Status |
|----|----------|-------------|---------------|--------|
| **test_acc_01** | Syndication & Source Family Grouping | Detect duplicate/syndicated articles, group `source_family: TRANSMEDIA`, prevent consensus inflation | `art_demo_03`, `04`, `13`, `16`, `21`, `22` | Verified Baseline |
| **test_acc_02** | Canonical Event & Timeline | Multi-source reports → 1 canonical event with source-linked claims, preserved time qualifiers, chronological timeline | `art_demo_01`, `08`, `09`, `10`, `14`, `15`, `19`, `20`, `23` | Verified Baseline |
| **test_acc_03** | Hard Constraints (Time/Location) | Prevent false merge on similar reports at different times (>72h) or locations (Jakarta Barat vs Jakarta Timur) → `SEPARATE_EVENT` | `art_demo_06` | Verified Baseline |
| **test_acc_04** | Number Conflict Detection | Detect factual conflicts (5 vs 7 districts) without unilateral choice → mark `evidence_status = CONFLICTING` | `art_demo_01` (5) vs `art_demo_02` (7) | Verified Baseline |
| **test_acc_05a** | Official Update & Change Set | Official update triggers `EventSnapshot v2` + structured `EventChange` (What Changed), resolves prior conflicts, handles retractions | `art_demo_05`, `11`, `12`, `17`, `18` | Verified Baseline |
| **test_acc_05b** | Negative: Wording-Only Reprocessing | Wording-only reprocessing produces **ZERO** `EventChange` records (`no-change specificity = 1.00`) | Wording-only sub-fixture Cluster A | Verified Baseline (PASSED) |
| **test_acc_06** | Prompt Injection & Unsupported Action | Treat article text as untrusted input; reject malicious instructions; reject `ACTION_REQUIRED` without official authority | `art_demo_07` | Passing |
| **test_acc_07a** | Multi-Event Article & Cross-Domain Isolation | Separate and attribute claims discussing two different agendas/issues within one article → correct events without mixing | `art_demo_23` | Verified Baseline |
| **test_acc_07b** | UI Views in Live, Demo, Degraded Modes | All views (Overview, Detail, Sources, Timeline, Changes, Transparency) function consistently in demo/live/degraded modes with honest error/empty states | All event snapshots & fixture UI | Passing |
| **test_acc_08a** | Evaluator Report Artifact Produced | Running evaluator (`make eval-baseline`) generates report artifact in `eval/reports/` with `report_id` and full trace | Fixtures & dev/test gold sets | Verified Baseline |
| **test_acc_08b** | Zero Hardcoded Metrics Contract | No fake metrics/UI traces displayed in README or UI without direct reference to official report artifact file | Repository & UI audit | Planned |

**Extra Fixture Cases** (EX-01 through EX-10): See `docs/acceptance-matrix.md` §2.

---

## 11. TIER-1 OFFICIAL SOURCES (ACTION_REQUIRED/ACTION_RECOMMENDED)

From ADR-006 and DEC-0004:

**Authorized `source_family` for actionable alerts**:
1. **`GOV_BMKG`** — Meteorology, Climatology, and Geophysics Agency
2. **`GOV_BPBD_DKI`** — Regional Disaster Management Agency (DKI Jakarta)
3. **`GOV_BNPB`** — National Disaster Management Agency
4. **`GOV_SETKAB`** — Cabinet Secretariat of the Republic of Indonesia

**Tier-2 Media Attribution Rule** (per ADR-006 user decision):
- Media Tier 2 (Tempo.co, Kompas.com, CNBC Indonesia) quoting official statements **CAN qualify** for action attribution

**Target Metric**: `unsupported_action_rate = 0.00`

---

## 12. ADDITIONAL HARD RULES & INVARIANTS

### From AGENTS.md:
- **No changing schema, enum, score, source policy, or public API without ADR**
- **No hard-coded UI numbers, fake traces, or fake Gemini results**
- **Production mode cannot use fixture adapter** (startup must fail)
- **All article/RSS text = untrusted data, not instructions**
- **Never read/modify `eval/gold/` during blind evaluation**
- **Never change tests to pass; change code, or propose ADR**
- **Never request or display Gemini chain-of-thought**

### Standard Verification Command:
```bash
make lint && make test && make eval-baseline
```

All three must pass before advancing stages.

### Handoff Requirements:
At end of task, write `docs/handoffs/NN-<stage>.md` with:
- Files changed
- Commands + output
- Acceptance evidence
- Open risks
- Decisions needing review

---

## 13. KEY CONFLICTS RESOLVED

From `decisions.md`:

| # | Master Spec | Addendum | Resolution |
|---|-------------|----------|------------|
| **1** | Importance includes Confidence 10% and Urgency 20% (§21) | Importance, urgency, confidence separate; high-impact but uncertain events must not be silently deprioritized (§5) | Calculate importance WITHOUT confidence. Display confidence and urgency as separate fields. Low-confidence events marked "uncertain", not down-ranked. Weights in `config/importance.yaml`. |
| **2** | Example action: "Check on vulnerable family members" (§22) | ACTION REQUIRED/RECOMMENDED must have official source; safety advice not fabricated (§5.6) | Master example violates Addendum contract. Fixtures only contain officially-sourced actions (BMKG/BPBD/etc). Used as negative test case. |
| **3** | Confidence = HIGH/MEDIUM/LOW (§19) | `confidence_score` numeric + `evidence_status` + `verification_level` + enums CONFIRMED/SUPPORTED/UNCONFIRMED/CONFLICTING/UNKNOWN | Three overlapping enum sets. ADR-004: `confidence_score` numeric is source of truth. HIGH/MEDIUM/LOW are display buckets with thresholds in config. CONFIRMED…UNKNOWN derived from `evidence_status` + `verification_level` via mapping table. |
| **7** | Screen 3 named "AI Reasoning / Transparency" | Named "Processing & Evidence" and must NOT show chain-of-thought | Use Addendum name. Master Spec §39 has only 7 endpoints; add `GET /events/{id}/processing` and `GET /health` via ADR and OpenAPI. |

---

## 14. GEMINI CALL TYPES

From Addendum §5, §6, ADR-007:

1. **Call Type 1 — Extract**: Article → structured claims (atomic assertions with source, span, confidence, language, temporal qualifier)
2. **Call Type 2 — Adjudicate**: Candidate pair + Tier 1+2 signals → resolution decision (`SAME_EVENT | RELATED_EVENT | SEPARATE_EVENT | NEEDS_REVIEW`) with reason codes
3. **Call Type 3 — Synthesize**: Event + evidence claims → narrative bullets (`what_happened`, `why_it_matters`, `who_is_affected`, `what_is_unknown`) with `evidence_claim_ids`

**Model**: `gemini-2.0-flash` for all 3 types  
**Embedding Model**: `text-multilingual-embedding-002` (768-dim)

**Chain-of-Thought**: **NEVER** requested or displayed (Addendum §5.8)

---

## 15. 23-ARTICLE SEED FIXTURE

From `eval/fixtures/seed_demo_23.json` and `docs/handoffs/00-delivery-framing.md`:

**4 Clusters covering 3 MVP categories**:

| Cluster | Topic | Articles | Category |
|---------|-------|----------|----------|
| **A** | Jakarta Timur Flooding (Ciliwung overflow) | 8 | `disaster_and_weather` |
| **B** | Mount Merapi Activity Increase | 5 | `disaster_and_weather` |
| **C** | KRL Signaling Disruption (Manggarai) | 4 | `transportation_and_infrastructure` |
| **D** | Presidential Regulation on Transport Subsidy | 6 | `government_and_public_policy` |
| **TOTAL** | | **23** | 3 categories (per DEC-0002, DEC-0007) |

**Edge Cases Covered**: 16 critical types including syndication_duplicate, number_conflict, official_update, retraction, relative_time, malicious_prompt_injection, multi_event_article, different_day_similar_event, hard_constraints_isolation, action_policy_violation, etc.

---

## 16. DEPLOYMENT & CLOUD RUN REQUIREMENTS

From ADR-002, Addendum §9:

- **Container**: Docker
- **Registry**: Artifact Registry
- **Runtime**: Cloud Run
- **Database**: Cloud SQL (PostgreSQL 15 + pgvector 0.7+)
- **Secrets**: Google Cloud Secret Manager
- **Required Secrets**:
  - `GEMINI_API_KEY`
  - `DATABASE_URL`
  - `GEMINI_MODEL=gemini-2.0-flash`
  - `EMBEDDING_MODEL=text-multilingual-embedding-002`
- **Health Check**: `GET /health` returns HTTP 503 if:
  - Database disconnected
  - `fixture_mode = true` in production
  - `GEMINI_API_KEY` invalid in production

---

## 17. ACCEPTANCE CRITERIA (from Master Spec §51, Addendum §13)

Prototype complete ONLY if:

### Data
- [x] News sources can be ingested
- [x] Articles normalized
- [x] Duplicate articles detected

### AI
- [x] Gemini actually integrated
- [x] Claims extracted
- [x] Events resolved
- [x] Timeline generated
- [x] Conflicts detected
- [x] Impact generated
- [x] Actionability determined

### Product
- [x] Daily overview works
- [x] Event detail works
- [x] Timeline works
- [x] What Changed works
- [ ] Geographic filtering works (planned Stage 07)
- [x] Sources visible
- [x] Confidence visible
- [x] AI reasoning can be inspected

### Infrastructure
- [x] Application runs locally
- [ ] Application containerized (planned Stage 07)
- [x] Gemini credentials secure
- [ ] Deployed to Google Cloud (planned Stage 07)
- [ ] Cloud Run deployment works (planned Stage 07)
- [ ] Public URL works (planned Stage 07)

### Competition
- [x] Core innovation immediately understandable
- [x] AI contribution demonstrable
- [x] Demo reproducible
- [x] No fabricated metrics
- [x] Known limitations documented

---

## 18. MODULE-BY-MODULE AUDIT CHECKLIST

| Module | Path | Key Contracts | Verification Commands |
|--------|------|---------------|----------------------|
| **DB Models** | `backend/staymad/db/models/` | 16 entities, ADR-003, pgvector 768-dim | `make test -k test_db_models` |
| **Ingest** | `backend/staymad/ingest/` | Source allowlist, dedup, normalization | `make test -k test_ingest` |
| **Normalize** | `backend/staymad/normalize/` | Content-hash, timezone, language | `make test -k test_normalize` |
| **LLM** | `backend/staymad/llm/` | Gemini client, structured output, schema versioning | `make test -k test_llm_adapter` |
| **Claims** | `backend/staymad/claims/` | Call Type 1 Extract, grounding safety | `make test -k test_grounding_safety` |
| **Resolver** | `backend/staymad/resolver/` | 3-tier pipeline, transitive guard, ablation | `make test -k test_resolver` |
| **Timeline** | `backend/staymad/timeline/` | Chronological order, WIB conversion, qualifiers | `make test -k test_timeline` |
| **Events** | `backend/staymad/events/` | Snapshot, changeset, conflict detection | `make test -k test_changeset test_conflicts` |
| **Confidence** | `backend/staymad/confidence/` | 5-component formula, sum=1.00, ADR-004 | `make test -k test_scoring` |
| **Intelligence** | `backend/staymad/intelligence/` | 5-component importance, separate from confidence | `make test -k test_scoring` |
| **API** | `backend/staymad/api/routers/` | 9 endpoints, OpenAPI 3.1, async query | `make test -k test_acceptance_matrix` |
| **Tests** | `backend/tests/` | 89 tests passing, acceptance matrix coverage | `make test` |

---

## 19. STAGE COMPLETION STATUS (Stages 00–06)

| Stage | Name | Status | Handoff Report | Key Deliverables |
|-------|------|--------|----------------|------------------|
| **00** | Delivery Framing | ✅ COMPLETED | `docs/handoffs/00-delivery-framing.md` | 23-article seed, DEC-0007, acceptance-matrix.md |
| **01** | Architecture | ✅ COMPLETED | `docs/handoffs/01-architecture.md` | ADRs 001-008, architecture docs |
| **02** | Data Foundation | ✅ COMPLETED | `docs/handoffs/02-data-foundation.md` | 16 DB models, Alembic migration, fixtures |
| **03** | Ingestion & Extraction | ✅ COMPLETED | `docs/handoffs/03-ingestion-and-extraction.md` | Gemini Extract, claim pipeline, grounding safety |
| **04** | Event Resolution | ✅ COMPLETED | `docs/handoffs/04-event-resolution.md` | 3-tier resolver, transitive guard, ablation config |
| **05** | Intelligence & Synthesis | ✅ COMPLETED | `docs/handoffs/05-intelligence-and-synthesis.md` | Confidence, importance, timeline, conflict, synthesis |
| **06** | API & Acceptance | ✅ COMPLETED | `docs/handoffs/06-api-and-acceptance.md` | 9 FastAPI endpoints, 89 tests passing, eval-baseline |
| **07** | Frontend UI | 🔜 NEXT | — | Next.js, 3 screens, geographic filtering |

---

## 20. RISK REGISTER (from handoff reports)

| Risk ID | Description | Mitigation | ADR Ref |
|---------|-------------|------------|---------|
| **RSK-06** | False merge risk in event resolution | Default-to-separate, hard constraints, transitive guard | ADR-005 |
| **RSK-12** | Gold set leakage | Path isolation, CI grep check, blind evaluator runner | ADR-008 |
| **RSK-13** | Schema instability across agents | Schema changes require ADR + migration | ADR-003 |
| **RSK-14** | Deployment cold start (Cloud Run) | Next.js SSR tuning, keep-alive health check | ADR-002 |

---

## 21. VERIFICATION SUMMARY (Stage 06 Completion)

### Commands Run:
```bash
make lint      # ✅ All checks passed, 90 files formatted
make test      # ✅ 89 tests passed in 1.12s
make eval-baseline  # ✅ 23 articles, 4 clusters, 10 events, report artifact generated
```

### Test Coverage:
- Unit tests: 77 tests
- Contract tests: 12 tests
- Acceptance tests: 12 tests
- **Total: 89 tests passing**

### Acceptance Matrix:
- ✅ test_acc_01: Syndication grouping
- ✅ test_acc_02: Canonical event + timeline
- ✅ test_acc_03: Hard constraints isolation
- ✅ test_acc_04: Number conflict detection
- ✅ test_acc_05a: Official update changeset
- ✅ test_acc_05b: Wording-only no changeset
- ✅ test_acc_06: Prompt injection safety
- ✅ test_acc_07b: UI mode views
- ✅ test_acc_08a: Report artifact produced

---

## 22. FRONTEND REQUIREMENTS FOR STAGE 07

From `docs/handoffs/06-api-and-acceptance.md` §6:

### Screen 1 — Overview View
- **Endpoints**: `GET /events`, `GET /locations`
- **Features**: Filter by category, location (province/city), data mode; display importance-ranked events

### Screen 2 — Event Detail View
- **Endpoints**: `GET /events/{id}`, `GET /events/{id}/timeline`, `GET /events/{id}/sources`, `GET /events/{id}/changes`, `GET /events/{id}/analysis`
- **Features**: Narrative summary, What Changed, timeline, sources, conflicts, confidence signals, actions

### Screen 3 — Processing & Evidence View
- **Endpoint**: `GET /events/{id}/processing`
- **Features**: Transparency breakdown, 5 confidence components, 5 importance components, audit trail, NO chain-of-thought

### System Status
- **Endpoint**: `GET /health`
- **Features**: Mode indicator (live/demo/degraded), database status, version

### CORS
- Already enabled for `http://localhost:3000` and `http://127.0.0.1:3000`

### Data Contracts
- All response schemas defined in `backend/staymad/api/schemas.py`
- OpenAPI 3.1 spec: `docs/contracts/openapi.yaml`
- Enums: Use lowercase values from OpenAPI spec (e.g., `disaster_and_weather`, not `DISASTER_AND_WEATHER`)

---

**END OF AUTHORITY SUMMARY**

This document serves as the single source of truth for the comprehensive audit of Stay Mad (Stages 00–06). All code verification, invariant checking, and acceptance testing must reference the specifications, decisions, ADRs, and contracts documented herein.
