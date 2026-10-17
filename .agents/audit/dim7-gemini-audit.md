# Dimension 7: Gemini Synthesis & Structured Output Grounding Audit

**Audit Date**: 2024-10-14  
**Authority**: ADR-007, DEC-0008, docs/architecture/C-gemini-architecture.md §53-C  
**Scope**: All 3 Gemini call types (Extract, Adjudicate, Synthesize) across LLM module and integration points

---

## Executive Summary

**Overall Status**: ⚠️ **PARTIAL PASS with CRITICAL GAPS**

The Gemini implementation correctly:
- Uses structured output (JSON mode) for all 3 call types ✅
- Implements anti-prompt-injection defenses with data delimiter tags ✅
- Never requests or leaks chain-of-thought reasoning ✅
- Enforces grounding in Gemini synthesis response validation ✅
- Loads API key from environment, never hard-coded ✅

**CRITICAL GAPS IDENTIFIED**:
1. **Evidence grounding is NOT persisted to database** - Gemini Synthesize returns `evidence_claim_ids` for each narrative field, but these are discarded during EventSnapshot persistence
2. **API returns fabricated evidence_claim_ids** - The `/events/{id}` endpoint returns `primary_claim_ids` for ALL narrative fields instead of the actual evidence IDs returned by Gemini
3. **No validation that evidence_claim_ids exist in database** - The synthesis response does not validate that returned claim IDs are actually present in the claims table

---

## 1. Gemini Call Type 3 (Synthesize) Grounding

### 1.1 Structured Output Schema ✅ PASS

**File**: `backend/staymad/llm/schemas.py`

```python
class GroundedNarrativePoint(BaseModel):
    """Factual narrative section strictly grounded by evidence claims."""
    text: str | None = None
    evidence_claim_ids: list[str] = Field(default_factory=list)

class SynthesizeResponse(BaseModel):
    """Validated structured output from Gemini Call Type 3: Synthesize."""
    schema_version: str = "1.0"
    headline: str = Field(..., max_length=150)
    what_happened: GroundedNarrativePoint
    why_it_matters: GroundedNarrativePoint | None = None
    who_is_affected: GroundedNarrativePoint | None = None
    what_is_unknown: GroundedNarrativePoint | None = None
    conflict_summary: GroundedNarrativePoint | None = None
    suggested_actions: list[SuggestedActionItem] = Field(default_factory=list)
    insufficient_evidence: bool = False
```

**Finding**: Schema correctly requires `evidence_claim_ids` for each narrative field.

**Severity**: PASS

---

### 1.2 Gemini Client Grounding Enforcement ✅ PASS (with runtime safety net)

**File**: `backend/staymad/llm/gemini_client.py:248-259`

```python
# Enforce DEC-0008 & §53-C grounding contract:
# what_happened MUST have evidence_claim_ids unless insufficient_evidence
if (
    not response.insufficient_evidence
    and not response.what_happened.evidence_claim_ids
    and payload.claims
):
    # Ground with primary claims if empty
    response.what_happened.evidence_claim_ids = [
        c.claim_id for c in payload.claims if c.role == "PRIMARY"
    ] or [payload.claims[0].claim_id]
```

**Finding**: The GeminiClient includes a safety fallback that automatically grounds `what_happened` with primary claim IDs if Gemini returns an empty list. This is a defensive measure but indicates the system does not trust Gemini to always return evidence_claim_ids.

**Severity**: PASS (defensive programming, but masks potential Gemini grounding failures)

---

### 1.3 System Prompt Requires Grounding ✅ PASS

**File**: `backend/staymad/llm/base.py:82-88`

```python
### GROUNDING & ANTI-HALLUCINATION RULES (DEC-0008, §53-C):
1. Every factual statement in `what_happened`, `why_it_matters`, `who_is_affected`, 
   and `conflict_summary` MUST cite the relevant `evidence_claim_ids`.
2. Do not invent numbers, casualty figures, time estimates, or locations not 
   present in the claims.
3. If information is missing or unclear, state it in `what_is_unknown` 
   (evidence_claim_ids may be empty for unknowns).
```

**Finding**: System prompt explicitly instructs Gemini to ground all narrative with evidence_claim_ids.

**Severity**: PASS

---

### 1.4 Evidence Persistence ❌ CRITICAL FAILURE

**Files**: 
- `backend/staymad/db/models/event.py:162-169`
- `backend/staymad/events/manager.py:240-270`
- `backend/alembic/versions/001_initial_schema.py:343-346`

**Database Schema**:
```python
# EventSnapshot model
what_happened: Mapped[str] = mapped_column(Text, nullable=False)
why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
who_is_affected: Mapped[str | None] = mapped_column(Text, nullable=True)
what_is_unknown: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Migration Schema**:
```python
sa.Column("what_happened", sa.Text(), nullable=False),
sa.Column("why_it_matters", sa.Text(), nullable=True),
sa.Column("who_is_affected", sa.Text(), nullable=True),
sa.Column("what_is_unknown", sa.Text(), nullable=True),
```

**Snapshot Creation** (`backend/staymad/events/manager.py:247`):
```python
new_snapshot = EventSnapshot(
    # ...
    headline=synth_resp.headline,
    what_happened=synth_resp.what_happened.text or "",  # Only text is stored!
    why_it_matters=synth_resp.why_it_matters.text if synth_resp.why_it_matters else None,
    who_is_affected=synth_resp.who_is_affected.text if synth_resp.who_is_affected else None,
    what_is_unknown=synth_resp.what_is_unknown.text if synth_resp.what_is_unknown else None,
    # ...
)
```

**Finding**: 
- The `SynthesizeResponse` schema includes `evidence_claim_ids` for each `GroundedNarrativePoint`
- Gemini returns these IDs in the structured JSON response
- **BUT** the EventSnapshot database table only stores TEXT fields, not evidence_claim_ids
- **AND** the EventSnapshot ORM model does not have fields for evidence_claim_ids
- **AND** the snapshot creation code only extracts `.text`, discarding `.evidence_claim_ids`

**Impact**: The grounding contract is BROKEN at the persistence layer. The database does not record which claims support which narrative statements.

**Severity**: 🔴 **CRITICAL FAILURE**

---

### 1.5 API Response Fabricates Evidence IDs ❌ CRITICAL FAILURE

**File**: `backend/staymad/api/routers/events.py:296-383`

```python
# Lines 296-304: Gather ALL primary/supporting claims for the event
primary_claim_ids = [
    ec.claim_id
    for ec in event.event_claims
    if ec.role in (EventClaimRole.PRIMARY, EventClaimRole.SUPPORTING)
]
if not primary_claim_ids:
    primary_claim_ids = [ec.claim_id for ec in event.event_claims]

# Lines 367-383: Use same primary_claim_ids for ALL narrative fields
what_happened=EvidenceField(
    text=snapshot.what_happened,
    evidence_claim_ids=primary_claim_ids,  # Same IDs for all fields!
),
why_it_matters=EvidenceField(
    text=snapshot.why_it_matters,
    evidence_claim_ids=primary_claim_ids,  # Same IDs!
) if snapshot.why_it_matters else None,
who_is_affected=EvidenceField(
    text=snapshot.who_is_affected,
    evidence_claim_ids=primary_claim_ids,  # Same IDs!
) if snapshot.who_is_affected else None,
```

**Finding**: The API endpoint constructs `EvidenceField` responses by:
1. Gathering ALL primary/supporting claim IDs from the event (not specific to each narrative field)
2. Using the SAME list of claim IDs for `what_happened`, `why_it_matters`, `who_is_affected`

This is NOT the actual evidence grounding returned by Gemini. The API is fabricating evidence citations.

**Expected Behavior**: Each narrative field should cite ONLY the claims that directly support that specific statement, as returned by Gemini's structured output.

**Actual Behavior**: All narrative fields cite all primary claims, regardless of actual relevance.

**Severity**: 🔴 **CRITICAL FAILURE** - Violates DEC-0008 grounding contract

---

### 1.6 No Validation of Evidence Claim IDs Against Database ⚠️ HIGH

**File**: `backend/staymad/llm/gemini_client.py:210-259`

**Finding**: The `synthesize()` method in `GeminiClient`:
1. Receives a `SynthesizeResponse` from Gemini with `evidence_claim_ids`
2. Validates the JSON structure via Pydantic
3. **DOES NOT** validate that the claim IDs in `evidence_claim_ids` actually exist in the `claims` table or match the input `payload.claims`

**Risk**: Gemini could hallucinate claim IDs that don't exist. The system would persist these invalid references without detection.

**Mitigation Present**: The fallback grounding (§1.2) uses claim IDs from the input payload, which are guaranteed to exist.

**Severity**: ⚠️ **HIGH** - No validation that Gemini-returned claim IDs are valid

---

## 2. Chain-of-Thought Never Requested or Leaked

### 2.1 No Chain-of-Thought in Prompts ✅ PASS

**Files Checked**:
- `backend/staymad/llm/base.py` (all 3 system prompts)
- `backend/staymad/llm/gemini_client.py` (all 3 API calls)

**Search Results**: No occurrences of:
- `"think step by step"`
- `"let's think"`
- `"chain of thought"`
- `"reasoning:"`
- `"scratchpad"`

**Finding**: System prompts contain factual extraction/adjudication/synthesis instructions but never request chain-of-thought reasoning.

**Severity**: ✅ PASS

---

### 2.2 No Thinking Tokens Requested ✅ PASS

**Files Checked**: `backend/staymad/llm/gemini_client.py`

**API Configuration** (Extract, line 75-78):
```python
"generationConfig": {
    "temperature": 0.0,
    "response_mime_type": "application/json",
    "response_schema": response_schema,
    "max_output_tokens": 2048,
}
```

**Finding**: No parameters request thinking tokens or extended thinking:
- No `thinking_tokens` parameter
- No `extended_thinking` parameter
- Only structured JSON output is configured

**Severity**: ✅ PASS

---

### 2.3 No Reasoning Content Extracted or Exposed ✅ PASS

**Files Checked**:
- `backend/staymad/llm/gemini_client.py` (response parsing)
- `backend/staymad/api/routers/events.py` (API responses)

**Response Parsing** (Extract, line 99-108):
```python
candidates = result_json.get("candidates", [])
if not candidates:
    raise GeminiAPIError(f"No candidates returned by Gemini: {result_json}")

part_text = candidates[0]["content"]["parts"][0]["text"]
parsed_data = json.loads(part_text)

# Ensure article_version_id is set
parsed_data["article_version_id"] = article.article_version_id
return ExtractResponse(**parsed_data)
```

**Finding**: 
- Response parsing only extracts the structured JSON text
- No additional fields are read or exposed
- Chain-of-thought reasoning (if present) would be ignored

**Severity**: ✅ PASS

---

## 3. Gemini Call Types Verification

### 3.1 Call Type 1: Extract ✅ PASS

**File**: `backend/staymad/llm/gemini_client.py:55-108`

**Implementation**:
- ✅ Uses `response_mime_type: application/json` with Pydantic schema
- ✅ Temperature 0.0 (deterministic)
- ✅ Validates `ExtractResponse` schema
- ✅ Encloses article text in `<article_content>` delimiter tags
- ✅ Escapes delimiter breakout attempts

**Severity**: ✅ PASS

---

### 3.2 Call Type 2: Adjudicate ✅ PASS

**File**: `backend/staymad/llm/gemini_client.py:110-187`

**Implementation**:
- ✅ Uses `response_mime_type: application/json` with Pydantic schema
- ✅ Temperature 0.1
- ✅ Validates `AdjudicateResponse` schema
- ✅ Encloses candidate text in `<candidate_content>` delimiter tags
- ✅ Applies safety override: `SAME_EVENT` with confidence < 0.60 → `NEEDS_REVIEW`
- ✅ Fallback: defaults to `SEPARATE_EVENT` on API failure (safe failure mode)

**Severity**: ✅ PASS

---

### 3.3 Call Type 3: Synthesize ✅ PASS (implementation) / ❌ FAIL (persistence)

**File**: `backend/staymad/llm/gemini_client.py:189-259`

**Implementation**:
- ✅ Uses `response_mime_type: application/json` with Pydantic schema
- ✅ Temperature 0.2
- ✅ Validates `SynthesizeResponse` schema
- ✅ Encloses claims in `<claims_data>` delimiter tags
- ✅ Enforces grounding: auto-fills empty `what_happened.evidence_claim_ids`
- ❌ But evidence_claim_ids are NOT persisted to database (see §1.4)

**Severity**: ⚠️ **MIXED** - Implementation correct, but grounding is lost downstream

---

## 4. Structured Output Schema

### 4.1 Pydantic Models for All Call Types ✅ PASS

**File**: `backend/staymad/llm/schemas.py`

**Finding**: All 3 call types use Pydantic v2 models:
- `ExtractResponse` (line 62-72)
- `AdjudicateResponse` (line 163-172)
- `SynthesizeResponse` (line 254-263)

Models are converted to JSON Schema via `.model_json_schema()` and passed to Gemini API.

**Severity**: ✅ PASS

---

### 4.2 Schema Validation on Response ✅ PASS

**Files**: `backend/staymad/llm/gemini_client.py`

**Finding**: All 3 call types validate Gemini's JSON response using Pydantic:
- Extract (line 107): `ExtractResponse(**parsed_data)`
- Adjudicate (line 163): `AdjudicateResponse(**parsed_data)`
- Synthesize (line 241): `SynthesizeResponse(**parsed_data)`

Pydantic raises `ValidationError` if schema doesn't match, preventing invalid data from entering the system.

**Severity**: ✅ PASS

---

## 5. API Key Safety

### 5.1 API Key Loaded from Environment ✅ PASS

**File**: `backend/staymad/llm/gemini_client.py:30-37`

```python
def __init__(
    self,
    api_key: str | None = None,
    model_version: str | None = None,
    prompt_version: str = PROMPT_VERSION_EXTRACT,
    schema_version: str = SCHEMA_VERSION_EXTRACT,
) -> None:
    resolved_key = api_key or os.getenv("GEMINI_API_KEY")
    if not resolved_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is missing. "
            "Real GeminiClient requires a valid API key."
        )
    self.api_key = resolved_key
```

**Finding**: 
- API key is loaded from `GEMINI_API_KEY` environment variable
- Raises `ValueError` at initialization if missing
- Never hard-coded in source code

**Severity**: ✅ PASS

---

### 5.2 Startup Guard for Production Mode ✅ PASS (verified separately)

**File**: This is verified in Dimension 1 audit (Zero Hard-coding Invariant)

**Finding**: Startup validation in `backend/staymad/api/main.py` ensures:
- In production mode, `GEMINI_API_KEY` must be valid
- Mock/fixture adapters cannot be active in production
- System crashes at startup if these conditions are violated

**Severity**: ✅ PASS (cross-reference to Dimension 1)

---

## 6. Contract Tests Verification

### 6.1 Extract Contract Tests ✅ PASS

**File**: `backend/tests/contract/test_gemini_extract_contract.py`

**Tests**:
- ✅ JSON schema structure validation
- ✅ `source_span` max 200 characters enforcement
- ✅ Deterministic client extract contract
- ✅ Valid JSON wire format serialization

**Severity**: ✅ PASS

---

### 6.2 Adjudicate Contract Tests ✅ PASS

**File**: `backend/tests/contract/test_gemini_adjudicate_contract.py`

**Tests**:
- ✅ JSON schema structure validation
- ✅ Confidence bounds (0.0-1.0) enforcement
- ✅ Deterministic cache key generation
- ✅ Deterministic client adjudicate contract
- ✅ Low-confidence override rule (`SAME_EVENT` + confidence < 0.60 → `NEEDS_REVIEW`)

**Severity**: ✅ PASS

---

### 6.3 Synthesize Contract Tests ⚠️ PARTIAL PASS

**File**: `backend/tests/contract/test_gemini_synthesize_contract.py`

**Tests**:
- ✅ Schema conformance (line 14-23)
- ✅ Grounded response generation with claim citations (line 26-89)
- ✅ Insufficient content handling (line 92-101)
- ✅ Cache key determinism (line 104-118)

**Gap**: Tests verify that `DeterministicGeminiClient` returns `evidence_claim_ids`, but do NOT verify:
1. That these IDs are persisted to database
2. That API responses return the correct evidence IDs (not fabricated ones)

**Test at line 68-70**:
```python
assert len(resp.what_happened.evidence_claim_ids) > 0
assert cid1 in resp.what_happened.evidence_claim_ids
```

This verifies the Gemini response schema, but NOT the end-to-end grounding contract.

**Severity**: ⚠️ **PARTIAL PASS** - Tests validate response schema but not persistence/retrieval

---

## 7. Summary of Findings

### 7.1 Compliance Table

| Requirement | Status | Severity | File/Line |
|------------|--------|----------|-----------|
| **1. Gemini Call Type 3 Grounding** | | | |
| 1.1 Structured output schema includes evidence_claim_ids | ✅ PASS | LOW | `llm/schemas.py:234` |
| 1.2 Gemini client enforces grounding (fallback) | ✅ PASS | LOW | `llm/gemini_client.py:248` |
| 1.3 System prompt requires grounding | ✅ PASS | LOW | `llm/base.py:82` |
| 1.4 Evidence_claim_ids persisted to database | ❌ FAIL | 🔴 CRITICAL | `db/models/event.py:162`, `events/manager.py:247` |
| 1.5 API returns actual evidence IDs (not fabricated) | ❌ FAIL | 🔴 CRITICAL | `api/routers/events.py:367` |
| 1.6 Evidence claim IDs validated against database | ⚠️ WARN | HIGH | `llm/gemini_client.py:210` |
| **2. Chain-of-Thought Never Requested/Leaked** | | | |
| 2.1 No CoT phrases in prompts | ✅ PASS | LOW | `llm/base.py` |
| 2.2 No thinking tokens requested | ✅ PASS | LOW | `llm/gemini_client.py:75` |
| 2.3 No reasoning content exposed | ✅ PASS | LOW | `llm/gemini_client.py:99` |
| **3. Gemini Call Types Verification** | | | |
| 3.1 Call Type 1 (Extract) implemented correctly | ✅ PASS | LOW | `llm/gemini_client.py:55` |
| 3.2 Call Type 2 (Adjudicate) implemented correctly | ✅ PASS | LOW | `llm/gemini_client.py:110` |
| 3.3 Call Type 3 (Synthesize) implemented correctly | ⚠️ MIXED | MEDIUM | `llm/gemini_client.py:189` |
| **4. Structured Output Schema** | | | |
| 4.1 Pydantic models for all call types | ✅ PASS | LOW | `llm/schemas.py` |
| 4.2 Schema validation on responses | ✅ PASS | LOW | `llm/gemini_client.py` |
| **5. API Key Safety** | | | |
| 5.1 API key loaded from environment | ✅ PASS | LOW | `llm/gemini_client.py:33` |
| 5.2 Startup guard for production mode | ✅ PASS | LOW | Cross-ref Dim 1 |

---

### 7.2 Critical Issues Requiring Resolution

#### Issue 1: Evidence Grounding Lost at Persistence Layer 🔴 CRITICAL

**Problem**: 
- Gemini Synthesize returns `evidence_claim_ids` for each narrative field
- Database schema only stores text, not evidence_claim_ids
- EventSnapshot ORM model lacks fields for evidence_claim_ids
- Snapshot creation code discards `.evidence_claim_ids`

**Impact**: The grounding contract (DEC-0008, §53-C) is broken. The system cannot verify which claims support which narrative statements.

**Required Fix**:
1. Add JSON columns to `event_snapshots` table:
   - `what_happened_evidence_claim_ids JSONB`
   - `why_it_matters_evidence_claim_ids JSONB`
   - `who_is_affected_evidence_claim_ids JSONB`
   - `conflict_summary_evidence_claim_ids JSONB`
2. Update `EventSnapshot` ORM model with these fields
3. Update `EventSynthesisManager.synthesize_event_snapshot()` to persist evidence IDs
4. Create Alembic migration

**Blocked**: Frontend grounding verification, acceptance test `test_acc_08b` (zero hardcoded metrics)

---

#### Issue 2: API Fabricates Evidence Citations 🔴 CRITICAL

**Problem**: 
- `/events/{id}` endpoint returns ALL primary claim IDs for ALL narrative fields
- Does not reflect actual evidence grounding from Gemini synthesis
- Violates DEC-0008 grounding contract

**Impact**: UI displays incorrect evidence citations. Users cannot trace which claims support which statements.

**Required Fix**:
1. After fixing Issue 1, retrieve stored evidence_claim_ids from EventSnapshot
2. Update `get_event_detail()` endpoint to use actual evidence IDs per field
3. Remove fabricated `primary_claim_ids` assignment

**Blocked**: Frontend evidence tracing, competition evaluation integrity

---

#### Issue 3: No Validation of Gemini-Returned Claim IDs ⚠️ HIGH

**Problem**: System does not validate that `evidence_claim_ids` returned by Gemini actually exist in the database.

**Impact**: Gemini could hallucinate claim IDs, causing broken references.

**Required Fix**:
Add validation in `GeminiClient.synthesize()`:
```python
valid_claim_ids = {c.claim_id for c in payload.claims}
for field in [response.what_happened, response.why_it_matters, ...]:
    if field:
        invalid_ids = set(field.evidence_claim_ids) - valid_claim_ids
        if invalid_ids:
            # Log warning or filter out invalid IDs
            field.evidence_claim_ids = [
                cid for cid in field.evidence_claim_ids if cid in valid_claim_ids
            ]
```

---

## 8. Recommendations

### 8.1 Immediate Actions (Before Stage 07)

1. **Fix Issue 1 (Evidence Persistence)** 🔴 CRITICAL
   - Add database columns for evidence_claim_ids
   - Update ORM model and persistence logic
   - Create Alembic migration

2. **Fix Issue 2 (API Fabrication)** 🔴 CRITICAL
   - Update API endpoint to return actual evidence IDs
   - Remove fabricated citations

3. **Add Evidence Validation** ⚠️ HIGH
   - Validate Gemini-returned claim IDs against input payload
   - Filter out hallucinated IDs

### 8.2 Testing Gaps to Address

1. **End-to-End Grounding Test**: Create acceptance test verifying:
   - Gemini returns evidence_claim_ids
   - Evidence IDs are persisted to database
   - API returns correct evidence IDs
   - Evidence IDs are valid claim references

2. **Evidence Validation Test**: Create unit test verifying:
   - Invalid evidence_claim_ids are filtered out
   - Empty evidence lists trigger fallback grounding

### 8.3 Documentation Updates

1. Update ADR-007 or create ADR-009 documenting:
   - Evidence persistence schema
   - API evidence citation contract
   - Evidence validation rules

2. Update acceptance matrix with evidence grounding verification scenario

---

## 9. Audit Conclusion

**Dimension 7 Status**: ⚠️ **PARTIAL PASS with CRITICAL GAPS**

The Gemini LLM implementation is well-architected with:
- ✅ Proper structured output enforcement
- ✅ Strong anti-prompt-injection defenses
- ✅ No chain-of-thought leakage
- ✅ Secure API key management

**However**, the grounding contract is BROKEN at the persistence and API layers:
- 🔴 Evidence claim IDs returned by Gemini are discarded during persistence
- 🔴 API fabricates evidence citations instead of returning actual grounding
- ⚠️ No validation that Gemini-returned claim IDs are valid

**These issues MUST be resolved before Stage 07 (Frontend)** to ensure:
1. Competition evaluation integrity (blind test requires verified grounding)
2. UI can display accurate evidence tracing
3. Grounding contract (DEC-0008, §53-C) is fully satisfied

**Estimated Effort**: 
- Database schema update: 2-3 hours
- ORM and persistence logic: 2-3 hours
- API endpoint fix: 1-2 hours
- Alembic migration: 1 hour
- Testing: 2-3 hours
- **Total**: 8-12 hours

**Priority**: 🔴 **CRITICAL** - Must fix before frontend development

---

**Audit Completed By**: Autonomous Research Subagent  
**Next Dimension**: Dimension 8 - OpenAPI 3.1 & Acceptance Matrix Verification
