# ADR-007: Gemini Model Selection dan Embedding Strategy

**Tanggal**: 2026-10-11
**Status**: Accepted
**Decided by**: Susi (human)
**Decision date**: 2026-10-12
**Penulis**: Architecture Agent

---

## Konteks

Addendum §9 menyatakan: "Select the Gemini model at implementation time from current official Google documentation, document the choice in an ADR, and put it behind configuration such as `GEMINI_MODEL`."

`decisions.md` baris terakhir menyatakan: "Gemma opsional. Master Spec bilang 'Gemini/Gemma where appropriate'. Jangan masukkan Gemma sampai ada alasan terukur."

Master Spec §14 dan §37 menyebutkan embedding sebagai bagian strategi hibrida. Embedding dibutuhkan untuk Tier 2 resolution.

## Keputusan (PROPOSED — butuh persetujuan user)

### Model Gemini

| Use Case | Model Candidate | Catatan |
|---|---|---|
| Extract, Adjudicate, Synthesize | `gemini-2.0-flash` | Direkomendasikan: biaya rendah, latensi baik, structured output support |
| Alternatif jika quota tidak cukup | `gemini-1.5-flash` | Fallback |
| Alternatif premium (jika diperlukan) | `gemini-2.0-pro` | Biaya lebih tinggi; perlu evaluasi cost-benefit |

**Rekomendasi awal**: `gemini-2.0-flash` untuk semua 3 call types (Extract, Adjudicate, Synthesize).

Model dipilih **definitif** saat implementasi Stage 03, berdasarkan:
- Ketersediaan API key + quota
- Uji coba structured output dengan schema yang diusulkan
- Evaluasi cost estimate

### Embedding Model

| Kandidat | Dimensi | Catatan |
|---|---|---|
| `text-embedding-004` (Google) | 768 | Recommended; support pgvector |
| `text-multilingual-embedding-002` | 768 | Lebih baik untuk teks Bahasa Indonesia |

**Rekomendasi**: `text-multilingual-embedding-002` karena konten mayoritas Bahasa Indonesia.

Pilihan final dikonfirmasi saat Stage 03 dengan benchmark pada sample teks Indonesia.

### Gemma

**Tidak digunakan di MVP**. Alasan:
- Tidak ada kebutuhan on-device atau offline inference saat ini.
- Biaya Gemini Flash sudah terjangkau untuk volume MVP.
- Jika di masa depan ada alasan terukur (mis. ekstraksi murah untuk Tier 2 sumber bervolume tinggi), buat ADR baru.

### Konfigurasi

```env
GEMINI_MODEL=gemini-2.0-flash     # dari Secret Manager
EMBEDDING_MODEL=text-multilingual-embedding-002  # dari Secret Manager
```

---

## Open Questions untuk User

1. **Model Gemini**: Setujui `gemini-2.0-flash` sebagai default? Atau ada preferensi lain?
2. **Embedding**: Setujui `text-multilingual-embedding-002`? Atau cukup `text-embedding-004`?
3. **Gemma**: Konfirmasi tidak digunakan di MVP? (Sesuai rekomendasi `decisions.md`)

---

## Konsekuensi

- `GEMINI_MODEL` dan `EMBEDDING_MODEL` adalah required env vars; startup validation harus memeriksa keduanya.
- Startup gagal jika `GEMINI_API_KEY` tidak valid di production mode.
- Model version dicatat di setiap `Claim`, `EventMembershipAudit`, dan `EventSnapshot` untuk reprodusibilitas evaluasi.
- Perubahan model version membutuhkan re-extraction dan re-evaluation (cache invalidation otomatis via `model_version` di cache key).

## Keputusan User

**Dipilih: model gemini = gemini-2.0-flash dan embedding model = text-multilingual-embedding-002**
## Open Questions untuk User
1. **Model Gemini**: Setujui `gemini-2.0-flash` sebagai default? Atau ada preferensi lain?
Jawab: Setuju untuk menggunakan gemini-2.0-flash
2. **Embedding**: Setujui `text-multilingual-embedding-002`? Atau cukup `text-embedding-004`?
Jawab: Setuju untuk menggunakan text-multilingual-embedding-002
3. **Gemma**: Konfirmasi tidak digunakan di MVP? (Sesuai rekomendasi `decisions.md`)
Jawab: Konfirmasi tidak digunakan di MVP