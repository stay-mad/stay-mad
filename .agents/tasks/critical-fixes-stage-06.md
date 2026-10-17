# Critical Fixes for Stage 06 → Stage 07 Readiness

**Created**: 2026-10-14  
**Authority**: Comprehensive Stage 00-06 Audit Report  
**Blocking**: Stage 07 (Frontend Development)  
**Estimated Total Effort**: 11.5 hours

---

## Context

The comprehensive audit identified 3 CRITICAL issues that must be fixed before advancing to Stage 07 (Frontend). These issues break the evidence grounding contract (§53-C, DEC-0008, Addendum §5) and transparency metrics (DEC-0006).

**Current Status**: 88/100 competition score  
**Target Status**: 92-95/100 after fixes applied

---

## Fix #1: Evidence Grounding Persistence (DIM7-001)

### Severity: 🔴 CRITICAL  
### Estimated Effort: 8 hours  
### Files to Modify:
- `backend/staymad/db/models/event.py` (lines 162-169)
- `backend/staymad/alembic/versions/002_add_evidence_grounding.py` (NEW)
- `backend/staymad/events/manager.py` (line 247)
- `tests/unit/test_event_snapshot.py` (NEW tests)

### Problem
EventSnapshot model stores TEXT for narrative fields (`what_happened`, `why_it_matters`, `who_is_affected`, `conflict_summary`) but does NOT persist the `evidence_claim_ids` returned by Gemini Synthesize. This violates:
- §53-C: "Every narrative bullet strictly links to valid evidence_claim_ids"
- DEC-0008: Source-grounding contract
- Addendum §5.2: "Every factual field must contain one or more evidence_claim_ids"

**Current Implementation** (BROKEN):
```python
# backend/staymad/events/manager.py:247
synthesis_result = await self.gemini_client.synthesize(payload)
# synthesis_result.what_happened.evidence_claim_ids EXISTS but NOT STORED

snapshot = EventSnapshot(
    what_happened=synthesis_result.what_happened.text,  # Only text stored
    # evidence_claim_ids DISCARDED
)
```

### Required Changes

#### Step 1: Update EventSnapshot ORM Model

**File**: `backend/staymad/db/models/event.py` (lines 162-169)

Add JSONB columns for evidence arrays:

```python
class EventSnapshot(Base):
    __tablename__ = "event_snapshots"
    
    # ... existing fields ...
    
    what_happened: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_happened_evidence_claim_ids: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
    
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters_evidence_claim_ids: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
    
    who_is_affected: Mapped[str | None] = mapped_column(Text, nullable=True)
    who_is_affected_evidence_claim_ids: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
    
    conflict_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflict_summary_evidence_claim_ids: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
```

#### Step 2: Create Alembic Migration

**File**: `backend/alembic/versions/002_add_evidence_grounding.py` (NEW)

```python
"""Add evidence grounding to event_snapshots

Revision ID: 002_add_evidence_grounding
Revises: 001_initial_schema
Create Date: 2026-10-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '002_add_evidence_grounding'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add evidence_claim_ids JSONB columns
    op.add_column('event_snapshots', sa.Column(
        'what_happened_evidence_claim_ids', JSONB, nullable=True, server_default='[]'
    ))
    op.add_column('event_snapshots', sa.Column(
        'why_it_matters_evidence_claim_ids', JSONB, nullable=True, server_default='[]'
    ))
    op.add_column('event_snapshots', sa.Column(
        'who_is_affected_evidence_claim_ids', JSONB, nullable=True, server_default='[]'
    ))
    op.add_column('event_snapshots', sa.Column(
        'conflict_summary_evidence_claim_ids', JSONB, nullable=True, server_default='[]'
    ))
    
    # Create GIN indexes for efficient JSONB queries
    op.create_index(
        'idx_snapshot_what_happened_evidence',
        'event_snapshots',
        ['what_happened_evidence_claim_ids'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    op.drop_index('idx_snapshot_what_happened_evidence', table_name='event_snapshots')
    op.drop_column('event_snapshots', 'conflict_summary_evidence_claim_ids')
    op.drop_column('event_snapshots', 'who_is_affected_evidence_claim_ids')
    op.drop_column('event_snapshots', 'why_it_matters_evidence_claim_ids')
    op.drop_column('event_snapshots', 'what_happened_evidence_claim_ids')
```

#### Step 3: Update EventSynthesisManager to Persist Evidence

**File**: `backend/staymad/events/manager.py` (line 247)

```python
async def synthesize_event_snapshot(
    self, event_id: str, processing_run_id: str
) -> EventSnapshot:
    # ... existing code to prepare payload ...
    
    synthesis_result = await self.gemini_client.synthesize(payload)
    
    # FIXED: Store both text AND evidence_claim_ids
    snapshot = EventSnapshot(
        event_id=event_id,
        processing_run_id=processing_run_id,
        
        # What Happened (with evidence)
        what_happened=synthesis_result.what_happened.text if synthesis_result.what_happened else None,
        what_happened_evidence_claim_ids=synthesis_result.what_happened.evidence_claim_ids if synthesis_result.what_happened else [],
        
        # Why It Matters (with evidence)
        why_it_matters=synthesis_result.why_it_matters.text if synthesis_result.why_it_matters else None,
        why_it_matters_evidence_claim_ids=synthesis_result.why_it_matters.evidence_claim_ids if synthesis_result.why_it_matters else [],
        
        # Who Is Affected (with evidence)
        who_is_affected=synthesis_result.who_is_affected.text if synthesis_result.who_is_affected else None,
        who_is_affected_evidence_claim_ids=synthesis_result.who_is_affected.evidence_claim_ids if synthesis_result.who_is_affected else [],
        
        # Conflict Summary (with evidence)
        conflict_summary=synthesis_result.conflict_summary.text if synthesis_result.conflict_summary else None,
        conflict_summary_evidence_claim_ids=synthesis_result.conflict_summary.evidence_claim_ids if synthesis_result.conflict_summary else [],
        
        # ... other fields ...
    )
    
    return snapshot
```

#### Step 4: Add Unit Tests

**File**: `tests/unit/test_event_snapshot.py` (NEW)

```python
import pytest
from staymad.db.models.event import EventSnapshot

def test_evidence_grounding_persistence():
    """Test that evidence_claim_ids are persisted to EventSnapshot."""
    snapshot = EventSnapshot(
        event_id="evt_123",
        processing_run_id="run_456",
        what_happened="Banjir melanda 7 kecamatan di Jakarta Timur",
        what_happened_evidence_claim_ids=["claim_001", "claim_002", "claim_007"],
        why_it_matters="Ribuan warga terdampak dan jalur transportasi utama terputus",
        why_it_matters_evidence_claim_ids=["claim_003", "claim_005"],
    )
    
    assert snapshot.what_happened_evidence_claim_ids == ["claim_001", "claim_002", "claim_007"]
    assert snapshot.why_it_matters_evidence_claim_ids == ["claim_003", "claim_005"]
    assert len(snapshot.what_happened_evidence_claim_ids) == 3

def test_empty_evidence_defaults_to_empty_list():
    """Test that missing evidence_claim_ids defaults to empty list."""
    snapshot = EventSnapshot(
        event_id="evt_123",
        what_happened="Some text without evidence",
    )
    
    assert snapshot.what_happened_evidence_claim_ids == []
```

### Acceptance Criteria
- [ ] Migration `002_add_evidence_grounding.py` runs successfully: `alembic upgrade head`
- [ ] All 4 new JSONB columns exist in `event_snapshots` table
- [ ] EventSnapshot ORM model includes all 4 evidence_claim_ids fields
- [ ] EventSynthesisManager stores evidence arrays from Gemini response
- [ ] Unit tests pass: `pytest tests/unit/test_event_snapshot.py -v`
- [ ] No existing tests broken: `make test` (89/89 still passing)

---

## Fix #2: API Evidence Citation Accuracy (DIM7-002)

### Severity: 🔴 CRITICAL  
### Estimated Effort: 3 hours  
### Files to Modify:
- `backend/staymad/api/routers/events.py` (lines 296-383)
- `backend/staymad/api/schemas.py` (verify EvidenceField schema)
- `tests/e2e/test_api_evidence_accuracy.py` (NEW tests)

### Problem
The `/events/{id}` endpoint fabricates `evidence_claim_ids` by using ALL primary claim IDs for ALL narrative fields, instead of returning the actual evidence grounding stored in EventSnapshot.

**Current Implementation** (BROKEN):
```python
# backend/staymad/api/routers/events.py:296-383
@router.get("/events/{id}")
async def get_event(id: str, db: Session = Depends(get_db)):
    # ... fetch snapshot ...
    
    # WRONG: Uses ALL primary claims for ALL fields
    primary_claim_ids = [str(c.id) for c in event_claims if c.is_primary]
    
    return EventDetailResponse(
        what_happened=EvidenceField(
            text=snapshot.what_happened,
            evidence_claim_ids=primary_claim_ids,  # FABRICATED
        ),
        why_it_matters=EvidenceField(
            text=snapshot.why_it_matters,
            evidence_claim_ids=primary_claim_ids,  # SAME LIST FOR ALL FIELDS
        ),
        # ... all fields use same fabricated list ...
    )
```

### Required Changes

#### Step 1: Update API Endpoint to Use Stored Evidence

**File**: `backend/staymad/api/routers/events.py` (lines 296-383)

```python
@router.get("/events/{id}", response_model=EventDetailResponse)
async def get_event(
    id: str,
    db: Session = Depends(get_db)
) -> EventDetailResponse:
    """Get event detail with accurate evidence citations."""
    
    snapshot = db.query(EventSnapshot).filter(
        EventSnapshot.event_id == id
    ).order_by(EventSnapshot.created_at.desc()).first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    
    # FIXED: Use actual stored evidence_claim_ids
    return EventDetailResponse(
        id=str(snapshot.event_id),
        snapshot_id=str(snapshot.id),
        category=snapshot.category,
        headline=snapshot.headline,
        
        # Use stored evidence arrays (not fabricated)
        what_happened=EvidenceField(
            text=snapshot.what_happened,
            evidence_claim_ids=snapshot.what_happened_evidence_claim_ids or [],
        ),
        why_it_matters=EvidenceField(
            text=snapshot.why_it_matters,
            evidence_claim_ids=snapshot.why_it_matters_evidence_claim_ids or [],
        ),
        who_is_affected=EvidenceField(
            text=snapshot.who_is_affected,
            evidence_claim_ids=snapshot.who_is_affected_evidence_claim_ids or [],
        ),
        conflict_summary=EvidenceField(
            text=snapshot.conflict_summary,
            evidence_claim_ids=snapshot.conflict_summary_evidence_claim_ids or [],
        ),
        
        # ... other fields ...
    )
```

#### Step 2: Remove Fabricated Evidence Logic

Delete lines 296-304 that compute `primary_claim_ids` for fabrication:

```python
# DELETE THIS BLOCK:
# event_claims = db.query(EventClaim).filter(
#     EventClaim.event_id == id
# ).all()
# primary_claim_ids = [str(c.claim_id) for c in event_claims if c.is_primary]
```

#### Step 3: Add E2E Tests

**File**: `tests/e2e/test_api_evidence_accuracy.py` (NEW)

```python
import pytest
from fastapi.testclient import TestClient

def test_api_returns_accurate_evidence_citations(client: TestClient, seeded_db):
    """Test that /events/{id} returns actual stored evidence_claim_ids."""
    
    # Arrange: Get event with known evidence grounding
    event_id = "evt_jakarta_flood_demo"  # From seed fixture
    
    # Act: Call API
    response = client.get(f"/events/{event_id}")
    assert response.status_code == 200
    data = response.json()
    
    # Assert: Evidence arrays are DIFFERENT for different fields
    what_happened_ids = data["what_happened"]["evidence_claim_ids"]
    why_it_matters_ids = data["why_it_matters"]["evidence_claim_ids"]
    
    # These should NOT be identical (different statements have different evidence)
    assert what_happened_ids != why_it_matters_ids, \
        "Evidence arrays should differ across narrative fields"
    
    # Each array should contain only relevant claim IDs
    assert len(what_happened_ids) >= 1, "what_happened must have evidence"
    assert len(why_it_matters_ids) >= 1, "why_it_matters must have evidence"
    
    # Verify claim IDs exist in database
    for claim_id in what_happened_ids:
        assert seeded_db.query(Claim).filter(Claim.id == claim_id).first() is not None

def test_api_evidence_matches_snapshot_storage(client: TestClient, seeded_db):
    """Test that API evidence matches what's stored in EventSnapshot."""
    
    event_id = "evt_jakarta_flood_demo"
    
    # Fetch from API
    api_response = client.get(f"/events/{event_id}").json()
    
    # Fetch from DB
    snapshot = seeded_db.query(EventSnapshot).filter(
        EventSnapshot.event_id == event_id
    ).order_by(EventSnapshot.created_at.desc()).first()
    
    # Assert: API returns exactly what's stored
    assert api_response["what_happened"]["evidence_claim_ids"] == \
        snapshot.what_happened_evidence_claim_ids
    assert api_response["why_it_matters"]["evidence_claim_ids"] == \
        snapshot.why_it_matters_evidence_claim_ids
```

### Acceptance Criteria
- [ ] API endpoint reads `evidence_claim_ids` from EventSnapshot table
- [ ] Different narrative fields have DIFFERENT evidence arrays
- [ ] No fabricated `primary_claim_ids` logic remains
- [ ] E2E tests pass: `pytest tests/e2e/test_api_evidence_accuracy.py -v`
- [ ] OpenAPI contract compliance maintained
- [ ] Existing acceptance tests still pass: `make test`

---

## Fix #3: Candidate Count Inflation (DIM1-001)

### Severity: ⚠️ MEDIUM  
### Estimated Effort: 30 minutes  
### Files to Modify:
- `backend/staymad/api/routers/events.py` (line 751)
- `tests/e2e/test_transparency_metrics.py` (verify test expectations)

### Problem
The `/events/{id}/processing` endpoint artificially inflates `candidate_events_considered` by reporting `max(len(candidate_ids), len(all_event_ids))`, which shows total database size instead of actual candidates evaluated during resolution.

**Current Implementation** (BROKEN):
```python
# backend/staymad/api/routers/events.py:751
all_event_ids = db.query(Event.id).all()
candidate_events_count = max(len(candidate_ids), len(all_event_ids))  # WRONG
```

In a database with 100 events, an article compared to only 3 candidates reports "100 candidates considered" — misleading for Screen 3 transparency.

### Required Change

#### Step 1: Fix Candidate Count Logic

**File**: `backend/staymad/api/routers/events.py` (line 751)

```python
# BEFORE (WRONG):
# all_event_ids = db.query(Event.id).all()
# candidate_events_count = max(len(candidate_ids), len(all_event_ids))

# AFTER (CORRECT):
candidate_events_count = len(candidate_ids) if candidate_ids else 0
```

That's it. One-line fix.

#### Step 2: Verify Test Expectations

**File**: `tests/e2e/test_transparency_metrics.py`

Update test to expect accurate counts:

```python
def test_processing_endpoint_accurate_counts(client: TestClient, seeded_db):
    """Test that /events/{id}/processing reports accurate candidate counts."""
    
    event_id = "evt_jakarta_flood_demo"
    response = client.get(f"/events/{event_id}/processing")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify count matches actual EventMembershipAudit records
    audit_records = seeded_db.query(EventMembershipAudit).filter(
        EventMembershipAudit.event_id == event_id
    ).all()
    
    expected_count = len(audit_records)
    assert data["candidate_events_considered"] == expected_count, \
        f"Expected {expected_count} candidates, got {data['candidate_events_considered']}"
    
    # Should NOT equal total database size
    total_events = seeded_db.query(Event).count()
    if expected_count < total_events:
        assert data["candidate_events_considered"] < total_events, \
            "Candidate count should not inflate to total DB size"
```

### Acceptance Criteria
- [ ] Line 751 fixed to use actual candidate count
- [ ] No reference to total database size in candidate counting
- [ ] Test expectations updated if needed
- [ ] Transparency metrics accurate in demo: `make run-demo` → check Screen 3
- [ ] DEC-0006 compliance verified: all counts from real processing records

---

## Verification Plan

### Step 1: Run Migrations
```bash
cd backend
alembic upgrade head  # Should apply 002_add_evidence_grounding
```

### Step 2: Run Full Test Suite
```bash
make lint      # Should pass (ruff + mypy)
make test      # Should pass 89+ tests
```

### Step 3: Verify Evidence Grounding End-to-End
```bash
# Start backend
make run-backend

# In another terminal, test API
curl http://localhost:8080/events/evt_jakarta_flood_demo | jq '.what_happened'
# Should show: { "text": "...", "evidence_claim_ids": ["claim_001", "claim_007"] }

# Verify different fields have different evidence
curl http://localhost:8080/events/evt_jakarta_flood_demo | jq '.why_it_matters.evidence_claim_ids'
# Should be DIFFERENT from what_happened.evidence_claim_ids
```

### Step 4: Verify Transparency Metrics
```bash
curl http://localhost:8080/events/evt_jakarta_flood_demo/processing | jq '.candidate_events_considered'
# Should show actual count (e.g., 3), NOT total DB size (e.g., 23)
```

### Step 5: Run Acceptance Tests
```bash
pytest tests/e2e/test_acceptance_matrix.py -v
# All 12 acceptance tests should still pass
```

---

## Post-Fix Validation

After all 3 fixes applied, verify:

- [ ] `alembic current` shows `002_add_evidence_grounding`
- [ ] `make test` shows 89+ tests passing (100% pass rate)
- [ ] API `/events/{id}` returns accurate evidence_claim_ids
- [ ] Different narrative fields have DIFFERENT evidence arrays
- [ ] API `/events/{id}/processing` shows accurate candidate count
- [ ] Audit report criteria DIM7-001, DIM7-002, DIM1-001 resolved
- [ ] Competition score improves to 92-95/100 range

---

## Impact on Competition Score

**Before Fixes**: 88/100
- Technical Merit: 36/40 (deductions for evidence gaps)
- Problem Alignment: 23/25 (deductions for grounding contract broken)

**After Fixes**: 92-95/100
- Technical Merit: 39/40 (all core systems functioning correctly)
- Problem Alignment: 25/25 (full transparency & provenance implemented)

**Stage 07 Readiness**: ✅ UNBLOCKED

Frontend can begin with stable, correct API contracts delivering accurate evidence citations and transparency metrics.

---

## Notes for Implementation Agent

**Critical Requirements**:
1. Read audit report first: `.agents/audit/comprehensive-stage-00-06-audit.md`
2. Follow authority hierarchy: ADR > decisions.md > Addendum > Master Spec
3. Do NOT change any other code unrelated to these 3 fixes
4. Run full test suite after each fix to catch regressions
5. Evidence grounding (Fix #1) MUST be completed before Fix #2 (API depends on schema)

**Success Criteria**:
- All 3 fixes applied
- 89+ tests passing
- Evidence citations accurate
- Transparency metrics honest
- DEC-0006, §53-C compliance verified

**Handoff Requirements**:
- Document changes in `docs/handoffs/06b-critical-fixes.md`
- List modified files with line numbers
- Include before/after verification commands
- Report final test results

---

**END OF FIX SPECIFICATION**
