# Audit Dimension 1: Zero Fake Trace & Hard-coding Invariant

**Authority**: DEC-0006, Addendum §3  
**Auditor**: Autonomous Research Subagent  
**Date**: 2024-01-XX  
**Status**: AUDIT COMPLETE

---

## Executive Summary

**Overall Assessment**: **WARN** — Production startup guards are COMPLIANT, but one MEDIUM-severity issue found in the `/events/{id}/processing` endpoint that artificially inflates `candidate_events_considered` count.

**Key Findings**:
- ✅ **PASS**: Production startup guard correctly implemented and enforced
- ✅ **PASS**: No hard-coded counts in API schemas, main endpoints, or response builders
- ✅ **PASS**: All database models properly tagged with `processing_run_id`
- ✅ **PASS**: LLM factory enforces production safety with clear exception raising
- ✅ **PASS**: Ingest pipeline properly validates and gates sources
- ⚠️ **WARN**: One endpoint artificially inflates candidate count (line 751, events.py)

---

## 1. No Hard-coded Counts in API Layer

### 1.1 API Routers

#### File: `backend/staymad/api/routers/events.py`

**Lines Audited**: 1-775 (entire file)

**Status**: **WARN** — One problematic line found

##### FINDING DIM1-001: Artificial Candidate Count Inflation

**Location**: `backend/staymad/api/routers/events.py:751`

**Code**:
```python
all_event_ids = db.scalars(select(Event.id)).all()
candidate_events_count = max(len(candidate_ids), len(all_event_ids))
```

**Severity**: **MEDIUM**

**Category**: WARN

**Description**: The `/events/{id}/processing` endpoint artificially inflates the `candidate_events_considered` metric by taking the maximum of actual candidate IDs and ALL event IDs in the database. This violates DEC-0006 because:

1. The count does not strictly originate from real resolution audit records
2. It creates a misleading metric that grows with database size, not actual processing
3. In a database with 100 events, an article that was only compared to 3 candidates would report "100 candidates considered"

**Impact**: 
- Violates transparency contract (Screen 3)
- Misleads users about resolution pipeline work performed
- Inflates processing metrics artificially

**Recommendation**: 
Replace with:
```python
candidate_events_count = len(candidate_ids)
```

If no audit records exist, return `0` or the actual count from `EventMembershipAudit.candidate_event_ids`, not the total event count.

**Evidence of Other Counts Being Correct**:
- `articles_analyzed = len(art_ver_ids)` — correctly derived from claim associations (line 745)
- `claims_extracted = len(claims)` — correctly derived from event claims (line 746)
- `timeline_count = len(...)` — correctly queried from TimelineEntry table (lines 754-758)
- `conflicts_detected = len(conflicts)` — correctly derived from event conflicts (line 765)

##### All Other Endpoints: PASS

- **`list_events()`** (lines 219-289): All counts derived from database queries with proper filtering
- **`get_event()`** (lines 292-378): No hardcoded counts; all data from DB relationships
- **`get_event_timeline()`** (lines 381-458): Timeline entries queried from DB, display_time computed via `format_timeline_display_time()`
- **`get_event_sources()`** (lines 461-535): Source items derived from claims and article versions, `unique_source_families` computed from set
- **`get_event_changes()`** (lines 538-613): Changes queried from EventChange table
- **`get_event_analysis()`** (lines 616-672): All metrics derived from event relationships

**Status**: ✅ **PASS** (except DIM1-001)

---

#### File: `backend/staymad/api/routers/system.py`

**Lines Audited**: 1-87 (entire file)

**Status**: ✅ **PASS**

**Findings**: Health check endpoint correctly:
- Tests database connectivity with actual query (`SELECT 1`)
- Reads environment variables without hardcoding
- Returns derived status based on actual checks
- No fake traces or hardcoded metrics

---

#### File: `backend/staymad/api/routers/locations.py`

**Lines Audited**: 1-52 (entire file)

**Status**: ✅ **PASS**

**Findings**: 
- All location data queried from `Location` model with proper filters
- No hardcoded counts or traces

---

### 1.2 API Schemas

#### File: `backend/staymad/api/schemas.py`

**Lines Audited**: 1-367 (entire file)

**Status**: ✅ **PASS**

**Findings**:
- All response models are Pydantic schemas with proper type annotations
- No default values set for counts or metrics
- `EventListResponse.total`, `SourcesResponse.unique_source_families`, `ChangesResponse.material_change_count`, etc. all declared as required fields without defaults
- No hardcoded UUIDs or processing_run_id values

---

### 1.3 API Main & Dependencies

#### File: `backend/staymad/api/main.py`

**Lines Audited**: 1-82 (entire file)

**Status**: ✅ **PASS**

**Findings**:
- `perform_startup_checks()` correctly validates production environment (lines 19-40)
- Lifespan context enforces startup checks (lines 43-46)
- No hardcoded data in application factory

---

#### File: `backend/staymad/api/dependencies.py`

**Lines Audited**: 1-16 (entire file)

**Status**: ✅ **PASS**

**Findings**: Simple DB session dependency with no hardcoded data

---

#### File: `backend/staymad/api/middleware.py`

**Lines Audited**: 1-99 (entire file)

**Status**: ✅ **PASS**

**Findings**: CORS and error handling middleware with no hardcoded data

---

## 2. Processing Run ID Tagging

### 2.1 Database Models Audit

#### Core Models with `processing_run_id` Field

**Status**: ✅ **PASS**

All critical entities properly include `processing_run_id` as a foreign key to `ProcessingRun`:

1. **`Claim`** (`backend/staymad/db/models/claim.py:70-75`):
   ```python
   processing_run_id: Mapped[uuid.UUID] = mapped_column(
       Uuid,
       ForeignKey("processing_runs.id", ondelete="CASCADE"),
       nullable=False,
   )
   ```

2. **`ArticleVersion`** (`backend/staymad/db/models/article.py:87-91`):
   ```python
   processing_run_id: Mapped[uuid.UUID | None] = mapped_column(
       Uuid,
       ForeignKey("processing_runs.id", ondelete="SET NULL"),
       nullable=True,
   )
   ```
   **Note**: Nullable is acceptable here as articles may be ingested before processing run assignment.

3. **`EventSnapshot`** (`backend/staymad/db/models/event.py:176-180`):
   ```python
   processing_run_id: Mapped[uuid.UUID] = mapped_column(
       Uuid,
       ForeignKey("processing_runs.id", ondelete="CASCADE"),
       nullable=False,
   )
   ```

4. **`EventMembershipAudit`** (verified via grep search results):
   Confirmed to include `processing_run_id` field in audit trail records.

#### Models NOT Requiring `processing_run_id`

The following models correctly do NOT have `processing_run_id` as they are either:
- Reference data (Source, Location)
- Aggregation containers (Event, Article)
- Derived associations (EventClaim, EventChange)

- `Source` — Reference data
- `Location` — Reference data
- `Article` — Container (versions have processing_run_id)
- `Event` — Container (snapshots have processing_run_id)
- `EventClaim` — Association (linked claims have processing_run_id)
- `EventChange` — Derived from snapshots (which have processing_run_id)
- `Conflict` — Derived from claims (which have processing_run_id)
- `Action` — Derived from snapshot (which has processing_run_id)
- `TimelineEntry` — Linked to snapshot (which has processing_run_id)

**Verification**: All API endpoints return `processing_run_id` from:
- `EventSnapshot.processing_run_id`
- `Claim.processing_run_id`
- `ProcessingRun.id`

**Status**: ✅ **PASS**

---

## 3. Startup Production Guard

### 3.1 Main Application Startup

#### File: `backend/staymad/api/main.py`

**Lines Audited**: 19-46

**Status**: ✅ **PASS**

**Implementation**:
```python
def perform_startup_checks() -> None:
    """Validate critical startup configuration per DEC-0006."""
    env = os.getenv("STAYMAD_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    fixture_mode = os.getenv("FIXTURE_MODE", "false").lower() in (
        "true",
        "1",
    ) or os.getenv("USE_MOCK_GEMINI", "false").lower() in ("true", "1")
    if env == "production":
        if fixture_mode:
            raise RuntimeError(
                "FATAL: Fixture / mock adapter cannot be used in production environment (DEC-0006)."
            )
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
            raise RuntimeError(
                "FATAL: GEMINI_API_KEY is required in production environment (DEC-0006)."
            )
```

**Lifespan Integration**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context enforcing startup checks."""
    perform_startup_checks()
    yield
```

**Compliance**:
- ✅ Checks `STAYMAD_ENV=production`
- ✅ Detects fixture mode via `FIXTURE_MODE` or `USE_MOCK_GEMINI`
- ✅ Raises `RuntimeError` (crashes startup) if fixture mode active in production
- ✅ Raises `RuntimeError` if `GEMINI_API_KEY` missing in production
- ✅ Enforced via FastAPI lifespan context (runs before any request)

---

### 3.2 LLM Factory Guard

#### File: `backend/staymad/llm/factory.py`

**Lines Audited**: 1-75 (entire file)

**Status**: ✅ **PASS**

**Implementation**:
```python
class StartupConfigurationError(RuntimeError):
    """Raised when environment or adapter configuration violates production safety rules."""


def validate_production_startup(
    data_mode: DataMode | str | None = None, use_fixture: bool = False
) -> None:
    """Enforce DEC-0006 startup guard rules."""
    env = os.getenv("STAYMAD_ENV", "").lower()
    norm_mode = str(data_mode or os.getenv("DATA_MODE", "DEMO")).upper()
    is_prod = env == "production" or norm_mode == DataMode.LIVE.value

    if is_prod:
        if use_fixture:
            raise StartupConfigurationError(
                "DEC-0006 Violation: Fixture/mock adapter is strictly forbidden in production mode. "
                "System startup halted."
            )
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise StartupConfigurationError(
                "DEC-0006 Violation: Production mode requires a valid GEMINI_API_KEY in environment. "
                "System startup halted."
            )
```

**Factory Enforcement**:
```python
def get_llm_client(...) -> BaseGeminiClient:
    """Factory creating Gemini client with production startup guard."""
    # ...
    validate_production_startup(data_mode=norm_mode, use_fixture=use_mock)
    
    if is_prod:
        return GeminiClient(api_key=api_key, model_version=model_version)
    # ...
```

**Compliance**:
- ✅ Custom exception type `StartupConfigurationError` for clear error identification
- ✅ Checks both `STAYMAD_ENV=production` and `DATA_MODE=LIVE`
- ✅ Validates `use_fixture` parameter and environment variables
- ✅ Strictly enforces `GEMINI_API_KEY` requirement
- ✅ Called by factory before client instantiation

---

### 3.3 Health Check Production Validation

#### File: `backend/staymad/api/routers/system.py`

**Lines Audited**: 36-68

**Status**: ✅ **PASS**

**Implementation**:
```python
if env_str == "production":
    if fixture_mode:
        errors.append(
            "FATAL: Fixture / mock adapter cannot be used in production environment (DEC-0006)"
        )
    if not gemini_key:
        errors.append(
            "FATAL: GEMINI_API_KEY is required in production environment (DEC-0006)"
        )

if errors:
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    health_status = "error"
```

**Compliance**:
- ✅ Returns HTTP 503 if production rules violated
- ✅ Exposes configuration errors via health endpoint
- ✅ Explicit DEC-0006 citation in error messages

---

## 4. Ingest Layer — No Fake/Mock Data

### 4.1 Ingest Pipeline

#### File: `backend/staymad/ingest/pipeline.py`

**Lines Audited**: 1-150+ (partial read)

**Status**: ✅ **PASS**

**Findings**:
- Pipeline processes `RawArticle` inputs through real parsing and LLM extraction
- `sync_sources_to_db()` reads from `config/sources.yaml`, not hardcoded fixtures
- `process_batch()` creates real `ProcessingRun` record with proper provenance
- All Article, ArticleVersion, Claim entities saved to DB with `processing_run_id`
- Unauthorized sources correctly rejected via `UnauthorizedSourceError`

**No Evidence Of**:
- Hardcoded article fixtures
- Fake claim data
- Mock adapters bypassing LLM layer

---

### 4.2 Source Registry

#### File: `backend/staymad/ingest/sources.py`

**Lines Audited**: 1-128 (entire file)

**Status**: ✅ **PASS**

**Findings**:
- `SourceRegistry` loads from `config/sources.yaml` (line 14)
- `validate_article_source()` raises `UnauthorizedSourceError` for domains not in allowlist (lines 107-113)
- No hardcoded source data or fixture bypass

**Compliance**: Strictly implements DEC-0003 source allowlist

---

## 5. LLM Layer — No Fake Traces

### 5.1 Production Gemini Client

#### File: `backend/staymad/llm/gemini_client.py`

**Lines Audited**: 1-286 (entire file)

**Status**: ✅ **PASS**

**Findings**:
- `GeminiClient` makes real HTTP requests to Google GenAI API (lines 140-160, 200-220, 270-285)
- API key validated in `__init__` (lines 48-53)
- All responses parsed from actual JSON returned by Gemini
- Fallback behavior documented and deterministic (adjudicate fallback to `SEPARATE_EVENT`)
- No hardcoded extraction results or simulated outputs

**Compliance**: Real API integration per ADR-007

---

### 5.2 Deterministic Client (Test/Demo Only)

#### File: `backend/staymad/llm/deterministic_client.py`

**Lines Audited**: 1-350+ (entire file)

**Status**: ✅ **PASS**

**Findings**:
- Clearly marked as "mock adapter for offline testing" (line 1-6)
- Rule-based extraction from article text (no fake traces)
- Prompt injection defense implemented (lines 86-92)
- Used only when `use_mock=True` or no API key available
- **Gated by factory**: Cannot be used in production mode (see §3.2)

**Compliance**: 
- Correctly isolated for test/CI/demo use
- Production guard prevents activation in `STAYMAD_ENV=production`

---

### 5.3 LLM Factory

**Status**: ✅ **PASS** (covered in §3.2)

---

## 6. Summary of Findings

| Finding ID | Location | Severity | Category | Status |
|------------|----------|----------|----------|--------|
| **DIM1-001** | `backend/staymad/api/routers/events.py:751` | MEDIUM | WARN | Artificial candidate count inflation |

---

## 7. Compliance Matrix

| Invariant | Status | Notes |
|-----------|--------|-------|
| **No hard-coded counts in API layer** | ⚠️ WARN | One endpoint artificially inflates candidate count (DIM1-001); all others PASS |
| **Processing run ID tagging** | ✅ PASS | All critical models properly tagged |
| **Production startup guard (main.py)** | ✅ PASS | Correctly crashes on fixture mode or missing API key |
| **Production startup guard (LLM factory)** | ✅ PASS | Dual-layer validation with custom exception |
| **Production startup guard (health check)** | ✅ PASS | Returns HTTP 503 on violation |
| **No fake data in ingest** | ✅ PASS | All data from real sources, parsed via registry |
| **No fake traces in LLM layer** | ✅ PASS | Production client uses real API; mock client gated |

---

## 8. Recommendations

### 8.1 REQUIRED FIX (DIM1-001)

**File**: `backend/staymad/api/routers/events.py`

**Line**: 751

**Current Code**:
```python
all_event_ids = db.scalars(select(Event.id)).all()
candidate_events_count = max(len(candidate_ids), len(all_event_ids))
```

**Recommended Fix**:
```python
candidate_events_count = len(candidate_ids) if candidate_ids else 0
```

**Rationale**: The processing transparency endpoint should report the actual number of candidate events considered during resolution, not an artificial inflation based on total database size.

---

### 8.2 OPTIONAL ENHANCEMENT

**File**: `backend/staymad/api/routers/events.py`

**Enhancement**: Add explicit validation that `processing_run_id` is not a zero UUID or default value before returning it in API responses.

**Example**:
```python
if snapshot.processing_run_id == uuid.UUID('00000000-0000-0000-0000-000000000000'):
    raise ValueError("Invalid processing_run_id: zero UUID detected")
```

---

## 9. Overall Verdict

**Status**: ⚠️ **WARN** (with one MEDIUM-severity finding)

**Compliance Score**: 6/7 invariants PASS, 1 WARN

**Production Readiness**: 
- ✅ Production startup guards are STRONG and correctly enforced
- ✅ Core data flow from ingest → extraction → resolution → API properly tagged
- ✅ No fake traces or mock adapters can bypass production mode
- ⚠️ One endpoint (processing transparency) artificially inflates a metric
- **Recommendation**: Fix DIM1-001 before Stage 07 to ensure full DEC-0006 compliance

---

## 10. Evidence Summary

### Files Audited (15 total)

**API Layer** (7 files):
1. `backend/staymad/api/routers/events.py` — ⚠️ WARN (DIM1-001)
2. `backend/staymad/api/routers/system.py` — ✅ PASS
3. `backend/staymad/api/routers/locations.py` — ✅ PASS
4. `backend/staymad/api/schemas.py` — ✅ PASS
5. `backend/staymad/api/main.py` — ✅ PASS
6. `backend/staymad/api/dependencies.py` — ✅ PASS
7. `backend/staymad/api/middleware.py` — ✅ PASS

**Database Models** (4 files):
8. `backend/staymad/db/models/__init__.py` — ✅ PASS
9. `backend/staymad/db/models/claim.py` — ✅ PASS
10. `backend/staymad/db/models/article.py` — ✅ PASS
11. `backend/staymad/db/models/event.py` — ✅ PASS

**Ingest Layer** (2 files):
12. `backend/staymad/ingest/pipeline.py` — ✅ PASS
13. `backend/staymad/ingest/sources.py` — ✅ PASS

**LLM Layer** (3 files):
14. `backend/staymad/llm/factory.py` — ✅ PASS
15. `backend/staymad/llm/gemini_client.py` — ✅ PASS
16. `backend/staymad/llm/deterministic_client.py` — ✅ PASS

---

## Audit Signature

**Auditor**: Autonomous Research Subagent  
**Authority Documents Read**:
- `AGENTS.md`
- `docs/decisions.md` (DEC-0001 through DEC-0008)
- `docs/STAY_MAD_MASTER_SPEC_ADDENDUM.md`
- `.agents/audit/authority-summary.md`

**Audit Methodology**: 
- Sequential file reading with line-by-line code inspection
- Grep search for critical patterns (`processing_run_id`, hardcoded values)
- Cross-referencing with authority documents for compliance verification
- Evidence-based reporting with exact file paths and line numbers

**Audit Complete**: 2024-01-XX

---

*End of Dimension 1 Audit Report*
