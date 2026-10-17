# C. Gemini Architecture — Stay Mad §53-C

> Tiga tipe call Gemini: Extract / Adjudicate / Synthesize.
> Model dipilih saat implementasi; dikonfigurasi via `GEMINI_MODEL` env var (ADR-007).
> Free-form model text bukan sumber kebenaran — hanya JSON tervalidasi yang diproses.

---

## Prinsip Lintas-Tipe

1. **Structured output only**: semua call menggunakan `response_mime_type: application/json` dengan schema JSON tervalidasi.
2. **Prompt injection defense**: teks artikel ditempatkan dalam delimitir data eksplisit (`<article_data>…</article_data>`); sistem tidak pernah menggabungkan teks bebas artikel ke dalam system instruction.
3. **Cache key**: setiap call tipe memiliki cache key deterministik. Hasil di-cache; klaim/artikel tidak diproses ulang bila tidak berubah.
4. **Fallback**: setiap call memiliki fallback deterministik yang tidak menghasilkan output palsu.
5. **Validasi**: output JSON divalidasi terhadap Pydantic schema sebelum dipersist.
6. **Versioning**: setiap call merekam `model_version`, `prompt_version`, `schema_version`, `processing_run_id`.

---

## Call Type 1 — Extract

### Tujuan
Mengekstrak klaim atomik terstruktur, entitas, referensi temporal, dan kategori dari satu `ArticleVersion`. Ini adalah titik masuk AI ke pipeline.

### Input

```json
{
  "article_version_id": "uuid",
  "source_id": "uuid",
  "source_tier": "TIER_1",
  "source_family": "GOV_BMKG",
  "title": "...",
  "excerpt": "...",         // max 500 karakter; BUKAN full text
  "published_time": "ISO-8601",
  "updated_time": "ISO-8601 | null",
  "source_url": "https://..."
}
```

**Catatan input**: `full_text` TIDAK dikirim ke Gemini (copyright & biaya). Hanya `title` + `excerpt` (≤ 500 karakter).

### Output Schema

```json
{
  "schema_version": "1.0",
  "article_version_id": "uuid",
  "suggested_category": "DISASTER_AND_WEATHER | TRANSPORTATION_AND_INFRASTRUCTURE | GOVERNMENT_AND_PUBLIC_POLICY | UNKNOWN",
  "claims": [
    {
      "claim_text": "string",
      "source_span": "string (< 200 karakter verbatim dari excerpt)",
      "speaker": "string | null",
      "negation": false,
      "numeric_value": null,
      "unit": null,
      "location_raw": "string | null",
      "event_time_raw": "string | null",
      "event_time_qualifier": "sekitar | diperkirakan | null",
      "event_time_precision": "EXACT | APPROXIMATE | DAY | RANGE | UNKNOWN",
      "extraction_confidence": 0.92
    }
  ],
  "entities": [
    {
      "name": "string",
      "type": "PERSON | ORGANIZATION | LOCATION | INFRASTRUCTURE | INSTITUTION",
      "canonical_form": "string | null"
    }
  ],
  "primary_location_raw": "string | null",
  "primary_event_time_raw": "string | null",
  "insufficient_content": false
}
```

### Model Config

| Parameter | Nilai |
|---|---|
| `model` | `${GEMINI_MODEL}` (lihat ADR-007) |
| `temperature` | `0.0` (deterministic extraction) |
| `response_mime_type` | `application/json` |
| `max_output_tokens` | 2048 |
| `top_k` | — |

### Validasi

1. `claims[].source_span` harus merupakan substring (fuzzy ≥ 85%) dari `excerpt` yang diberikan.
2. `extraction_confidence` adalah float 0.0–1.0.
3. `suggested_category` harus masuk enum atau `UNKNOWN`.
4. Klaim dengan `extraction_confidence < 0.5` ditandai suspicious dan memerlukan review.

### Fallback

Jika call gagal (timeout, error API, invalid JSON): simpan `ProcessingJob.status = FAILED`, artikel masuk dead-letter queue. **Tidak ada output diinvent**. Event tidak dihasilkan dari artikel yang gagal ekstraksi.

### Cache Key

```
sha256(article_version_id + ":" + prompt_version + ":" + schema_version)
```

Jika `article_version_id` sama dan versi identik, hasil cache digunakan; Gemini tidak dipanggil ulang.

---

## Call Type 2 — Adjudicate

### Tujuan
Menentukan apakah sekumpulan kandidat artikel/klaim merujuk pada **peristiwa yang sama, terkait, atau terpisah**. Dipanggil HANYA setelah Tier 1 (deterministic) dan Tier 2 (embedding) lolos dan menghasilkan kandidat yang ambigu.

### Input

```json
{
  "schema_version": "1.0",
  "processing_run_id": "uuid",
  "anchor_event_id": "uuid | null",
  "anchor_summary": {
    "headline": "string",
    "category": "string",
    "primary_location": "string",
    "time_window_start": "ISO-8601 | null",
    "time_window_end": "ISO-8601 | null",
    "representative_claims": ["string", "string", "string"]
  },
  "candidate_articles": [
    {
      "article_version_id": "uuid",
      "source_tier": "TIER_1",
      "source_family": "string",
      "title": "string",
      "excerpt": "string (≤ 500 karakter)",
      "published_time": "ISO-8601",
      "primary_location_raw": "string | null",
      "primary_event_time_raw": "string | null",
      "deterministic_score": 0.72,
      "deterministic_signals": {
        "location_match": true,
        "time_delta_hours": 2.5,
        "entity_overlap_count": 3,
        "category_match": true
      },
      "top_claims": ["string", "string"]
    }
  ]
}
```

### Output Schema

```json
{
  "schema_version": "1.0",
  "decisions": [
    {
      "article_version_id": "uuid",
      "decision": "SAME_EVENT | RELATED_EVENT | SEPARATE_EVENT | NEEDS_REVIEW",
      "decision_reason_codes": ["LOC_MATCH", "TIME_WITHIN_WINDOW", "ENT_OVERLAP"],
      "evidence_claim_ids": ["uuid"],
      "confidence": 0.88,
      "notes": "string | null"
    }
  ],
  "suggested_event_headline": "string | null"
}
```

### Decision Reason Codes (daftar resmi)

| Kode | Makna |
|---|---|
| `LOC_MATCH` | Lokasi primer kompatibel |
| `LOC_INCOMPATIBLE` | Lokasi primer berbeda/bertentangan |
| `TIME_WITHIN_WINDOW` | Event time dalam window yang sama |
| `TIME_INCOMPATIBLE` | Waktu saling eksklusif |
| `ENT_OVERLAP` | Entity kunci tumpang tindih |
| `CAT_MISMATCH` | Kategori tidak kompatibel |
| `SOURCE_SYNDICATE` | Artikel berasal dari source family yang sama (tidak independen) |
| `CORROBORATED` | Dikuatkan oleh sumber independen |
| `AMBIGUOUS` | Sinyal tidak cukup untuk keputusan pasti |

### Model Config

| Parameter | Nilai |
|---|---|
| `model` | `${GEMINI_MODEL}` |
| `temperature` | `0.1` (sedikit fleksibel untuk reasoning) |
| `response_mime_type` | `application/json` |
| `max_output_tokens` | 1024 |

### Validasi

1. `decision` harus masuk enum.
2. `confidence` adalah float 0.0–1.0.
3. Bila `decision = NEEDS_REVIEW`, flag untuk human/manual review queue.
4. Bila `decision = SAME_EVENT` tapi `confidence < 0.6`: override ke `NEEDS_REVIEW`.

### Fallback

Jika call gagal: default ke `SEPARATE_EVENT` dengan `decision_reason_codes: ["ADJUDICATION_FAILED"]`. False merge lebih berbahaya dari false separation (Addendum §6).

### Cache Key

```
sha256(sorted(article_version_ids) + ":" + anchor_event_id + ":" + prompt_version + ":" + schema_version)
```

---

## Call Type 3 — Synthesize

### Tujuan
Menghasilkan narasi final event (WHAT HAPPENED, WHY IT MATTERS, WHO IS AFFECTED, WHAT IS UNKNOWN), ringkasan konflik, dan teks aksi — semua grounded pada `evidence_claim_ids`. Dipanggil untuk membuat atau memperbarui `EventSnapshot`.

### Input

```json
{
  "schema_version": "1.0",
  "processing_run_id": "uuid",
  "event_id": "uuid",
  "category": "DISASTER_AND_WEATHER",
  "primary_location": {
    "city": "Jakarta Timur",
    "province": "DKI Jakarta",
    "country": "Indonesia"
  },
  "time_window_start": "ISO-8601",
  "time_window_end": "ISO-8601 | null",
  "output_language": "id",
  "claims": [
    {
      "claim_id": "uuid",
      "claim_text": "string",
      "source_span": "string",
      "source_tier": "TIER_1",
      "source_family": "GOV_BPBD_DKI",
      "event_time": "ISO-8601 | null",
      "event_time_qualifier": "sekitar | null",
      "extraction_confidence": 0.92,
      "role": "PRIMARY | SUPPORTING | CONFLICTING"
    }
  ],
  "conflicts": [
    {
      "field_name": "affected_districts_count",
      "value_a": "5",
      "value_b": "7",
      "claim_a_id": "uuid",
      "claim_b_id": "uuid"
    }
  ],
  "previous_snapshot_id": "uuid | null",
  "actionability_gate_passed": false
}
```

### Output Schema

```json
{
  "schema_version": "1.0",
  "headline": "string (Bahasa Indonesia, ≤ 120 karakter)",
  "what_happened": {
    "text": "string (Bahasa Indonesia)",
    "evidence_claim_ids": ["uuid"]
  },
  "why_it_matters": {
    "text": "string | null",
    "evidence_claim_ids": ["uuid"]
  },
  "who_is_affected": {
    "text": "string | null",
    "evidence_claim_ids": ["uuid"]
  },
  "what_is_unknown": {
    "text": "string | null",
    "evidence_claim_ids": []
  },
  "conflict_summary": {
    "text": "string | null",
    "evidence_claim_ids": ["uuid"]
  },
  "suggested_actions": [
    {
      "action_level": "ACTION_REQUIRED | ACTION_RECOMMENDED | OPTIONAL | INFORMATIONAL | NO_IMMEDIATE_ACTION",
      "action_text": "string",
      "requires_official_source": true,
      "evidence_claim_ids": ["uuid"]
    }
  ],
  "insufficient_evidence": false
}
```

### Model Config

| Parameter | Nilai |
|---|---|
| `model` | `${GEMINI_MODEL}` |
| `temperature` | `0.2` |
| `response_mime_type` | `application/json` |
| `max_output_tokens` | 2048 |

### Validasi

1. Setiap field faktual **wajib** memiliki `evidence_claim_ids` non-kosong — kecuali `what_is_unknown`.
2. `suggested_actions[].action_level = ACTION_REQUIRED | ACTION_RECOMMENDED` hanya valid jika claim yang direferensikan berasal dari sumber `TIER_1` dengan `source_family` bertipe `GOV_*`.
3. Bila `insufficient_evidence = true`: semua field naratif bernilai `"Not enough information available."`.
4. Narasi final divalidasi: tidak boleh mengandung angka, waktu, atau kutipan yang tidak tercantum di `claims` yang dikirimkan.

### Fallback

Jika call gagal: `EventSnapshot` tidak dihasilkan. Status `ProcessingJob = FAILED`. UI menampilkan state degradasi yang jujur.

### Cache Key

```
sha256(sorted(claim_ids_used) + ":" + event_id + ":" + prompt_version + ":" + schema_version)
```

Cache tidak valid jika ada klaim baru yang menambah atau mengubah set `claim_ids`.

---

## Ringkasan Tiga Tipe Call

| Aspek | Extract | Adjudicate | Synthesize |
|---|---|---|---|
| Dipanggil untuk | 1 ArticleVersion | N kandidat artikel | 1 Event (kumpulan klaim) |
| Temperature | 0.0 | 0.1 | 0.2 |
| Output utama | Claims + Entities | Membership decision | EventSnapshot narasi |
| Fallback | Dead-letter | SEPARATE_EVENT | No snapshot |
| Cache invalidation | Perubahan article_version | Perubahan kandidat set | Perubahan klaim set |
| Wajib evidence_ids | source_span verbatim | evidence_claim_ids | Setiap field naratif |
