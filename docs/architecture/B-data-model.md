# B. Data Model — Stay Mad §53-B

> Gabungan Master Spec §38 + Addendum §9. ADR-003 berlaku untuk semua keputusan skema.
> Perubahan skema, enum, atau kebijakan retensi memerlukan ADR baru.

---

## 1. Entity Relationship Overview

```
Source ─────────────────── ArticleVersion
  │                              │
  │                         Article (canonical)
  │                              │
  │                           Claim ──── ClaimEvidence (kutipan verbatim)
  │                              │
  │                        EventClaim
  │                              │
  └──────────────────── Event (canonical)
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
       EventSnapshot    TimelineEntry      Conflict
              │               │
       EventChange       Location
              │
    EventMembershipAudit
              │
     ProcessingRun ◄─── ProcessingJob
              │
           Action
```

---

## 2. Entity Definitions

### 2.1 Source

```yaml
id: UUID
name: string                        # nama tampilan sumber
url: string                         # base URL
source_type: enum(RSS|API|OFFICIAL_GOV|SCRAPE)
source_tier: enum(TIER_1|TIER_2)
source_family: string               # e.g. "TRANSMEDIA", "GOV_BMKG"
robots_policy: text                 # catatan kebijakan robots.txt
rate_limit_per_min: int
retention_rule: text                # kebijakan retensi konten
active: boolean
created_at: timestamptz
```

### 2.2 Article

```yaml
id: UUID
source_id: UUID → Source
url: string                         # URL kanonik artikel
content_hash: string                # SHA-256 dari konten normalized
category: enum(DISASTER_AND_WEATHER|TRANSPORTATION_AND_INFRASTRUCTURE|
               GOVERNMENT_AND_PUBLIC_POLICY)   # 3 MVP + EXTENSIBLE
language: string                    # BCP-47 (id, en)
created_at: timestamptz
```

### 2.3 ArticleVersion  *(immutable – Addendum §4)*

```yaml
id: UUID
article_id: UUID → Article
fetch_time: timestamptz             # waktu artikel diambil
published_time: timestamptz?
updated_time: timestamptz?
title: string
excerpt: string                     # maks 500 karakter
author: string?
content_hash: string                # SHA-256 versi ini
full_text_expires_at: timestamptz?  # sesuai retention_rule
schema_version: string              # versi kontrak data
processing_run_id: UUID → ProcessingRun
```

### 2.4 Claim  *(append-only – Addendum §9)*

```yaml
id: UUID
article_version_id: UUID → ArticleVersion
source_id: UUID → Source
claim_text: string                  # klaim atomik
source_span: string                 # kutipan verbatim < 200 karakter
speaker: string?                    # atribusi pembicara jika ada
negation: boolean                   # klaim negatif/ketidakpastian
numeric_value: float?               # nilai numerik ternormalisasi
unit: string?                       # satuan numerik
location_raw: string?               # teks lokasi dari sumber
event_time_raw: string?             # teks waktu asli dari sumber
event_time: timestamptz?            # hasil normalisasi (nullable)
event_time_precision: enum(EXACT|APPROXIMATE|DAY|RANGE|UNKNOWN)
event_time_qualifier: string?       # "sekitar", "diperkirakan", dst.
source_timezone: string?            # IANA timezone dari sumber
extraction_confidence: float        # 0.0–1.0
language: string                    # BCP-47
model_version: string               # model Gemini yang mengekstrak
prompt_version: string
schema_version: string
processing_run_id: UUID → ProcessingRun
created_at: timestamptz
```

### 2.5 Location

```yaml
id: UUID
city: string?
district: string?                   # kecamatan/kelurahan
province: string?
country: string
continent: string?
geo_level: enum(CITY|PROVINCE|COUNTRY|CONTINENT|WORLD)
canonical_name: string
source_text: string                 # teks lokasi asli
```

### 2.6 Event

```yaml
id: UUID
event_type: string                  # sub-type dalam kategori
category: enum(DISASTER_AND_WEATHER|TRANSPORTATION_AND_INFRASTRUCTURE|
               GOVERNMENT_AND_PUBLIC_POLICY)
primary_location_id: UUID → Location
time_window_start: timestamptz?
time_window_end: timestamptz?
created_at: timestamptz
updated_at: timestamptz
```

### 2.7 EventSnapshot  *(immutable – Addendum §4)*

```yaml
id: UUID
event_id: UUID → Event
version_number: int                 # 1, 2, 3…
published_at: timestamptz
headline: string                    # Bahasa Indonesia
what_happened: text
why_it_matters: text?
who_is_affected: text?
what_is_unknown: text?
confidence_score: float             # 0.0–1.0; lihat §53-F
confidence_bucket: enum(HIGH|MEDIUM|LOW)
evidence_status: enum(SUPPORTED|CONFLICTING|INSUFFICIENT|RETRACTED)
verification_level: enum(OFFICIAL_PRIMARY|INDEPENDENTLY_CORROBORATED|SINGLE_SOURCE)
actionability_level: enum(ACTION_REQUIRED|ACTION_RECOMMENDED|OPTIONAL|INFORMATIONAL|NO_IMMEDIATE_ACTION)
importance_score: float             # 0.0–1.0; lihat §53-G
urgency_score: float                # terpisah dari confidence
data_mode: enum(LIVE|DEMO)
last_processed_at: timestamptz
model_version: string
prompt_version: string
schema_version: string
processing_run_id: UUID → ProcessingRun
```

### 2.8 EventChange  *(Addendum §7)*

```yaml
id: UUID
event_id: UUID → Event
from_snapshot_id: UUID → EventSnapshot
to_snapshot_id: UUID → EventSnapshot
change_type: enum(ADDED|UPDATED|CORRECTED|RETRACTED)
field_name: string?
before_value: text?
after_value: text?
evidence_claim_ids: UUID[]          # referensi ke Claim
created_at: timestamptz
```

### 2.9 EventClaim

```yaml
id: UUID
event_id: UUID → Event
snapshot_id: UUID → EventSnapshot
claim_id: UUID → Claim
role: enum(PRIMARY|SUPPORTING|CONFLICTING|RETRACTED)
assigned_at: timestamptz
```

### 2.10 EventMembershipAudit  *(Addendum §6)*

```yaml
id: UUID
article_version_id: UUID → ArticleVersion
candidate_event_ids: UUID[]
decision: enum(SAME_EVENT|RELATED_EVENT|SEPARATE_EVENT|NEEDS_REVIEW)
deterministic_signals: jsonb        # {"location_match":true,"time_delta_hours":2, ...}
decision_reason_codes: string[]     # ["LOC_MATCH","TIME_WITHIN_WINDOW","ENT_OVERLAP"]
evidence_claim_ids: UUID[]
model_version: string
prompt_version: string
schema_version: string
processing_run_id: UUID → ProcessingRun
created_at: timestamptz
```

### 2.11 TimelineEntry

```yaml
id: UUID
event_id: UUID → Event
snapshot_id: UUID → EventSnapshot
event_time: timestamptz?
event_time_precision: enum(EXACT|APPROXIMATE|DAY|RANGE|UNKNOWN)
event_time_qualifier: string?       # "sekitar", "diperkirakan"
description: string                 # Bahasa Indonesia
evidence_claim_ids: UUID[]
order_index: int                    # posisi urutan dalam timeline
created_at: timestamptz
```

### 2.12 Conflict

```yaml
id: UUID
event_id: UUID → Event
snapshot_id: UUID → EventSnapshot
field_name: string                  # mis. "affected_districts_count"
claim_a_id: UUID → Claim
claim_b_id: UUID → Claim
value_a: text
value_b: text
context: text?                      # penjelasan singkat konflik
resolved: boolean
resolution_claim_id: UUID?          # klaim yang menyelesaikan konflik
created_at: timestamptz
```

### 2.13 Action

```yaml
id: UUID
event_id: UUID → Event
snapshot_id: UUID → EventSnapshot
action_level: enum(ACTION_REQUIRED|ACTION_RECOMMENDED|OPTIONAL|INFORMATIONAL|NO_IMMEDIATE_ACTION)
action_text: string                 # Bahasa Indonesia
source_type: enum(OFFICIAL_EMERGENCY|OFFICIAL_GOV|OFFICIAL_HEALTH|INFORMATIONAL)
evidence_claim_ids: UUID[]          # WAJIB ada untuk REQUIRED/RECOMMENDED
created_at: timestamptz
```

### 2.14 ProcessingRun  *(Addendum §9)*

```yaml
id: UUID
stage: enum(INGEST|EXTRACT|RESOLVE|SYNTHESIZE|EVALUATE)
triggered_at: timestamptz
completed_at: timestamptz?
status: enum(RUNNING|COMPLETED|FAILED|DEAD_LETTER)
articles_processed: int
error_message: text?
model_version: string
prompt_version: string
schema_version: string
cost_estimate_usd: float?
```

### 2.15 ProcessingJob  *(antrean kerja; berbeda dari ProcessingRun)*

```yaml
id: UUID
processing_run_id: UUID → ProcessingRun
job_type: enum(INGEST|EXTRACT|RESOLVE|SYNTHESIZE)
idempotency_key: string
status: enum(QUEUED|RUNNING|DONE|FAILED|DEAD_LETTER)
retry_count: int
max_retries: int
correlation_id: string
payload: jsonb
enqueued_at: timestamptz
started_at: timestamptz?
completed_at: timestamptz?
error_message: text?
```

### 2.16 EventRelation  *(opsional MVP – Addendum §6)*

```yaml
id: UUID
from_event_id: UUID → Event
to_event_id: UUID → Event
relation_type: enum(RELATED_TO)     # hanya related_to di MVP jika ada kebutuhan UI
confidence: float
processing_run_id: UUID → ProcessingRun
created_at: timestamptz
```

---

## 3. Index Kritis

```sql
-- Deduplication
CREATE UNIQUE INDEX idx_article_content_hash ON article(content_hash);

-- Candidate retrieval
CREATE INDEX idx_claim_event_time ON claim(event_time);
CREATE INDEX idx_event_location ON event(primary_location_id, time_window_start);
CREATE INDEX idx_event_category ON event(category);

-- pgvector embedding (Tier 2)
CREATE INDEX idx_claim_embedding ON claim USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Processing trace
CREATE INDEX idx_processing_run_id ON claim(processing_run_id);
CREATE INDEX idx_processing_run_id_snapshot ON event_snapshot(processing_run_id);
```

---

## 4. Kebijakan Retensi

| Entity | Retensi |
|---|---|
| ArticleVersion.full_text | Sesuai `source.retention_rule`; ANTARA 7 hari, BPBD/BNPB 30 hari |
| Claim (kutipan < 200 karakter) | Permanen (bukti provenance) |
| EventSnapshot | Permanen (immutable record) |
| EventChange | Permanen |
| ProcessingRun | Permanen |
| Embedding vectors | Permanen (diperlukan untuk retrieval) |

---

## 5. Enum Authority

Semua enum di atas adalah **sumber kebenaran kanonik**. Perubahan memerlukan ADR.

| Enum Group | ADR Ref |
|---|---|
| `evidence_status` | ADR-004 |
| `confidence_bucket` (HIGH/MEDIUM/LOW) | ADR-004 |
| `verification_level` | ADR-004 |
| `actionability_level` | ADR-006 |
| `decision` (EventMembershipAudit) | ADR-005 |
| `category` | DEC-0002, DEC-0007 |
