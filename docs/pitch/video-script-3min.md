# 🎬 Naskah Video Pitch 3 Menit: Stay Mad

> **Durasi Total**: Tepat 180 detik (03:00 menit)  
> **Target Audiens**: Dewan Juri Kompetisi AI & Inovasi Teknologi  
> **Format Visual**: Kombinasi Talking Head, Live Demo Screencast, dan Diagram Arsitektur  
> **Prinsip Utama**: Dinamis, meyakinkan, berbasis bukti riil (*No Fake Mocks*).

---

## ⏱️ BABAK 1: Problem Statement (0:00 – 0:45 | 45 Detik)

| Visual / On-Screen | Audio / Naskah Narator | Durasi |
| :--- | :--- | :---: |
| **[0:00 - 0:10]**<br>Montase headline berita krisis di Indonesia: banjir Jakarta, erupsi Merapi, gangguan KRL. Teks berkedip: *"5 Kecamatan? 7 Kecamatan? Status Siaga atau Awas?"* | *"Pernahkah Anda membuka portal berita saat terjadi bencana darurat di kota Anda, lalu mendapati puluhan artikel yang isinya saling bertentangan? Satu media menyebut 5 kecamatan terendam, media lain menyebut 7 kecamatan. Ada media yang salah mengabarkan status Merapi naik ke Awas, lalu meralatnya begitu saja 30 menit kemudian."* | 10s |
| **[0:10 - 0:25]**<br>Infografis bergerak: 1 berita disalin ke 15 portal berita jaringan Transmedia/MNC. Chatbot LLM umum memberikan jawaban tebakan yang salah. | *"Di Indonesia, sindikasi konglomerasi media menciptakan ilusi konsensus palsu. Lebih parah lagi, chatbot AI konvensional sering berhalusinasi—mengarang angka kepastian saat data tidak lengkap, atau bahkan tertipu oleh instruksi palsu di internet."* | 15s |
| **[0:25 - 0:45]**<br>Kamera beralih ke Presenter. Tampil logo **STAY MAD** dengan animasi glowing.<br>*Tagline*: **Stay Mad, Stay Updated. Monitor · Analyze · Do.** | *"Inilah alasan kami membangun STAY MAD: Platform Event Intelligence berbasis Google Gen AI pertama di Indonesia yang merekonstruksi puluhan artikel berita liar menjadi satu kebenaran terverifikasi—tanpa halusinasi, tanpa tebakan palsu, dan setiap klaim terikat langsung pada kalimat asli beritanya."* | 20s |

---

## ⏱️ BABAK 2: Solution & Live Demo Screencast (0:45 – 1:45 | 60 Detik)

| Visual / On-Screen | Audio / Naskah Narator | Durasi |
| :--- | :--- | :---: |
| **[0:45 - 1:00]**<br>Screencast Layar 1 (Overview): Browser membuka `http://localhost:3000`. Klik kartu "Banjir Luapan Ciliwung Jakarta Timur". Tampil badge urgensi & skor kepentingan. | *"Mari kita buktikan pada prototipe nyata Stay Mad. Di dashboard utama, seluruh peristiwa perkotaan telah dikelompokkan secara otomatis dengan tingkat urgensi dan skor kepercayaan berbasis bukti nyata."* | 15s |
| **[1:00 - 1:15]**<br>Screencast Layar 2 (Detail & Conflict Card): Kursor menyorot kotak oranye "Deteksi Perbedaan Informasi (5 vs 7 kecamatan)". | *"Lihat kasus banjir Jakarta Timur ini: Ketika Antara melaporkan 5 kecamatan dan Republika melaporkan 7 kecamatan, Stay Mad tidak menebak angka 6! Sistem secara jujur menandai 'Active Conflict' dan menampilkan kedua versi berdampingan."* | 15s |
| **[1:15 - 1:30]**<br>Kursor mengeklik butir linimasa. Popover **Evidence Chip** terbuka seketika, menyorot naskah kutipan asli (*source span*). | *"Setiap kalimat dan poin linimasa memiliki Evidence Chip. Cukup satu klik, juri dapat melihat kalimat kutipan asli dari naskah berita lengkap dengan media penerbit dan timestamp publikasi berzona waktu WIB."* | 15s |
| **[1:30 - 1:45]**<br>Kursor membuka tab "Pembaruan (What Changed)", lalu beralih ke tab "Processing" memperlihatkan serangan teks jahat `art_demo_07` ditolak. | *"Ketika rilis resmi BPBD masuk, sistem menerbitkan snapshot baru yang menyelesaikan konflik. Dan saat ada artikel berisi instruksi jahat pembajakan sistem, pertahanan anti-prompt-injection kami menolaknya secara mutlak. Nol aksi palsu yang lolos!"* | 15s |

---

## ⏱️ BABAK 3: Technical Merit & Google Gen AI Architecture (1:45 – 2:30 | 45 Detik)

| Visual / On-Screen | Audio / Naskah Narator | Durasi |
| :--- | :--- | :---: |
| **[1:45 - 2:05]**<br>Animasi diagram alir arsitektur Modular Monolith: Ingestion $\to$ Gemini Structured Extraction $\to$ 3-Tier Hybrid Resolver $\to$ pgvector $\to$ Gemini Synthesis. | *"Di balik layar, Stay Mad menggunakan arsitektur Modular Monolith kelas enterprise. Ekstraksi entitas diproses oleh Google Gemini 2.0 Flash dengan skema terstruktur ketat. Untuk resolusi kejadian, kami menciptakan 3-Tier Hybrid Resolver: Tier 1 menyaring batasan waktu dan geografi, Tier 2 menggunakan text-multilingual-embedding-002 dengan pgvector, dan Tier 3 memanggil Gemini untuk mengadili kasus-kasus ambigu."* | 20s |
| **[2:05 - 2:20]**<br>Tabel Metrik Evaluasi Ilmiah & Grafik Studi Ablasi: Pairwise F1 0.7805, B³ F1 0.9099, Grounded Coverage 1.0000, Safety Rate 0.00%. | *"Kami tidak menggunakan data tiruan. Pada pengujian evaluasi buta resmi di eval/reports/, arsitektur hibrida kami mendongkrak Pairwise F1 hingga 155% dibanding pendekatan deterministik, meraih B-cubed F1 0.9099, dan mempertahankan 100% keterikatan bukti naskah asli."* | 15s |
| **[2:20 - 2:30]**<br>Cuplikan terminal deployment: Google Cloud Run Jakarta (asia-southeast1), Cloud SQL, dan Secret Manager. | *"Seluruh sistem terkonfigurasi pada Google Cloud Run region Jakarta, siap melayani publik secara zero-downtime dan autoscaling otomatis."* | 10s |

---

## ⏱️ BABAK 4: Problem Impact & Closing Call to Action (2:30 – 3:00 | 30 Detik)

| Visual / On-Screen | Audio / Naskah Narator | Durasi |
| :--- | :--- | :---: |
| **[2:30 - 2:45]**<br>Montase visual: Warga menggunakan smartphone melihat panduan darurat Stay Mad; petugas tanggap bencana memantau linimasa perubahan. | *"Dalam situasi darurat, kecepatan informasi tanpa kebenaran adalah bahaya, sedangkan kebenaran yang terlambat tidak ada artinya. Stay Mad menghadirkan sintesis informasi yang cepat, akurat, dan dapat dipertanggungjawabkan hingga ke kata terakhir."* | 15s |
| **[2:45 - 3:00]**<br>Layar penutup: URL live demo `http://localhost:3000`, link GitHub, dan logo kompetisi.<br>*Tagline*: **Stay Mad, Stay Updated.** | *"Kunjungi live demo kami dan uji langsung kebenarannya di repo kami. Saya [Nama Presenter] dari Tim Stay Mad. Stay Mad, Stay Updated. Terima kasih!"* | 15s |

---

## 💡 Petunjuk Pengambilan Video bagi Tim (Production Notes)
1. **Perekaman Screencast**: Rekam dalam resolusi 1080p / 60fps dengan rasio layar browser 100% zoom pada tema gelap (*dark mode*).
2. **Kursor Mouse**: Aktifkan highlight kursor lembut saat mengeklik *Evidence Chips* dan tab *What Changed* untuk memandu mata penonton.
3. **Audio**: Gunakan mikrofon kondensor dengan noise suppression bersih dan latar musik ambient teknologi tempo sedang (volume -24dB di bawah vokal).
