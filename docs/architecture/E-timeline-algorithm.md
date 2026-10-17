# E. Timeline Algorithm — Stay Mad §53-E

> Algoritma rekonstruksi timeline kronologis dari klaim temporal.
> Semua presisi dan qualifier dipertahankan; tidak ada presisi yang diinvent.

---

## 1. Input

Timeline dibangun dari kumpulan `Claim` yang telah diasosiasikan dengan sebuah `Event` (hasil Event Resolution). Setiap klaim memiliki:

- `event_time_raw`: teks waktu asli dari sumber
- `event_time`: hasil normalisasi (nullable timestamptz)
- `event_time_precision`: `EXACT | APPROXIMATE | DAY | RANGE | UNKNOWN`
- `event_time_qualifier`: "sekitar", "diperkirakan", "sebelum", dll.
- `source_timezone`: timezone sumber (default `Asia/Jakarta` jika tidak ada)
- `published_time`: waktu publikasi artikel (fallback ordering)
- `evidence_claim_ids`: referensi bukti

---

## 2. Langkah-Langkah

### Step 1: Temporal Extraction (dilakukan di Gemini Call Type 1: Extract)

Gemini mengidentifikasi waktu dalam teks dengan aturan:
- **Waktu eksplisit** (jam:menit): `event_time_precision = EXACT` atau `APPROXIMATE`
- **Waktu relatif** ("dua jam setelah kejadian"): resolve terhadap `published_time` anchor, precision `APPROXIMATE`
- **Tanggal saja**: `event_time_precision = DAY`
- **Range** ("antara pukul 08:00-10:00"): `event_time_precision = RANGE`; simpan start/end
- **Tidak jelas** ("belum lama ini"): `event_time_precision = UNKNOWN`

Qualifier seperti "sekitar", "diperkirakan", "dilaporkan pada" **wajib dipertahankan** di `event_time_qualifier`. Jangan menginvent presisi.

### Step 2: Timezone Normalization

```python
def normalize_to_utc(raw_time, qualifier, source_timezone):
    tz = source_timezone or "Asia/Jakarta"
    if raw_time is None:
        return None, "UNKNOWN"
    utc_time = convert_to_utc(raw_time, tz)
    return utc_time, qualifier
```

Internal storage: UTC. UI display: `Asia/Jakarta` (WIB) sesuai DEC-0001.

### Step 3: Deduplication of Temporal Claims

Sebelum membuat TimelineEntry, deduplikasi klaim waktu:
- Klaim dari source_family yang sama untuk event_time yang sama → satu TimelineEntry (corroboration, bukan duplikat)
- Klaim yang mendeskripsikan **state yang sama** dengan presisi berbeda → pilih yang paling presisi dari sumber paling tinggi tier-nya

### Step 4: Conflict Normalization

Sebelum menandai dua klaim sebagai konflik:
1. Normalisasi nilai + satuan (mis. "5 kecamatan" vs "5 districts" → sama)
2. Normalisasi scope lokasi (mis. "Jakarta Timur" vs "Cipinang" dapat kompatibel)
3. Normalisasi event_time scope (klaim A = kondisi pukul 08:00, klaim B = kondisi pukul 14:00 → bukan konflik, tapi update)
4. Hanya jika tetap tidak rekonsiliasi → `Conflict` record dibuat

### Step 5: Timeline Assembly

```python
def build_timeline(claims: List[Claim]) -> List[TimelineEntry]:
    # Pisahkan: klaim dengan event_time vs tanpa
    known_time = [c for c in claims if c.event_time is not None]
    unknown_time = [c for c in claims if c.event_time is None]

    # Urutkan known_time secara kronologis (event_time ASC)
    known_time.sort(key=lambda c: c.event_time)

    # Untuk unknown_time: gunakan published_time sebagai proxy ordering
    unknown_time.sort(key=lambda c: c.published_time)

    # Gabungkan: known_time dahulu, lalu unknown_time di akhir
    ordered = known_time + unknown_time

    return [
        TimelineEntry(
            event_time=c.event_time,
            event_time_precision=c.event_time_precision,
            event_time_qualifier=c.event_time_qualifier,
            description=c.claim_text,   # Bahasa Indonesia (dari Synthesize)
            evidence_claim_ids=[c.id],
            order_index=i
        )
        for i, c in enumerate(ordered)
    ]
```

### Step 6: Material Change Detection

Sebelum membuat `EventSnapshot` baru, bandingkan timeline baru vs sebelumnya:
- **Material change**: entri baru, perubahan angka penting, eskalasi status resmi, resolusi konflik
- **Non-material**: perubahan wording saja, rephrasing oleh model (versi prompt baru)

Hanya material change yang memicu `EventSnapshot` baru + `EventChange` record.

---

## 3. Output: TimelineEntry

Setiap entri timeline yang disimpan:

```yaml
event_time: "2026-10-10T01:10:00Z"       # UTC; null jika UNKNOWN
event_time_precision: "APPROXIMATE"
event_time_qualifier: "sekitar"
display_time: "08:10 WIB"                 # UI display (Asia/Jakarta)
description: "Banjir pertama dilaporkan warga" # Bahasa Indonesia
evidence_claim_ids: ["uuid-claim-001"]
order_index: 2
```

---

## 4. Display Rules (untuk UI)

| Precision | Tampilan UI |
|---|---|
| `EXACT` | "08:10 WIB" |
| `APPROXIMATE` | "Sekitar 08:10 WIB" |
| `DAY` | "10 Oktober 2026" |
| `RANGE` | "08:00–10:00 WIB" |
| `UNKNOWN` | "Waktu tidak diketahui (dilaporkan ~14:00 WIB)" |

Qualifier **tidak pernah** dihilangkan dari tampilan UI.

---

## 5. Keterbatasan & Risiko

| Risiko | Mitigasi |
|---|---|
| Artikel tanpa timestamp eksplisit | Gunakan `published_time` sebagai proxy; tandai `precision = UNKNOWN` |
| Timezone ambigu dari sumber internasional | Default `Asia/Jakarta`; catat asumsi di `source_timezone` field |
| "Waktu kejadian" vs "waktu dilaporkan" tertukar | Gemini prompt menekankan perbedaan `event_time` vs `reported_time`; validasi spot-check di evaluasi |
| Klaim temporal dari sindikasi berulang | Source family grouping sebelum assembly |
