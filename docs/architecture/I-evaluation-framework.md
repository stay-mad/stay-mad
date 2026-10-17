# I. Evaluation Framework — Stay Mad §53-I

> Berdasarkan Addendum §8. Evaluasi adalah aktivitas berkelanjutan dari Stage 02, bukan hanya di akhir.
> Evaluator buta: tidak membaca/memodifikasi gold labels saat menjalankan evaluasi.

---

## 1. Dataset Evaluasi

### 1.1 Gold Evaluation Set

Target: **50–100 artikel**, **10–20 event berlabel**, mencakup:

| Kasus | Status |
|---|---|
| Artikel duplikat / sindikasi | ✅ Wajib ada |
| 1 event berkembang dengan update resmi | ✅ Wajib ada |
| 1 konflik angka yang bersumber | ✅ Wajib ada |
| Ekspresi temporal ambigu | ✅ Wajib ada |
| Beberapa lokasi Jakarta/Indonesia | ✅ Wajib ada |
| Wording mirip tapi event berbeda | ✅ Wajib ada |
| Artikel multi-event | ✅ Wajib ada (Addendum §11 extra fixtures) |
| Dua event serupa di hari berbeda | ✅ Wajib ada |
| Retraksi | ✅ Wajib ada |
| Timestamp parsial/relatif | ✅ Wajib ada |
| Instruksi jahat di teks sumber | ✅ Wajib ada |

### 1.2 Demo Fixture Set (Deterministic)

23 artikel di `eval/fixtures/seed_demo_23.json` — 4 klaster, 3 kategori MVP.
Digunakan untuk acceptance tests (test_acc_01 hingga test_acc_08) dan reproducible demo.

### 1.3 Pemisahan Data

```
eval/gold/
  train/    ← hanya untuk kalibrasi threshold (tidak untuk blind eval)
  dev/      ← development evaluation (ablation study)
  test/     ← final blind evaluation (baca hanya saat laporan resmi)
```

Evaluator tidak boleh membaca atau memodifikasi `eval/gold/` saat menjalankan blind run.

---

## 2. Metrik yang Diukur

### 2.1 Event Clustering

| Metrik | Formula | Target |
|---|---|---|
| Pairwise Precision | `TP / (TP + FP)` | ≥ 0.80 |
| Pairwise Recall | `TP / (TP + FN)` | ≥ 0.75 |
| Pairwise F1 | Harmonic mean | ≥ 0.77 |
| B³ Precision | Entitas-weighted | ≥ 0.78 |
| B³ Recall | Entitas-weighted | ≥ 0.73 |
| B³ F1 | Harmonic mean | ≥ 0.75 |

### 2.2 Timeline

| Metrik | Keterangan | Target |
|---|---|---|
| Pairwise Ordering F1 | Apakah A terjadi sebelum B | ≥ 0.75 |
| Timestamp Coverage | % TimelineEntry dengan `event_time` non-null | ≥ 0.60 |
| Temporal Qualifier Preservation | % kualifikasi "sekitar" dll. dipertahankan | = 1.00 |

### 2.3 Location Accuracy

| Metrik | Keterangan | Target |
|---|---|---|
| City-level Accuracy | Benar pada level kota | ≥ 0.85 |
| Province-level Accuracy | Benar pada level provinsi | ≥ 0.90 |
| Hierarchical F1 | Evaluasi multi-level hierarki lokasi | ≥ 0.82 |

### 2.4 Claim Attribution

| Metrik | Keterangan | Target |
|---|---|---|
| Grounded Claim Coverage | % output fields dengan evidence_claim_ids | = 1.00 |
| Unsupported Claim Rate | % klaim output tanpa grounding verbatim | = 0.00 |
| Source Attribution Accuracy | URL sumber benar untuk setiap klaim | ≥ 0.95 |

### 2.5 Conflict Detection

| Metrik | Keterangan | Target |
|---|---|---|
| Conflict Precision | False conflicts flagged | ≥ 0.80 |
| Conflict Recall | Missed conflicts | ≥ 0.80 |
| Conflict F1 | — | ≥ 0.80 |

### 2.6 Change Detection

| Metrik | Keterangan | Target |
|---|---|---|
| Change Precision | False change sets | ≥ 0.80 |
| Change Recall | Missed material changes | ≥ 0.75 |
| No-change Specificity | Wording-only tidak memicu change | = 1.00 |

### 2.7 Actionability Safety

| Metrik | Keterangan | Target |
|---|---|---|
| Unsupported Action Rate | ACTION REQUIRED/RECOMMENDED tanpa sumber resmi | = 0.00 |
| Prompt Injection Failure Rate | Instruksi jahat berhasil dieksekusi | = 0.00 |

---

## 3. Evaluation Report Format

Setiap evaluation run menghasilkan report di `eval/reports/YYYYMMDD-HHMMSS-<commit>.json`:

```json
{
  "report_id": "uuid",
  "dataset_version": "gold-v1.0",
  "code_commit": "abc1234",
  "model_version": "gemini-2.0-flash",
  "prompt_version": "extract-v1.2 | adjudicate-v1.1 | synthesize-v1.3",
  "schema_version": "1.0",
  "run_timestamp": "2026-10-11T07:00:00Z",
  "processing_run_id": "uuid",
  "ablation_tier": "TIER_3",
  "raw_counts": {
    "articles_processed": 75,
    "events_labeled": 15,
    "clusters_produced": 14,
    "timeline_entries": 87,
    "conflicts_detected": 5,
    "actions_generated": 3
  },
  "failures": {
    "extraction_failures": 2,
    "adjudication_failures": 0,
    "synthesis_failures": 1
  },
  "latency": {
    "p50_ms": 1200,
    "p95_ms": 4500,
    "p99_ms": 8200
  },
  "cost_estimate_usd": 0.42,
  "metrics": {
    "clustering": {"pairwise_f1": 0.83, "b3_f1": 0.79},
    "timeline": {"ordering_f1": 0.77, "timestamp_coverage": 0.68},
    "location": {"city_accuracy": 0.88},
    "attribution": {"grounded_coverage": 1.00, "unsupported_rate": 0.00},
    "conflict": {"f1": 0.82},
    "change": {"precision": 0.85, "recall": 0.78},
    "safety": {"unsupported_action_rate": 0.00, "injection_failure_rate": 0.00}
  }
}
```

---

## 4. Ablation Study Protocol

Jalankan tiga konfigurasi pada dev set (lihat §53-D):

```bash
make eval-baseline ABLATION=tier1  # deterministic only
make eval-baseline ABLATION=tier2  # + embeddings
make eval-baseline ABLATION=tier3  # + Gemini (full)
```

Setiap run menghasilkan report terpisah. Delta antara tier menunjukkan kontribusi tiap komponen untuk laporan competition.

---

## 5. Aturan Blind Evaluation

1. `eval/gold/test/` hanya dibaca oleh evaluator runner; tidak pernah dimodifikasi selama evaluasi.
2. Kode sistem tidak boleh mempunyai path code yang mengakses `eval/gold/` selama inferensi normal.
3. Semua metrik wajib berasal dari `processing_run_id` yang valid dan tersimpan di DB.
4. Competition demo hanya mengutip metrik dari report artifact yang sudah ada di repo.
5. Pelanggaran aturan ini termasuk dalam **RSK-12** di K-risk-register.md.

---

## 6. Jadwal Evaluasi

| Stage | Aktivitas Evaluasi |
|---|---|
| 02 | Buat gold labels, annotation guide, baseline expectation |
| 03 | Jalankan ablation tier1 terhadap fixture 23 artikel |
| 04 | Jalankan ablation tier2 setelah embedding tersedia |
| 05 | Jalankan ablation tier3 (full), kalibrasi threshold resolver |
| 08 | Final blind evaluation pada test set; tulis competition report |
