# Sources Allowlist & Policy (docs/sources.md)

Dokumen ini mendefinisikan seluruh sumber terverifikasi (*trusted sources*) yang diperbolehkan untuk diserap oleh sistem Stay Mad.
Sesuai dengan aturan di `AGENTS.md` dan Addendum, **sumber di luar daftar ini akan ditolak secara default** oleh modul `ingest`.

---

## 1. Tabel Kebijakan Sumber Terverifikasi

| Nama | URL | Tipe | Source Tier | Source Family | Catatan Lisensi / ToS | Robots.txt | Rate Limit | Aturan Retensi |
|---|---|---|---|---|---|---|---|---|
| **BMKG (Data Terbuka)** | `https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json` | API | `Tier 1` | `GOV_BMKG` | Domain publik / data terbuka pemerintah RI. Wajib atribusi BMKG. | Tidak ada larangan endpoint data publik (`*`). | Maks 60 req/menit (Cache 60s di sisi klien). | Simpan nilai parameter cuaca/gempa dan metadata secara permanen. |
| **BPBD DKI Jakarta** | `https://bpbd.jakarta.go.id/berita` | Resmi | `Tier 1` | `GOV_BPBD_DKI` | Portal informasi resmi Pemprov DKI Jakarta (UU KIP). Informasi keselamatan publik. | `Allow: /` untuk halaman publik berita. | Maks 20 req/menit. | Simpan status siaga, wilayah terdampak, dan kutipan rilis resmi. Teks penuh retensi 30 hari. |
| **BNPB Indonesia** | `https://bnpb.go.id/berita` | Resmi | `Tier 1` | `GOV_BNPB` | Informasi resmi kebencanaan nasional. Hak cipta BNPB RI, penggunaan wajar untuk kepentingan publik. | Mematuhi Cloudflare challenge / WAF bila diakses otomatis. | Maks 15 req/menit. | Simpan nomor siaran pers, data korban/kerusakan, dan tautan resmi. |
| **Sekretariat Kabinet RI** | `https://setkab.go.id/berita` | Resmi | `Tier 1` | `GOV_SETKAB` | Publikasi resmi kebijakan dan regulasi pemerintah RI. Domain publik / UU KIP. | `Allow: /` (X-Robots-Tag: nofollow). | Maks 20 req/menit. | Simpan nomor regulasi, ringkasan kebijakan, kutipan resmi, dan URL rilis. Teks penuh retensi 30 hari. |
| **LKBN ANTARA** | `https://www.antaranews.com/rss/terkini.xml` | RSS | `Tier 1` | `LKBN_ANTARA` | Kantor Berita Nasional BUMN. Penggunaan RSS publik untuk agregasi judul dan cuplikan wajar. | `Allow: /`, disallow: `/api/`, `/ajax/`. | Maks 30 req/menit. | Simpan judul, timestamp, cuplikan ringkas, klaim kutipan, dan URL asli. Teks penuh dihapus setelah 7 hari. |
| **CNN Indonesia** | `https://www.cnnindonesia.com/nasional/rss` | RSS | `Tier 2` | `TRANSMEDIA` | Lisensi Transmedia / WarnerMedia. RSS publik untuk konsumsi berita nasional. | `Allow: /`, mematuhi TTL RSS (cache-control: max-age=30). | Maks 20 req/menit. | Simpan metadata, klaim terverifikasi, dan URL sumber. Jangan reproduksi teks artikel utuh. |
| **Detikcom** | `https://news.detik.com/berita/rss` | RSS | `Tier 2` | `TRANSMEDIA` | Lisensi Transmedia. Satu grup editorial dengan CNN Indonesia. | `Allow: /`, mematuhi aturan crawling standar. | Maks 20 req/menit. | Simpan metadata dan kutipan bukti klaim. Sindikasi dengan CNN Indonesia dikelompokkan ke `TRANSMEDIA`. |
| **Republika** | `https://republika.co.id/rss` | RSS | `Tier 2` | `MAHAKA_MEDIA` | Lisensi Mahaka Media. Feed publik berita umum dan nasional. | `Allow: /`. | Maks 20 req/menit. | Simpan metadata, klaim, dan URL asli. |
| **Tempo.co** | `https://rss.tempo.co/nasional` | RSS | `Tier 2` | `TEMPO_INTI_MEDIA` | Lisensi Tempo Inti Media. RSS publik untuk agregasi berita nasional dan investigasi. | `Allow: /`, patuhi batasan robots.txt standar Tempo. | Maks 20 req/menit. | Simpan metadata, ringkasan klaim, dan URL asli. Dilarang scrape artikel penuh tanpa izin sindikasi. |
| **Kompas.com** | `https://news.kompas.com/rss` | RSS | `Tier 1` | `KOMPAS_GRAMEDIA` | Lisensi KG Media. Feed publik berita umum dan nasional kompas.com. | `Allow: /`, patuhi crawling-delay dan header cache. | Maks 20 req/menit. | Simpan metadata, kutipan bukti klaim, dan URL rujukan utama. Jangan menyalin teks lengkap. |
| **CNBC Indonesia** | `https://www.cnbcindonesia.com/news/rss` | RSS | `Tier 2` | `TRANSMEDIA` | Lisensi Transmedia / NBCUniversal. Feed publik berita ekonomi, pasar, dan nasional. | `Allow: /`, mematuhi TTL RSS (cache-control: max-age=30). | Maks 20 req/menit. | Simpan metadata, klaim data/berita, dan URL sumber. Sindikasi dikelompokkan ke `TRANSMEDIA`. |

---

## 2. Aturan Source Independence & Anti-Inflation
1. **Grouping Konglomerasi (`source_family`)**:
   - Sumber yang berada dalam payung grup media yang sama (misalnya Detikcom dan CNN Indonesia di bawah `TRANSMEDIA`) dikelompokkan ke dalam satu `source_family`.
   - Artikel bersumber dari keluarga yang sama **tidak dihitung sebagai laporan independen terpisah** dalam kalkulasi konsensus atau skor keyakinan (*confidence score*).
2. **Sindikasi Kantor Berita**:
   - Jika media Tier 2 menerbitkan ulang naskah dari LKBN ANTARA (misal tercantum "Dikutip dari Antara"), klaim diatribusikan kembali ke entitas LKBN ANTARA dan dianggap satu bukti primer.

---

## 3. Kebijakan Retensi Konten & Hak Cipta
- **Tidak Menyimpan Salinan Utuh**: Stay Mad tidak pernah mempublikasikan ulang atau menyimpan artikel lengkap secara permanen.
- **Penyimpanan Minimal**: Sistem hanya menyimpan:
  - Judul artikel & URL permanen asli.
  - Waktu publikasi & waktu pembaruan (*published_time*, *updated_time*).
  - Kutipan klaim verbatim singkat (< 200 karakter per klaim) yang digunakan sebagai referensi bukti (*evidence span*).
  - Metadata nama entitas, waktu peristiwa, dan lokasi.
- **Tautan Asli**: Antarmuka pengguna wajib menyediakan tautan langsung ke artikel asli di situs penerbit.
