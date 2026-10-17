# ADR 001: Arsitektur Pipeline Modular Stay Mad

## Status
Accepted

## Konteks
Sistem membutuhkan alur pemrosesan dari penyerapan data (ingest), normalisasi, ekstraksi klaim, resolusi entitas/event, penghitungan skor kepercayaan, hingga penyajian timeline dan aksi.

## Keputusan
Membangun struktur direktori backend yang modular dan terisolasi:
- `ingest`: Penyerapan data dari feed/crawler.
- `normalize`: Pembersihan data dan standarisasi format.
- `claims`: Ekstraksi dan atomisasi klaim.
- `resolver`: Resolusi entitas dan peristiwa.
- `events`: Model agregasi event.
- `timeline`: Kronologi dan hubungan kausal.
- `confidence`: Algoritma penilaian kepercayaan.
- `actions`: Trigger/webhook dan integrasi tindakan.
- `jobs`: Background jobs & batch evaluation.
- `api`: Endpoint REST/GraphQL.
- `llm`: Abstraksi model inferensi dan prompt.
- `db`: Model ORM dan koneksi basis data.

## Konsekuensi
Setiap modul memiliki batasan tanggung jawab yang jelas dan dapat diuji secara independen melalui unit test.
