# ADR-006: Actionability Policy dan Source Gating

**Tanggal**: 2026-10-11
**Status**: Accepted
**Decided by**: Susi (human)
**Decision date**: 2026-10-12
**Penulis**: Architecture Agent
**Konflik Diselesaikan**: decisions.md Conflict #2

---

## Konteks

**Konflik #2**: Master Spec §22 memberikan contoh aksi `"Check on vulnerable family members"`. Addendum §5.6 menyatakan: `ACTION REQUIRED` dan `ACTION RECOMMENDED` **wajib** dari sumber resmi darurat/pemerintah. Saran keselamatan tidak boleh dikarang.

Contoh di Master Spec melanggar kontrak Addendum: "Check on vulnerable family members" adalah saran umum yang tidak berasal dari sumber resmi spesifik.

Tambahan: Addendum §8 menyatakan "The unsupported-action rate must be zero."

## Keputusan (PROPOSED — butuh persetujuan user)

### Opsi A — Source Gating Ketat (Recommended)

Implementasi gating rules di `H-actionability-algorithm.md`:

1. `ACTION REQUIRED` / `ACTION RECOMMENDED`: **hanya** dari sumber dengan `source_family ∈ {GOV_BMKG, GOV_BPBD_DKI, GOV_BNPB, GOV_SETKAB}` dan `source_tier = TIER_1`.
2. Teks aksi wajib ada verbatim claim reference (`evidence_claim_ids` non-kosong dari sumber authorized).
3. Contoh Master Spec §22 "Check on vulnerable family members" **digunakan sebagai kasus uji negatif** — sistem harus mengklasifikasikannya sebagai `INFORMATIONAL` atau `NO_IMMEDIATE_ACTION`, bukan `ACTION REQUIRED`.
4. Fallback: jika tidak ada sumber resmi → `NO_IMMEDIATE_ACTION` atau `INFORMATIONAL`.

### Opsi B — Inferensi Diizinkan dengan Label

Izinkan saran umum tapi wajib dilabel "Saran Umum (bukan dari sumber resmi)" dan dikategorikan `OPTIONAL`.

### Opsi C — Hilangkan Fitur Actionability Sepenuhnya dari MVP

Terlalu ketat; mengurangi nilai produk.

---

## Dampak pada Fixture

Fixture 23 artikel saat ini harus diverifikasi:
- Setiap `Action` record dengan level REQUIRED/RECOMMENDED harus memiliki `evidence_claim_ids` ke klaim dari `GOV_*` source.
- `art_demo_07` (artikel dengan prompt injection) menjadi kasus uji negatif untuk aksi tidak sah.
- `test_acc_06_prompt_injection_safety` mencakup: tidak ada `ACTION REQUIRED` dari sumber non-resmi.

---

## Rekomendasi

**Opsi A** direkomendasikan. Ini satu-satunya opsi yang memenuhi Addendum §5.6 dan target `unsupported_action_rate = 0.00`.

**User perlu memutuskan**:
1. Apakah daftar `authorized_source_families` lengkap atau perlu tambahan sumber?
2. Apakah media Tier 2 yang mengutip pernyataan resmi (mis. ANTARA mengutip pernyataan BPBD) dapat qualify?

Saat ini: hanya source langsung yang qualify. Klaim yang di-rebroadcast oleh media Tier 2 dikembalikan ke sumber aslinya (ANTARA sebagai wire copy → klaim diatribusikan ke ANTARA, tidak ke sumber yang dikutip ANTARA, kecuali ada mekanisme attribution yang jelas).


## Keputusan User

**Dipilih: Opsi A**
**Alasan**: Sesuai dengan yang direkomendasikan dan ini satu-satunya opsi yang memenuhi Addendum §5.6 dan target `unsupported_action_rate = 0.00`
**User perlu memutuskan**:
1. Apakah daftar `authorized_source_families` lengkap atau perlu tambahan sumber? 
Jawab: Perlu ada tambahan sumber seperti dari tempo.co, kompas.com, dan cnbc indonesia
2. Apakah media Tier 2 yang mengutip pernyataan resmi (mis. ANTARA mengutip pernyataan BPBD) dapat qualify?
Jawab: ya qualify