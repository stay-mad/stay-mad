# ADR-003: Database Schema Strategy

**Tanggal**: 2026-10-11
**Status**: Accepted
**Penulis**: Architecture Agent

---

## Konteks

Addendum §9 mendefinisikan 14 entity wajib. Master Spec §38 mendefinisikan 10 entity. Ada 2 entity di Master Spec yang tidak ada di Addendum (ProcessingJob, EventRelation) dan beberapa entity baru di Addendum (ArticleVersion, EventSnapshot, EventChange, EventMembershipAudit, Conflict, ProcessingRun).

`decisions.md` Conflict #8 mengambil gabungan: keduanya dibutuhkan.

## Keputusan

**Ambil gabungan** semua entity dari kedua spec:

1. **ArticleVersion** (Addendum) — immutable capture, bukan overwrite
2. **EventSnapshot** (Addendum) — immutable published representation
3. **EventChange** (Addendum) — structured change tracking
4. **EventMembershipAudit** (Addendum) — decision record per article-event membership
5. **Conflict** (Addendum) — explicit conflict record
6. **ProcessingRun** (Addendum) — provenance metadata
7. **ProcessingJob** (Master Spec §38) — work queue unit (beda fungsi dari ProcessingRun)
8. **EventRelation** (Master Spec §38) — hanya `related_to` di MVP, hanya jika ada kebutuhan UI yang visible

Schema detail di [`B-data-model.md`](../architecture/B-data-model.md).

### Prinsip Skema

- **Append-only evidence**: klaim, ArticleVersion, EventSnapshot tidak pernah di-overwrite.
- **Immutable records**: pembaruan menghasilkan versi baru, bukan mutasi.
- **Provenance fields wajib**: setiap record memiliki `processing_run_id`, `schema_version`, `model_version`.
- **Enum perubahan via ADR**: enum baru atau perubahan enum memerlukan ADR + migration.

## Alternatif yang Ditolak

- **Hanya schema Addendum** (tanpa ProcessingJob dan EventRelation): ProcessingJob diperlukan sebagai unit kerja antrean yang berbeda dari ProcessingRun sebagai rekaman provenance.
- **Hanya schema Master Spec**: kehilangan immutability contract, change tracking, dan audit trail yang diperlukan Addendum.

## Konsekuensi

- Migration menggunakan Alembic; setiap perubahan schema memerlukan migration file.
- Unit test schema menggunakan test database terpisah.
- `EventRelation` diimplementasi kosong (tabel ada, tidak digunakan) sampai ada kebutuhan UI visible.
- **RSK-13**: Schema stability adalah kontrak lintas agent; perubahan tanpa ADR adalah pelanggaran.
