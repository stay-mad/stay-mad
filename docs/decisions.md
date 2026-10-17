# Keputusan Arsitektur & Produk (decisions.md)

Dokumen ini mencatat keputusan-keputusan eksplisit yang diambil selama pengembangan Stay Mad. Sesuai dengan aturan otoritas di `AGENTS.md`, urutan otoritas adalah: `ADR / decisions.md` > `Addendum` > `Master Spec` > asumsi mandiri.

---

## Log Keputusan

### DEC-0001: Bahasa Produk dan Zona Waktu Default
- **Tanggal**: 2026-10-11
- **Status**: Diterima
- **Konteks**: Sistem berfokus pada wilayah Indonesia dan wilayah metropolitan Jakarta pada rilis MVP.
- **Keputusan**: 
  - Bahasa produk untuk UI, label, dan penyajian ringkasan adalah **Bahasa Indonesia**.
  - Teks sumber berbahasa Inggris dapat diproses dengan mempertahankan bahasa asli dan tautan sumber.
  - Zona waktu tampilan default adalah **`Asia/Jakarta` (WIB)**. Timestamp internal disimpan dalam ISO-8601 UTC.
- **Konsekuensi**: Semua konversi waktu untuk UI harus mengacu pada `Asia/Jakarta` dan mempertahankan kualifikasi temporal asli ("sekitar 08:30").

---

### DEC-0002: Batasan Lingkup MVP (Bounded MVP)
- **Tanggal**: 2026-10-11
- **Status**: Diterima
- **Konteks**: Master Spec mendefinisikan 10 kategori, namun Addendum membatasi rilis pertama agar dapat diverifikasi secara mendalam.
- **Keputusan**: 
  - MVP hanya mengimplementasikan 3 kategori utama:
    1. *Disaster & Weather* (Bencana & Cuaca)
    2. *Transportation & Infrastructure* (Transportasi & Infrastruktur)
    3. *Government & Public Policy* (Pemerintah & Kebijakan Publik)
  - Taksonomi tetap dibuat extensible untuk 7 kategori lainnya, namun belum diklaim sebagai production-ready.
- **Konsekuensi**: Evaluasi dan fixture tahap awal hanya fokus pada 3 domain ini.

---

### DEC-0003: Kebijakan Sumber Ketat (Strict Sourcing Allowlist)
- **Tanggal**: 2026-10-11
- **Status**: Diterima
- **Konteks**: Menghindari web scraping liar, pelanggaran ToS, dan risiko data palsu/halusinasi.
- **Keputusan**: 
  - Penyerapan data dibatasi hanya pada daftar terverifikasi di `docs/sources.md` dan `config/sources.yaml`.
  - Sumber dikelompokkan ke dalam Tier (Tier 1: Resmi Pemerintah/Bencana & Kantor Berita Nasional Terakreditasi; Tier 2: Media Nasional Kredibel).
  - Setiap sumber mencatat `source_family` untuk mengidentifikasi sindikasi/konglomerasi media agar tidak menggelembungkan skor konsensus independen.
  - Tidak melakukan scraping tanpa persetujuan, mematuhi robots.txt, rate limit, dan kebijakan retensi minimal.
- **Konsekuensi**: Domain di luar allowlist akan ditolak saat tahap `ingest`.

---

### DEC-0004: Penanganan Input Artikel Sebagai Data Tidak Terpercaya (Anti-Prompt Injection)
- **Tanggal**: 2026-10-11
- **Status**: Diterima
- **Konteks**: Artikel berita atau feed pihak ketiga berpotensi mengandung teks injeksi instruksi (prompt injection).
- **Keputusan**: 
  - Semua teks artikel dan RSS diperlakukan murni sebagai data pasif, bukan instruksi sistem.
  - Gemini hanya menerima teks artikel di dalam penampung data terisolasi dengan skema output JSON yang terstruktur dan tervalidasi.
  - Sistem tidak pernah mengeksekusi instruksi yang tertanam di dalam artikel.
  - Pembuatan aksi darurat (`ACTION REQUIRED`) diwajibkan berasal dari sumber resmi institusional (BPBD, BNPB, BMKG, Polisi/Pemerintah), bukan dari opini/kutipan lepas media.
- **Konsekuensi**: Prompt injection dalam artikel akan gagal mengarahkan perilaku sistem.

---

### DEC-0005: Model Persistensi: Versi Artikel dan Snapshot Peristiwa
- **Tanggal**: 2026-10-11
- **Status**: Diterima
- **Konteks**: Peristiwa dunia nyata terus berkembang dan artikel sering kali diperbarui.
- **Keputusan**: 
  - `ArticleVersion`: Penangkapan artikel bersifat immutable. Pembaruan berita menghasilkan versi baru tanpa menghapus bukti lama.
  - `EventSnapshot`: Representasi event yang diterbitkan bersifat snapshot immutable.
  - `EventChange`: Perubahan antar dua snapshot memicu record perubahan terstruktur (`ADDED`, `UPDATED`, `CORRECTED`, `RETRACTED`) yang mengikat klaim bukti baru.
  - Basis data menggunakan **PostgreSQL + pgvector** dalam pola Modular Monolith.
- **Konsekuensi**: Provenance dan riwayat "What Changed" dapat diverifikasi kapan saja tanpa merekayasa data masa lalu.

---

### DEC-0006: Larangan Hard-coding Angka UI & Larangan Adapter Fixture di Production
- **Tanggal**: 2026-10-11
- **Status**: Diterima
- **Konteks**: Sesuai aturan keras `AGENTS.md` dan evaluasi kompetisi AI.
- **Keputusan**: 
  - Setiap angka hitungan artikel, klaim, kandidat, konflik, sinyal kepercayaan, dan timeline pada UI harus berasal dari query data riil dengan `processing_run_id` yang valid.
  - Fixture adapter hanya diizinkan untuk unit test dan mode demo berlabel.
  - Dalam mode `production`, sistem harus gagal booting (startup failure) jika adapter fixture terdeteksi aktif atau jika kunci API Gemini tidak valid.
- **Konsekuensi**: Menjamin integritas teknis di hadapan juri.

---

### DEC-0007: Resolusi Konflik Kategori: Pemetaan Kebijakan Ekonomi ke Government & Public Policy
- **Tanggal**: 2026-10-11
- **Status**: Diterima (Arahan Eksplisit User)
- **Konteks**: 
  - Master Spec §30 mencantumkan seed Event D bertopik "kebijakan ekonomi" (6 artikel).
  - Addendum §2 menetapkan batasan keras 3 kategori MVP: *Disaster & Weather*, *Transportation & Infrastructure*, dan *Government & Public Policy*. Kategori *Economy* belum diaktifkan pada vertical slice MVP.
- **Keputusan**: 
  - Event D ("kebijakan ekonomi", seperti regulasi subsidi transportasi/energi pemerintah) secara resmi diklasifikasikan ke dalam kategori **`Government & Public Policy`**.
  - Ruang lingkup kategori tetap terkunci pada 3 kategori bounded MVP, dan seed 23 artikel tetap sepenuhnya mencakup 4 klaster Master Spec §30.
- **Konsekuensi**: Taksonomi evaluasi dan skema fixture untuk Event D menggunakan nilai enum kategori `government_and_public_policy`.

2. Konflik dan celah antara Master Spec dan Addendum
#	Master Spec	Addendum	Usulan resolusi (perlu persetujuanmu)
1	Importance memuat Confidence 10% dan Urgency 20% (§21)	Importance, urgency, dan confidence harus terpisah. Event berdampak tinggi tapi tidak pasti tidak boleh diturunkan diam-diam (Bagian 5)	Hitung importance tanpa confidence. Tampilkan confidence dan urgency sebagai field terpisah. Event dengan confidence rendah ditandai “uncertain” dan tidak diturunkan peringkatnya. Bobot tetap di config/importance.yaml.
2	Contoh action: “Check on vulnerable family members” (§22)	ACTION REQUIRED/RECOMMENDED wajib sumber resmi, dan advis keselamatan tidak boleh dikarang (Bagian 5.6)	Contoh itu melanggar kontrak addendum. Fixture hanya berisi action yang bersumber resmi (BMKG/BPBD/dst). Tambahkan sebagai kasus uji.
3	Confidence = HIGH/MEDIUM/LOW (§19)	confidence_score numerik + evidence_status + verification_level. Ditambah enum CONFIRMED/SUPPORTED/UNCONFIRMED/CONFLICTING/UNKNOWN	Total ada tiga set enum yang tumpang tindih. ADR-004: confidence_score numerik adalah sumber kebenaran. HIGH/MEDIUM/LOW hanya bucket tampilan dengan ambang di config. Label CONFIRMED…UNKNOWN diturunkan dari evidence_status + verification_level lewat tabel pemetaan.
4	Contoh angka: “26 articles → 143 claims → 4 candidates” (§27, §47)	Semua angka harus berasal dari processing_run_id nyata (Bagian 3)	Angka itu ilustrasi, bukan target. Demo menampilkan angka hasil run fixture apa adanya. Jangan menyetel fixture agar menghasilkan 26/143/4.
5	Layar Overview berisi “World · 8 major developments” dan hierarki World→Asia→Indonesia→Jakarta (§23, §25)	MVP hanya Jakarta/Indonesia, 3 kategori	Model data mendukung semua level. UI hanya menampilkan level yang punya data, dan bagian tanpa data tampil sebagai empty state, bukan angka karangan.
6	“What Changed since I last checked” adalah fitur andalan (§18)	MVP hanya “Changed since the previous update”. Personalisasi butuh last_seen_snapshot_id dan tidak boleh diklaim sebelum ada	Opsional di akhir Stage 06: simpan last_seen_snapshot_id di localStorage (murah, tanpa auth). Setelah ada, boleh diklaim.
7	Layar 3 bernama “AI Reasoning / Transparency”	Namanya Processing & Evidence dan tidak boleh menampilkan chain-of-thought	Pakai nama addendum. Master Spec tidak punya endpoint untuknya (§39 hanya 7 endpoint), jadi tambah GET /events/{id}/processing dan GET /health lewat ADR dan OpenAPI.
8	Entitas DB: EventRelation, ProcessingJob (§38)	Daftar berbeda: ArticleVersion, EventSnapshot, EventChange, EventMembershipAudit, Conflict, ProcessingRun	Ambil gabungan. ProcessingJob (unit kerja antrean) dan ProcessingRun (rekaman provenance) berbeda fungsi, keduanya perlu. EventRelation hanya related_to, itu pun bila ada kebutuhan UI yang terlihat.

Dua penyesuaian saran saya sebelumnya:

Embedding tidak ditunda, tetapi diurutkan. Master Spec (§14, §37) menyebut embedding sebagai bagian strategi hibrida, dan itu juga bahan kuat untuk nilai Technical Merit 40%. Bangun dulu resolver deterministik dan ukur di dev set. Lalu tambah embedding retrieval dan ukur lagi. Terakhir tambah adjudikasi Gemini dan ukur lagi. Hasilnya studi ablasi tiga tingkat di laporan evaluasi, yang membuktikan kontribusi tiap komponen.
Gemma opsional. Master Spec bilang “Gemini/Gemma where appropriate”. Jangan masukkan Gemma sampai ada alasan terukur (misalnya ekstraksi murah). Cukup satu ADR singkat bila memutuskan tidak dipakai.

### DEC-0008: Hasil review silang setelah update ADR 4 6 7
- **Tanggal**: 2026-10-12
- **Status**: Diterima
- **Konteks**: Mengupdate keputusan berdasarkan hasil review silang.
- **Keputusan**: 
  - Model Gemini per jenis panggilan: dari halaman deprecations resmi. Mis. model Flash GA untuk Adjudicate/Synthesize, dan varian Flash-Lite hanya bila hasil dev set mendukung untuk Extract.
  - Embedding: model dan dimensi (1c).
  - Komponen confidence final. Daftar Master §19 berisi enam faktor (kualitas sumber, korobrasi independen, konsistensi klaim, konfirmasi resmi, konsistensi temporal, konsistensi geografis). Config reviewer berisi empat, dengan verbatim_quote_match dan recency_decay yang tidak ada di Master. Usul: pakai enam faktor Master; jadikan kecocokan kutipan sebagai gerbang validasi ekstraksi, bukan komponen berbobot; kesegaran dibahas di urgency, bukan confidence.
  - Urgency: terpisah dari importance (lihat 1d), dan bagaimana ia ikut peringkat “Need to know”.
  - EventRelation: tidak dibuat sekarang.
  - Aturan atribusi Tier-2 (V-2): media mana yang boleh jadi pembawa kutipan sumber resmi, dan bukti apa yang cukup.
  - Struktur narasi: statements dengan evidence_claim_ids (V-4).

---