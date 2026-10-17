# K. Risk Register — Stay Mad §53-K

> Risk register lengkap. Diperbarui di setiap handoff stage.
> Tambah risiko baru via PR ke file ini; ubah severity via ADR jika mempengaruhi kontrak.

---

## Tabel Risiko

| ID | Risiko | Dampak | Probabilitas | Severity | Mitigasi | Status |
|---|---|---|---|---|---|---|
| RSK-01 | **Hallucination klaim Gemini** — Model menghasilkan klaim yang tidak ada di teks sumber | Tinggi | Sedang | Kritis | Validasi `source_span` verbatim (fuzzy ≥ 85% match di excerpt); schema output JSON terstruktur; prompt menekankan "hanya dari teks yang diberikan" | Open |
| RSK-02 | **Ingest flooding / rate limiting** — Sumber memblokir permintaan karena frekuensi tinggi | Sedang | Tinggi | Tinggi | Adaptive backoff, rate limiter per sumber di `config/sources.yaml`; queue/dead-letter di `jobs` module | Open |
| RSK-03 | **Ambiguitas resolusi entitas** — Nama yang sama merujuk orang/tempat berbeda | Tinggi | Rendah | Sedang | Resolusi multi-konteks berbasis embedding + atribut jabatan/waktu; hard constraint geographic | Open |
| RSK-04 | **Poisoned / spoofed source feed** — Feed palsu atau dimanipulasi dari domain yang terlihat valid | Kritis | Rendah | Kritis | Validasi domain allowlist ketat; verifikasi TLS; checksum konten jika tersedia; alert jika URL menyimpang dari pola sumber | Open |
| RSK-05 | **Prompt injection via artikel** — Teks artikel mengandung instruksi ke sistem | Tinggi | Sedang | Kritis | Teks artikel dikemas dalam `<article_data>` delimitir; schema output JSON mencegah eksekusi instruksi; `test_acc_06` memverifikasi ini | Open |
| RSK-06 | **False merge (incorrect clustering)** — Dua event berbeda digabungkan menjadi satu | Tinggi | Sedang | Tinggi | Hard constraints (lokasi, waktu, kategori) sebelum Gemini; default ke SEPARATE_EVENT jika ambigu; EventMembershipAudit untuk audit trail | Open |
| RSK-07 | **Temporal errors** — Waktu kejadian vs waktu dilaporkan tertukar | Sedang | Sedang | Sedang | Prompt Gemini menekankan perbedaan `event_time` vs `published_time`; precision qualifier wajib; evaluasi `timestamp_coverage` metric | Open |
| RSK-08 | **Source reliability degradation** — Sumber Tier 1 menerbitkan informasi tidak akurat | Tinggi | Rendah | Tinggi | Tier system (Tier 1 mendapat bobot lebih tinggi); corroboration requirement; konflik diekspos ke pengguna bukan disembunyikan | Open |
| RSK-09 | **Data sparsity** — Kejadian di daerah terpencil atau di luar jam kerja tidak tercakup | Sedang | Sedang | Sedang | Fallback `evidence_status = INSUFFICIENT`; tampilkan kejadian dengan confidence LOW tetap; jangan buat klaim fiktif | Open |
| RSK-10 | **Biaya Gemini tak terduga** — Volume artikel tinggi menyebabkan billing spike | Tinggi | Sedang | Tinggi | Cache deterministik per (article_version_id, prompt_version, schema_version); dedup sebelum ekstraksi; cost estimate per ProcessingRun; budget alert di GCP | Open |
| RSK-11 | **Latensi tinggi** — Gemini calls lambat menyebabkan pipeline tertunda | Sedang | Sedang | Sedang | Async processing (user tidak menunggu Gemini); timeout 300s per job; dead-letter untuk retry; monitoring p95/p99 latency | Open |
| RSK-12 | **Data leakage ke gold set** — Evaluator atau pipeline membaca eval/gold/test/ selama inferensi | Kritis | Rendah | Kritis | eval/gold/ tidak boleh diakses oleh application code; evaluator runner memiliki path eksplisit ke gold; CI check untuk path imports | Open |
| RSK-13 | **Scraping/legal risk** — Ingest dari sumber di luar allowlist atau melanggar ToS | Tinggi | Rendah | Tinggi | Domain allowlist wajib di `config/sources.yaml`; startup check; robots.txt compliance per sumber; dokumentasi kebijakan di `docs/sources.md` | Open |
| RSK-14 | **Deployment risk** — Cloud Run startup failure karena misconfigured secrets atau DB connection | Sedang | Sedang | Sedang | `GET /health` diuji sebelum traffic dialihkan; startup failure jika fixture mode di production; Alembic migration diverifikasi sebelum deploy | Open |
| RSK-15 | **Unsupported action generation** — ACTION REQUIRED dihasilkan tanpa sumber resmi | Kritis | Rendah | Kritis | Source gating di H-actionability-algorithm.md; post-processing validation; `unsupported_action_rate` target = 0.00 di evaluasi | Open |
| RSK-16 | **Fixture mode di production** — Developer lupa mematikan `GEMINI_FIXTURE_MODE` | Tinggi | Rendah | Kritis | Startup check wajib: jika `ENVIRONMENT=production` dan `GEMINI_FIXTURE_MODE=true` → aplikasi menolak start | Open |
| RSK-17 | **Transitive false cluster** — A≈B dan B≈C menyebabkan A,C digabung padahal tidak terkait | Sedang | Sedang | Sedang | Setiap artikel dicek terhadap canonical event evidence, bukan terhadap cluster anggota; Transitive Cluster Guard di resolver | Open |
| RSK-18 | **Copyright/retention violation** — Full article text disimpan melebihi batas retention | Tinggi | Rendah | Tinggi | `full_text_expires_at` per ArticleVersion; scheduled cleanup job; hanya excerpt ≤ 500 karakter yang dikirim ke Gemini | Open |

---

## Severity Matrix

| | Dampak Rendah | Dampak Sedang | Dampak Tinggi |
|---|---|---|---|
| **Probabilitas Rendah** | Rendah | Sedang | Tinggi |
| **Probabilitas Sedang** | Sedang | Tinggi | Kritis |
| **Probabilitas Tinggi** | Tinggi | Kritis | Kritis |

---

## Risiko Kritis (Memerlukan Perhatian Segera)

| ID | Risiko | Tindakan Diperlukan |
|---|---|---|
| RSK-01 | Hallucination | Stage 03: evaluasi verbatim match rate |
| RSK-04 | Poisoned feed | Stage 04: implementasi domain validation |
| RSK-05 | Prompt injection | Stage 03: `test_acc_06` harus lulus |
| RSK-12 | Gold leakage | Stage 02: isolasi path eval/gold/ |
| RSK-15 | Unsupported action | Stage 05: evaluasi unsupported_action_rate = 0.00 |
| RSK-16 | Fixture in production | Stage 07: startup check dalam CI |

---

## Pembaruan Risk Register

Setiap handoff stage wajib:
1. Update kolom `Status` (Open → Mitigated/Accepted/Resolved)
2. Tambah risiko baru yang ditemukan selama stage
3. Catat di `docs/handoffs/NN-<stage>.md`
