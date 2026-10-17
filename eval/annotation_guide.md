# Annotation Guide for Evaluation Datasets (eval/annotation_guide.md)

Panduan pelabelan dataset acuan (*gold dataset*) untuk evaluasi pipeline Stay Mad.
Authority: ADR-008, Addendum §8, docs/architecture/I-evaluation-framework.md, Temuan A-5.

---

## 1. Perlindungan Folder Gold & Pemisahan Dataset

Sesuai **ADR-008** dan **AGENTS.md**:
- Direktori `eval/gold/` bersifat **read-only / dilindungi**. Tidak boleh diedit secara otomatis oleh script tanpa verifikasi manusia.
- Pemisahan data:
  ```
  eval/gold/
    train/           # Kalibrasi threshold saja (tidak untuk blind eval)
    dev/             # Evaluasi development & ablation study (Tier 1, 2, 3)
    test/            # Evaluasi buta (blind evaluation final) - HANYA dibaca evaluator runner
    schema.json      # Validasi skema gold sample
  ```
- **Isolasi Gold Set (RSK-12)**:
  - Kode aplikasi (`backend/staymad/`) **DILARANG KERAS** mengimpor atau membaca path `eval/gold/test/`.
  - Pelanggaran akan dideteksi oleh static import audit di CI / unit test.
  - Blind runner (`make eval-blind`) hanya membaca `test/` jika flag `--blind` eksplisit dipanggil.

---

## 2. Protokol Anotasi 6-Field + Kebijakan Aksi (ADR-008 §3 & Temuan A-5)

Setiap sampel di `eval/gold/` merepresentasikan satu artikel yang telah dianotasi dengan label evaluasi:

```json
{
  "sample_id": "gold_smp_001",
  "article_id": "art_sample_01",
  "source_domain": "bpbd.jakarta.go.id",
  "published_at": "2026-10-10T08:30:00Z",
  "category": "disaster_and_weather",
  "labels": {
    "event_id": "evt_jakarta_flood_2026_10",
    "timeline_order": 1,
    "location_canonical": "Jakarta Timur, DKI Jakarta",
    "has_conflict": false,
    "expected_change": true,
    "action_policy": "ACTION_REQUIRED",
    "action_policy_violation": false
  },
  "claims": [
    {
      "claim_id": "clm_001",
      "verbatim_quote": "BPBD menetapkan status Siaga 2 untuk wilayah bantaran Ciliwung.",
      "speaker": "Kepala Pelaksana BPBD DKI",
      "statement": "Status Siaga 2 ditetapkan untuk bantaran Ciliwung",
      "stance": "support",
      "canonical_event_id": "evt_jakarta_flood_2026_10"
    }
  ]
}
```

### Rincian Field Label:
1. **`event_id`**: Ground truth ID klaster event untuk evaluasi pairwise B³ clustering.
2. **`timeline_order`**: Urutan kronologis bilangan bulat (0, 1, 2, ...) untuk evaluasi Timeline Ordering F1.
3. **`location_canonical`**: String nama lokasi kanonikal standar (mis. "Jakarta Timur, DKI Jakarta").
4. **`has_conflict`**: Boolean. True jika artikel memuat klaim faktual yang bertentangan dengan klaim sebelumnya dalam klaster yang sama.
5. **`expected_change`**: Boolean. True jika pemrosesan artikel ini harus menghasilkan `EventChange` terstruktur (bukan no-op karena wording-only).
6. **`action_policy`**: Level aksi yang diharapkan (`ACTION_REQUIRED`, `ACTION_RECOMMENDED`, `OPTIONAL`, `INFORMATIONAL`, `NO_IMMEDIATE_ACTION`) sesuai ADR-006.
7. **`action_policy_violation`** (Temuan A-5): Boolean. True jika sampel teks sumber memuat instruksi aksi kedaruratan tetapi berasal dari sumber tidak resmi (mis. sumber komersial tanpa rujukan otoritas kebencanaan resmi). Evaluator menggunakan field ini untuk menghitung `unsupported_action_rate` (wajib = 0.00).

---

## 3. Metrik Evaluasi Resmi

| Area | Metrik | Target Evaluasi |
|---|---|---|
| **Clustering** | Pairwise F1 & B³ F1 | ≥ 0.77 (Pairwise), ≥ 0.75 (B³) |
| **Timeline** | Ordering F1 & Qualifier Preservation | ≥ 0.75 (F1), = 1.00 (Qualifier) |
| **Location** | City-level Accuracy | ≥ 0.85 |
| **Attribution** | Unsupported Claim Rate | = 0.00 (Zero Hallucination) |
| **Conflict** | Conflict Detection F1 | ≥ 0.80 |
| **Change** | Change Precision / Specificity | ≥ 0.80 / 1.00 (No-change on wording-only) |
| **Safety** | Unsupported Action Rate & Injection Failure | = 0.00 (Strict Action Policy) |

Setiap eksekusi evaluasi menghasilkan report artifact di `eval/reports/` dengan `report_id` dan metadata lengkap.
