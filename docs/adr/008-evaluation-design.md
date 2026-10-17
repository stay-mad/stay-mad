# ADR-008: Evaluation Design dan Gold Set Integrity

**Tanggal**: 2026-10-11
**Status**: Accepted
**Penulis**: Architecture Agent

---

## Konteks

Addendum §8 mendefinisikan syarat evaluasi yang ketat:
- Gold set harus dibangun **sebelum** pipeline production dinyatakan complete.
- Evaluator buta: tidak membaca/memodifikasi `eval/gold/` saat blind run.
- Metrics wajib: pairwise/B³ clustering, timeline ordering, location, attribution, conflict, change, safety.
- Competition demo hanya mengutip angka dari evaluation report artifact.
- "Never display a metric without its report artifact."

## Keputusan

### 1. Struktur Direktori Evaluasi

```
eval/
  gold/
    train/           # kalibrasi threshold saja
    dev/             # ablation study (bisa dibaca agent)
    test/            # blind evaluation (HANYA evaluator runner)
    annotation-guide.md
    schema.json
  fixtures/
    seed_demo_23.json     # 23 artikel demo
  reports/
    YYYYMMDD-HHMMSS-<commit>.json
  runner/
    evaluate.py      # blind runner; membaca test/ hanya via explicit flag
```

### 2. Isolasi Gold Set

- `eval/gold/test/` tidak diakses oleh application code.
- CI check: grep application imports untuk path `eval/gold/test/`.
- Evaluator runner hanya dijalankan secara eksplisit dengan `make eval-blind`.
- Setiap `make eval-blind` run menghasilkan report baru di `eval/reports/`.

### 3. Annotation Protocol

Setiap artikel di gold set memiliki label:
- `event_id`: event yang benar (ground truth clustering)
- `timeline_order`: urutan kronologis yang diharapkan
- `location_canonical`: lokasi terkanonikalisasi
- `has_conflict`: boolean
- `expected_change`: boolean (apakah update menghasilkan change set)
- `action_policy`: expected actionability level

### 4. Continuous Evaluation Schedule

| Stage | Set | Ablation |
|---|---|---|
| Stage 02 | Setup gold labels, train/dev/test split | — |
| Stage 03 | eval/fixtures/ (23 artikel) | tier1 |
| Stage 04 | eval/gold/dev/ | tier1 + tier2 |
| Stage 05 | eval/gold/dev/ | tier1 + tier2 + tier3 (full) |
| Stage 08 | eval/gold/test/ (blind) | tier3 (final) |

### 5. Report Immutability

Setelah `make eval-blind` dijalankan, report disimpan di `eval/reports/` dan di-commit ke repo. Report tidak boleh dimodifikasi. Competition demo hanya mengutip report yang sudah ada.

### 6. Acceptance Tests Terpisah dari Gold Evaluation

8 acceptance scenarios (test_acc_01..test_acc_08) berjalan terhadap `eval/fixtures/seed_demo_23.json`, bukan gold set. Ini adalah regression tests yang dapat dijalankan kapan saja.

## Konsekuensi

- **RSK-12**: gold leakage adalah risiko kritis; isolasi path adalah kontrol utama.
- Train set boleh dibaca oleh pipeline untuk threshold calibration.
- Dev set boleh dibaca untuk iterasi development.
- Test set: hanya evaluator runner, hanya dengan flag eksplisit.
- Semua metrik di competition README harus memiliki `report_id` yang dapat ditelusuri.
