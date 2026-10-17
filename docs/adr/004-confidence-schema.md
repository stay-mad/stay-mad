# ADR-004: Confidence Schema — Numeric Score + Evidence Status + Verification Level

**Tanggal**: 2026-10-11
**Status**: Accepted
**Decided by**: Susi (human)
**Decision date**: 2026-10-12
**Penulis**: Architecture Agent
**Konflik Diselesaikan**: decisions.md Conflict #1 dan #3

---

## Konteks

Tiga sistem confidence yang tumpang tindih ditemukan:

1. **Master Spec §19**: Confidence = `HIGH | MEDIUM | LOW` (3 enum)
2. **Addendum §5**: `confidence_score` numerik + `evidence_status` (`SUPPORTED | CONFLICTING | INSUFFICIENT | RETRACTED`) + `verification_level` (`OFFICIAL_PRIMARY | INDEPENDENTLY_CORROBORATED | SINGLE_SOURCE`)
3. **Master Spec §12**: Status klaim = `CONFIRMED | SUPPORTED | UNCONFIRMED | CONFLICTING | UNKNOWN`

`decisions.md` Conflict #3 mengusulkan: "confidence_score numerik adalah sumber kebenaran. HIGH/MEDIUM/LOW hanya bucket tampilan dengan ambang di config."

**Conflict #1 terkait**: Addendum §5 menyatakan importance, urgency, dan confidence harus **terpisah**. Master Spec §21 memasukkan confidence 10% ke dalam importance formula. Ini bertentangan.

## Keputusan (PROPOSED — butuh persetujuan user)

### Opsi A — Implementasi Usulan (Recommended)

Pisahkan ketiga concern:

1. **`confidence_score`** (float 0.0–1.0): sumber kebenaran numerik untuk confidence. Dihitung dari 5 komponen (lihat §53-F).
2. **`confidence_bucket`** (HIGH/MEDIUM/LOW): derived field, hanya untuk UI display. Threshold di `config/confidence.yaml`.
3. **`evidence_status`** (SUPPORTED/CONFLICTING/INSUFFICIENT/RETRACTED): menggantikan CONFIRMED/UNCONFIRMED/UNKNOWN dari Master Spec §12 untuk status **event-level**.
4. **`verification_level`** (OFFICIAL_PRIMARY/INDEPENDENTLY_CORROBORATED/SINGLE_SOURCE): tingkat verifikasi sumber.
5. **Importance formula** tidak memasukkan confidence (sesuai Addendum §5).

Status klaim individual (CONFIRMED/SUPPORTED/UNCONFIRMED dari Master Spec §12) **tidak digunakan** di level event — digantikan oleh evidence_status + verification_level. Label CONFIRMED dari Master Spec di-map: CONFIRMED → evidence_status=SUPPORTED + verification_level=OFFICIAL_PRIMARY.

### Opsi B — Kompatibilitas Penuh

Pertahankan semua 3 set enum, dengan mapping tabel dari satu ke lain. Lebih kompleks, risiko inconsistency.

### Opsi C — Hanya Numerik

Hapus semua enum label; tampilkan hanya angka. Kurang user-friendly untuk UI Indonesia.

---

## Mapping Table (Opsi A)

| evidence_status | verification_level | confidence_bucket | Kondisi |
|---|---|---|---|
| SUPPORTED | OFFICIAL_PRIMARY | HIGH | Ada sumber resmi GOV_* + score ≥ 0.70 |
| SUPPORTED | INDEPENDENTLY_CORROBORATED | HIGH/MEDIUM | ≥ 2 source families + score ≥ 0.45 |
| SUPPORTED | SINGLE_SOURCE | MEDIUM/LOW | 1 sumber saja |
| CONFLICTING | * | LOW/MEDIUM | Ada Conflict record yang belum resolved |
| INSUFFICIENT | SINGLE_SOURCE | LOW | Klaim terlalu sedikit |
| RETRACTED | — | — | Artikel diretraksi |

---

## Konsekuensi (Opsi A)

**Positif**:
- Satu sumber kebenaran (numerik).
- Enum legacy (CONFIRMED/UNCONFIRMED) dihapus; tidak ada ambiguitas.
- Confidence tidak mempengaruhi importance; event uncertain tetap visible.

**Negatif**:
- Agent lain yang sudah menulis kode berdasarkan CONFIRMED/UNCONFIRMED harus diupdate.
- Mapping tabel perlu diuji dengan evaluasi.

---

## Rekomendasi

**Opsi A** direkomendasikan karena sesuai Addendum §5 dan menyelesaikan kedua konflik (#1 dan #3) secara bersih.

**User perlu memutuskan**: apakah Opsi A disetujui sebelum Stage 02 (Data Contract Agent) menulis schema?

## Keputusan User

**Dipilih: Opsi A**
**Alasan**: Sesuai dengan yang direkomendasikan berdasarkan Addendum §5 dan menyelesaikan kedua konflik (#1 dan #3) secara bersih.
**Ditolak**: Opsi B (risiko inkonsistensi antar tiga set enum), Opsi C (melanggar Addendum §5.4 yang mewajibkan enum berlabel).
**Dampak ke dokumen lain**: OpenAPI (field baru X), config/confidence.yaml, acceptance-matrix (kasus uji Y).
**Dampak migrasi**: tidak ada kode/skema sebelumnya; skema Stage 02 dibuat langsung dari ADR ini.