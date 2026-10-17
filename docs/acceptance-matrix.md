# Acceptance Matrix — Skenario 1-8 + Extra Fixture Cases

Matriks pemetaan **8 skenario penerimaan wajib** (*Acceptance Scenarios* sesuai Addendum §11)
dan **extra fixture cases** (Addendum §11 paragraf 2) terhadap ID pengujian dan artikel fixture
pada `eval/fixtures/seed_demo_23.json`.

> **Authority**: Matriks ini adalah kontrak antar agent. Perubahan test ID atau pemetaan
> memerlukan ADR atau persetujuan eksplisit.

---

## 1. Skenario Wajib (Addendum §11 — 8 Acceptance Scenarios)

| No | Skenario Addendum §11 | Deskripsi & Bukti Ekspektasi | Artikel Uji Terkait | Test ID Implementasi | ADR Ref | Status |
|---|---|---|---|---|---|---|
| **1** | **Deduplikasi & Source Family Grouping** | Mendeteksi artikel duplikat/sindikasi dan mengelompokkan `source_family: TRANSMEDIA` sehingga tidak melipatgandakan skor konsensus independen. | `art_demo_03`, `art_demo_04`, `art_demo_13`, `art_demo_16`, `art_demo_21`, `art_demo_22` | `test_acc_01_syndicated_duplicate` | DEC-0003, ADR-005 | Passing (Verified) |
| **2** | **Rekonstruksi Event Kanonikal & Timeline** | Memproses laporan independen multi-sumber, menghasilkan 1 canonical event dengan klaim bertaut sumber, kualifikasi waktu relatif dipertahankan, dan timeline terurut kronologis. | `art_demo_01`, `art_demo_08`, `art_demo_09`, `art_demo_10`, `art_demo_14`, `art_demo_15`, `art_demo_19`, `art_demo_20`, `art_demo_23` | `test_acc_02_canonical_resolution_timeline` | ADR-005, §53-E | Passing (Verified) |
| **3** | **Pemisahan Hard Constraints (Waktu / Lokasi)** | Mencegah *false merge* pada laporan serupa di hari atau lokasi berbeda (> 72 jam, Jakarta Barat vs Jakarta Timur). Menghasilkan `SEPARATE_EVENT`. | `art_demo_06` (Banjir rob Jakbar 7 Okt vs Banjir luapan Ciliwung Jaktim 10 Okt) | `test_acc_03_same_day_location_isolation` | ADR-005, §53-D §2.1 | Passing (Verified) |
| **4** | **Deteksi Konflik Angka Faktual** | Mendeteksi pertentangan jumlah kecamatan (5 vs 7 kecamatan) tanpa memilih angka secara sepihak. Menandai `evidence_status = CONFLICTING`. | `art_demo_01` (5 kec) vs `art_demo_02` (7 kec) | `test_acc_04_number_conflict_detection` | ADR-004, §53-F | Passing (Verified) |
| **5a** | **Pembaruan Resmi & Change Set Snapshot** | Pembaruan resmi memicu `EventSnapshot v2` dan `EventChange` terstruktur (*What Changed*), menyelesaikan konflik sebelumnya, dan mengoreksi data (termasuk penanganan retraksi). | `art_demo_05` (BPBD DKI 6 kec/Siaga 2), `art_demo_11` (Retraksi Detikcom Merapi), `art_demo_12` (BNPB Merapi), `art_demo_17` (KAI normalisasi sinyal), `art_demo_18` (Setkab Perpres) | `test_acc_05_official_update_changeset` | ADR-003, §53-E §6 | Passing (Verified) |
| **5b** | **Negative Case: Wording-Only Reprocessing** (A-4) | Pemrosesan ulang artikel dengan variasi kalimat semata tanpa perubahan faktual menghasilkan ZERO `EventChange` baru (*no-change specificity = 1.00*). | Sub-fixture wording-only pada Klaster A | `test_acc_05b_no_changeset_wording_only` | Addendum §7 L110, §11 (5) | Passing (Verified) |
| **6** | **Penolakan Injeksi Jahat & Aksi Non-Resmi** | Memperlakukan teks artikel sebagai *untrusted input*. Menolak instruksi jahat (*prompt injection*) dan menolak pembuatan `ACTION REQUIRED` tanpa rujukan resmi otoritas kebencanaan. | `art_demo_07` (Teks injeksi `[SYSTEM INSTRUCTION OVERRIDE]`) | `test_acc_06_malicious_instruction_isolation` | ADR-006, §53-H, DEC-0004 | Passing (Verified) |
| **7a** | **Multi-Event Article & Isolasi Lintas Domain** | Memisahkan dan mengatribusikan klaim yang membahas dua agenda/isu berbeda dalam satu artikel ke event yang sesuai tanpa campur aduk. | `art_demo_23` (Sidang kabinet: subsidi transportasi vs mitigasi bencana) | `test_acc_07_multi_event_article_split` | ADR-005, §53-D §4.2 | Passing (Verified) |
| **7b** | **UI Views in Live, Demo, & Degraded Modes** (A-1) | Kunjungan pada Overview, Detail, Sources, Timeline, Changes, dan Transparency views berfungsi konsisten pada mode demo, live, dan degraded dengan rendering error/empty state yang jujur. | Seluruh data snapshot event & fixture UI | `test_acc_07b_ui_mode_views` | Addendum §11 (7), §5.7–5.8 | Passing (Verified) |
| **8a** | **Evaluator Report Artifact Produced** (A-2) | Menjalankan evaluator (`make eval-blind` / `make eval-baseline`) menghasilkan artifact laporan di `eval/reports/` dengan `report_id` dan trace lengkap yang dapat diverifikasi. | Fixtures & dev/test gold sets | `test_acc_08a_report_artifact_produced` | ADR-008, §53-I | Passing (Verified) |
| **8b** | **Zero Hardcoded Metrics Contract** (A-2) | Tidak ada angka metrik atau UI trace palsu yang ditampilkan di README atau UI tanpa rujukan langsung ke file artifact laporan resmi. | Repository & UI audit | `test_acc_08b_no_hardcoded_metrics` | ADR-008 §6, AGENTS.md | Passing (Verified) |

---

## 2. Extra Fixture Cases (Addendum §11 — Paragraf 2)

Kasus tambahan yang **wajib ada di fixture** dan dicakup oleh test suite:

| Extra Case | Deskripsi | Artikel Fixture | Test ID | ADR Ref | Status |
|---|---|---|---|---|---|
| **EX-01** | **Multi-event article** — Satu artikel membahas dua event berbeda | `art_demo_23` (Sidang kabinet: dua agenda berbeda) | `test_extra_01_multi_event_article` | ADR-005 §4.2 | Passing (Verified) |
| **EX-02** | **Dua event serupa di hari berbeda** — Sama wording, tanggal berbeda; harus SEPARATE_EVENT | `art_demo_06` vs artikel Klaster A hari berbeda | `test_extra_02_similar_events_different_days` | ADR-005 §2.1 | Passing (Verified) |
| **EX-03** | **Retraksi** — Artikel mencabut klaim sebelumnya; `EventChange.type = RETRACTED` | `art_demo_11` (Retraksi Detikcom: aktivitas Merapi) | `test_extra_03_retraction_handling` | ADR-003, §53-D §4.2 | Passing (Verified) |
| **EX-04** | **Timestamp parsial / relatif** — "Kemarin pagi", "sekitar pukul 8" → precision APPROXIMATE/DAY | Artikel dengan `event_time_qualifier` ambigu di Klaster A | `test_extra_04_partial_relative_timestamps` | §53-E §2.1 | Passing (Verified) |
| **EX-05** | **Instruksi jahat dalam teks sumber** — `[SYSTEM INSTRUCTION OVERRIDE: ...]` tidak dieksekusi | `art_demo_07` | `test_extra_05_malicious_content_passthrough` | DEC-0004, ADR-006 | Passing (Verified) |
| **EX-06** | **False merge prevention (transitive)** — A≈B, B≈C tidak cukup untuk merge A+C | Dua sub-fixture dengan chain similarity | `test_extra_06_transitive_cluster_guard` | ADR-005 §4.1 | Passing (Verified) |
| **EX-07** | **False causal claim prevention** — Urutan kronologis tidak otomatis = sebab-akibat | Timeline entry tidak mengklaim kausalitas tanpa bukti | `test_extra_07_no_false_causal_claim` | §53-C Call Type 3 | Passing (Verified) |
| **EX-08** | **Unsupported action prevention** — Sumber non-resmi tidak menghasilkan ACTION REQUIRED | `art_demo_07`, `art_demo_13`, `art_demo_16` | `test_extra_08_unsupported_action_prevention` | ADR-006, §53-H §7 | Passing (Verified) |
| **EX-09** | **Full Pipeline Instruction-Following Guard** (A-3) | Teks jahat yang disisipkan tidak mengubah field output non-aksi mana pun (headline, timeline text, skor kepercayaan, nama lokasi) | `art_demo_07` (semua field output) | `test_extra_09_instruction_following_guard` | DEC-0004, Addendum §11 | Passing (Verified) |
| **EX-10** | **Action Policy Violation & Unsupported Rate** (A-5) | Anotasi `action_policy_violation: bool` pada gold set diverifikasi dan menjamin metrik `unsupported_action_rate = 0.00` | Dataset gold `eval/gold/` | `test_extra_10_action_policy_violation_gold` | ADR-008, Addendum §8 | Passing (Verified) |

---

## 3. Pemetaan Klaster Terhadap 3 Kategori Bounded MVP

| Klaster | Topik | Jumlah Artikel | Kategori Terpilih | Catatan Otoritas |
|---|---|---|---|---|
| **Klaster A** | Banjir Luapan Ciliwung Jakarta Timur | 8 artikel | `disaster_and_weather` | Sesuai Master Spec §30 & Addendum |
| **Klaster B** | Peningkatan Aktivitas Gunung Merapi | 5 artikel | `disaster_and_weather` | Sesuai Master Spec §30 & Addendum |
| **Klaster C** | Gangguan Persinyalan KRL Lintas Manggarai | 4 artikel | `transportation_and_infrastructure` | Sesuai Master Spec §30 & Addendum |
| **Klaster D** | Perpres Baru Subsidi Transportasi Massal | 6 artikel | `government_and_public_policy` | **DEC-0007**: Resolusi konflik Master Spec vs Addendum |
| **TOTAL** | 4 Klaster Terintegrasi | **23 artikel** | 3 Kategori MVP | 100% Tercakup |

---

## 4. Test Execution Order (Recommended)

```bash
# Stage 02: Setelah fixtures dibuat
pytest tests/acceptance/ -k "test_acc_01 or test_acc_04 or test_extra_05"

# Stage 03: Setelah Gemini Extract tersedia
pytest tests/acceptance/ -k "test_acc_02 or test_acc_06 or test_extra_04"

# Stage 04: Setelah resolver Tier 2 tersedia
pytest tests/acceptance/ -k "test_acc_03 or test_acc_07 or test_extra_02 or test_extra_06"

# Stage 05: Full acceptance suite
pytest tests/acceptance/ --tb=short

# Stage 07: Smoke test terhadap deployed URL
bash deploy/smoke_test.sh $DEPLOYED_URL
```

---

## 5. Definition of "Verified Baseline" vs "Planned"

| Status | Makna |
|---|---|
| `Verified Baseline` | Pemetaan artikel-ke-test sudah dikonfirmasi; test infrastructure siap |
| `Planned` | Test ID sudah ditetapkan; fixture case sudah diidentifikasi; implementasi di Stage 02-05 |
| `Implemented` | Kode test ada dan passing |
| `Passing` | Lulus di CI dengan processing_run_id valid |
