# D. Event Resolution Algorithm — Stay Mad §53-D

> Algoritma hibrida tiga tingkat dengan ablation tiers.
> Semua threshold adalah nilai konfigurasi di `config/resolver.yaml`; tidak ada magic constant di kode.

---

## 1. Pipeline Overview

```
ArticleVersion (baru)
        │
        ▼
[Tier 1: Deterministic]
  Hard constraint check + content dedup + source family grouping
        │
        ├── REJECT (content duplicate / allowlist violation)
        │
        ▼
  Candidate generation (metadata filter: category, time window, location)
        │
        ▼
[Tier 2: Embedding Retrieval]
  pgvector cosine similarity top-K
  Gabungkan dengan: time delta score, location score, entity score
  → Composite candidate score
        │
        ├── Score < low_threshold → SEPARATE_EVENT (no Gemini needed)
        │
        ▼
[Tier 3: Gemini Adjudication]  (hanya kandidat ambiguous: score ∈ [low, high])
  Gemini Call Type 2 (Adjudicate)
  Output: SAME_EVENT | RELATED_EVENT | SEPARATE_EVENT | NEEDS_REVIEW
        │
        ▼
  EventMembershipAudit record (semua tier, disimpan selalu)
        │
        ▼
  MERGE → update EventSnapshot | SEPARATE → buat Event baru | RELATED → EventRelation
```

---

## 2. Tier 1 — Deterministic

### 2.1 Hard Constraints (sebelum kandidat dibuat)

Sebuah artikel **tidak dapat** dimasukkan ke event yang sudah ada jika **salah satu** kondisi berikut terpenuhi:

| Constraint | Definisi | Config Key |
|---|---|---|
| `LOC_INCOMPATIBLE` | Lokasi primer artikel & event tidak overlap (wilayah berbeda) | `resolver.hard.location_incompatible_km` |
| `TIME_INCOMPATIBLE` | `event_time` artikel lebih dari N jam sebelum/sesudah event time window | `resolver.hard.time_incompatible_hours` |
| `CAT_MISMATCH` | Kategori artikel berbeda dengan event category | `resolver.hard.strict_category` |
| `TYPE_EXCLUSIVE` | Event type saling eksklusif (mis. banjir vs gempa di lokasi sama) | `resolver.hard.type_exclusion_rules` |

Kegagalan hard constraint → langsung `SEPARATE_EVENT` tanpa memanggil Gemini.

### 2.2 Content Deduplication

```
content_hash = sha256(normalize(title + excerpt))
```

- Jika hash sudah ada di DB: `ArticleVersion` baru dibuat (immutable), namun tidak membuat `Claim` baru atau mempengaruhi corroboration count.
- Deduplikasi dilakukan **sebelum** ekstraksi Gemini (menghemat biaya).

### 2.3 Source Family Grouping

Sebelum menghitung corroboration:
- Artikel dari `source_family` yang sama (mis. `TRANSMEDIA`: CNN Indonesia + Detikcom) dihitung sebagai **satu laporan keluarga**, bukan dua laporan independen.
- Wire copy ANTARA yang diterbitkan ulang oleh media Tier 2: dikembalikan ke LKBN_ANTARA sebagai satu bukti primer.

### 2.4 Candidate Generation (Deterministic Filter)

Buat daftar event kandidat yang memenuhi:
- Kategori sama (`category_match = true`)
- Overlap temporal: `|article.event_time - event.time_window_center| ≤ time_candidate_window_hours`
- Overlap lokasi: `province` sama ATAU `location_raw` overlap string

---

## 3. Tier 2 — Embedding Retrieval

### 3.1 Embedding Generation

- Setelah klaim diekstrak, buat embedding dari: `title + " " + primary_claims_text`
- Model embedding: dikonfigurasi via `EMBEDDING_MODEL` env var (lihat ADR-007)
- Simpan di kolom `embedding` (pgvector) pada tabel `claim` dan `event_snapshot`

### 3.2 Cosine Similarity Top-K

```sql
SELECT event_id, 1 - (embedding <=> query_embedding) AS cosine_sim
FROM event_snapshot
WHERE category = :category
ORDER BY embedding <=> query_embedding
LIMIT :top_k;
-- top_k dikonfigurasi: resolver.embedding.top_k (default: 10)
```

### 3.3 Composite Candidate Score

Untuk setiap kandidat event dari Tier 2:

```
score = w_semantic  * cosine_sim
      + w_time      * time_score
      + w_location  * location_score
      + w_entity    * entity_overlap_score
```

Dimana:
- `time_score = max(0, 1 - time_delta_hours / resolver.scoring.time_decay_hours)`
- `location_score = 1.0` jika kota sama, `0.5` jika provinsi sama, `0.0` jika berbeda
- `entity_overlap_score = |entities_A ∩ entities_B| / |entities_A ∪ entities_B|` (Jaccard)

Bobot default di `config/resolver.yaml`:
```yaml
resolver:
  scoring:
    w_semantic: 0.40
    w_time: 0.30
    w_location: 0.20
    w_entity: 0.10
    time_decay_hours: 48
  thresholds:
    low: 0.35   # di bawah ini → SEPARATE_EVENT tanpa Gemini
    high: 0.75  # di atas ini → SAME_EVENT tanpa Gemini
    # antara low dan high → Gemini adjudication (Tier 3)
```

---

## 4. Tier 3 — Gemini Adjudication

Dipanggil **hanya** untuk kandidat dengan `score ∈ [low_threshold, high_threshold]`.

- Input: anchor event summary + candidate articles (lihat §53-C Call Type 2)
- Output: keputusan per kandidat artikel
- Semua sinyal deterministik (Tier 1+2) **disertakan** di input Gemini sebagai konteks
- Keputusan Gemini disimpan di `EventMembershipAudit` dengan `decision_reason_codes`

### 4.1 Transitive Cluster Guard

Gemini **tidak boleh** membentuk cluster transitif secara buta (A≈B, B≈C → A,B,C dianggap satu event). Setiap artikel dicek secara independen terhadap **canonical event evidence**, bukan terhadap artikel lain dalam cluster.

### 4.2 Special Cases

| Kasus | Penanganan |
|---|---|
| Recurring event (mis. banjir rutin tahunan) | Beda time window → SEPARATE_EVENT |
| Multi-event article | Klaim dari artikel ini dapat masuk dua event berbeda; satu artikel ≠ satu event |
| Correction/retraction | Buat EventChange type CORRECTED/RETRACTED; klaim lama tidak dihapus |
| Parent event vs effect | RELATED_EVENT; tidak di-merge |
| Ambiguous evidence | Default: SEPARATE_EVENT atau NEEDS_REVIEW |

---

## 5. Decision & Audit Record

Setiap keputusan (dari tier manapun) disimpan di `EventMembershipAudit`:

```yaml
decision: SAME_EVENT | RELATED_EVENT | SEPARATE_EVENT | NEEDS_REVIEW
deterministic_signals:
  location_match: true
  time_delta_hours: 2.5
  entity_overlap_count: 3
  cosine_sim: 0.81
  composite_score: 0.72
decision_reason_codes: ["LOC_MATCH", "TIME_WITHIN_WINDOW", "CORROBORATED"]
tier_used: "TIER_2"  # atau TIER_1, TIER_3, GEMINI
```

---

## 6. Ablation Study Design

Tiga konfigurasi untuk studi ablasi (diukur terhadap gold evaluation set):

| Konfigurasi | Komponen Aktif | Metric Target |
|---|---|---|
| `ablation_tier1` | Hanya deterministic rules | Baseline precision/recall |
| `ablation_tier2` | Tier 1 + embedding retrieval | Delta precision/recall vs tier1 |
| `ablation_tier3` | Tier 1 + 2 + Gemini (full) | Delta precision/recall vs tier2 |

Setiap run ablasi disimpan dengan `processing_run_id` unik dan menghasilkan evaluation report terpisah (lihat §53-I).

---

## 7. Konfigurasi (config/resolver.yaml skeleton)

```yaml
resolver:
  hard:
    time_incompatible_hours: 72
    location_incompatible_km: null   # TODO: implementasi geodistance Stage 04
    strict_category: true
    type_exclusion_rules: []         # diisi saat Stage 04
  embedding:
    top_k: 10
    min_cosine: 0.20               # abaikan kandidat dengan similarity sangat rendah
  scoring:
    w_semantic: 0.40
    w_time: 0.30
    w_location: 0.20
    w_entity: 0.10
    time_decay_hours: 48
  thresholds:
    low: 0.35
    high: 0.75
  adjudication:
    max_candidates_per_call: 5      # batasi input Gemini
    needs_review_confidence_cutoff: 0.60
```

> Semua nilai ini adalah **starting point**; wajib dikalibrasi terhadap labeled evaluation set sebelum Stage 05 dinyatakan complete.
