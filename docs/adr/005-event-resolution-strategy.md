# ADR-005: Event Resolution Strategy — Hybrid 3-Tier dengan Ablation

**Tanggal**: 2026-10-11
**Status**: Accepted
**Penulis**: Architecture Agent

---

## Konteks

Master Spec §14 mendefinisikan pipeline resolusi hibrida (deterministic + embeddings + Gemini). Addendum §6 memperinci: hard constraints, candidate retrieval, deterministic scoring, Gemini adjudication hanya untuk kandidat ambigu, dan penyimpanan decision records.

Keputusan penting: kapan Gemini dipanggil, dan apa yang dilakukan jika hasilnya ambigu?

## Keputusan

Implementasi **3-Tier Resolution Pipeline** (detail di [`D-event-resolution-algorithm.md`](../architecture/D-event-resolution-algorithm.md)):

### Tier 1 — Deterministic (selalu aktif)
- Hard constraints: lokasi, waktu, kategori
- Content deduplication (content-hash)
- Source family grouping (anti-inflation)
- Kandidat difilter secara deterministik

### Tier 2 — Embedding Retrieval (tambahan dari Tier 1)
- pgvector cosine similarity
- Composite score: semantic + time + location + entity
- Threshold rendah → SEPARATE_EVENT tanpa Gemini
- Threshold tinggi → SAME_EVENT tanpa Gemini
- Ambiguous range → lanjut ke Tier 3

### Tier 3 — Gemini Adjudication (hanya untuk kandidat ambigu)
- Gemini Call Type 2 (Adjudicate)
- Input mencakup semua sinyal deterministik dari Tier 1+2
- Output: SAME_EVENT | RELATED_EVENT | SEPARATE_EVENT | NEEDS_REVIEW

### Ablation Study Design
Tiga konfigurasi dijalankan terhadap gold dev set:
- `tier1`: hanya deterministic
- `tier2`: tier1 + embeddings
- `tier3`: tier1 + tier2 + Gemini (full)

### Default Safety Rule
Jika evidence ambigu: default ke **SEPARATE_EVENT** atau **NEEDS_REVIEW**, bukan confident merge. False separation lebih aman dari false merge.

### Transitive Cluster Guard
Tidak membentuk cluster A→B→C transitif. Setiap artikel dicek terhadap canonical event evidence, bukan terhadap artikel lain dalam cluster.

## Alternatif yang Ditolak

- **Hanya LLM**: biaya tinggi, tidak reproducible, tidak dapat di-ablasi. Master Spec §14 dan Addendum §6 melarang ini.
- **Hanya embedding**: recall tinggi tapi precision rendah untuk false merges.
- **Hanya deterministic**: recall rendah untuk artikel yang ditulis berbeda tentang event yang sama.

## Konsekuensi

- Semua decision tersimpan di `EventMembershipAudit` dengan sinyal dan reason codes.
- Threshold di `config/resolver.yaml`, dikalibrasi terhadap labeled dev set sebelum Stage 05.
- Ablation study menghasilkan 3 evaluation reports → bukti kontribusi tiap komponen untuk competition.
- **RSK-06**: false merge risk; mitigated by default-to-separate dan hard constraints.
