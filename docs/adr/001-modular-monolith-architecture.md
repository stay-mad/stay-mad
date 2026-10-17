# ADR-001: Arsitektur Pipeline Modular Monolith

**Tanggal**: 2026-10-11
**Status**: Accepted
**Penulis**: Architecture Agent

---

## Konteks

Sistem Stay Mad membutuhkan pipeline dari ingest → extraction → resolution → intelligence → API → frontend. Ada trade-off antara simplisitas (single service) dan separation of concerns (microservices).

Addendum §9 menyatakan: "asynchronous processing for ingestion and AI work" dan Addendum §1 menuntut modul yang dapat diuji secara independen. Master Spec §35 eksplisit merekomendasikan Modular Monolith.

## Keputusan

Bangun backend sebagai **Modular Monolith** dengan modul-modul yang terisolasi logikanya:

```
backend/
  ingest/        # source adapters, normalization, dedup
  extraction/    # Gemini Extract call, claim atomization
  resolver/      # Tier 1-3 resolution pipeline
  timeline/      # temporal normalization, ordering
  intelligence/  # confidence, importance, actionability, conflict
  synthesis/     # Gemini Synthesize call, narrative generation
  jobs/          # async job state machine, idempotency, retry
  api/           # FastAPI routes, OpenAPI, middleware
  llm/           # Gemini client abstraction, prompt versioning, cache
  db/            # SQLAlchemy models, Alembic migrations, pgvector
  eval/          # evaluation runner (blind; isolated from gold/)
```

Setiap modul memiliki interface yang terdefinisi jelas dan dapat diuji secara independen.

## Konsekuensi

**Positif**:
- Masing-masing modul dapat dikembangkan dan diuji oleh agent berbeda.
- Path migrasi ke microservices tersedia tanpa schema rewrite.
- Observability mudah: satu deployment, satu log stream.

**Negatif**:
- Scaling granular (mis. scale extraction saja) tidak bisa tanpa refactor ke services.
- Single point of deployment risk mitigated oleh health check dan staged rollout.

**Catatan**: ADR-001 lama (arsitektur direktori) tetap berlaku; dokumen ini memperluas dengan kontrak modul yang lebih detail.
