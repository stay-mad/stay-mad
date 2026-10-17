# F. Confidence Algorithm — Stay Mad §53-F

> Confidence adalah field TERPISAH dari importance dan urgency (Addendum §5, Conflict #1, #3).
> `confidence_score` numerik adalah sumber kebenaran; bucket HIGH/MEDIUM/LOW hanya untuk tampilan.

---

## 1. Prinsip

- **Confidence** mengukur seberapa yakin sistem bahwa **klaim-klaim yang mendukung event ini akurat dan konsisten**.
- Confidence **tidak mempengaruhi** visibility event. Event dengan confidence rendah tetap ditampilkan dengan label "uncertain" (tidak di-downrank secara diam-diam).
- Confidence ≠ Importance. Event berdampak tinggi tapi belum terverifikasi harus tetap terlihat jelas.

---

## 2. Komponen Confidence Score

```
confidence_score = w_source_quality   * source_quality_score
                 + w_corroboration    * corroboration_score
                 + w_claim_consistency * claim_consistency_score
                 + w_official_confirm * official_confirmation_score
                 + w_temporal_consist * temporal_consistency_score
```

### 2.1 source_quality_score

Berdasarkan tier sumber terkuat yang memberikan klaim utama:

| Sumber | Skor |
|---|---|
| `TIER_1` resmi pemerintah (BMKG, BPBD, BNPB, Setkab) | 1.0 |
| `TIER_1` kantor berita nasional (ANTARA) | 0.85 |
| `TIER_2` media kredibel | 0.65 |
| Single source, tier tidak diketahui | 0.40 |

### 2.2 corroboration_score

```python
# Hitung jumlah source_family UNIK yang memberikan klaim utama
unique_families = len({c.source_family for c in primary_claims
                       if c.source_family not in {"UNKNOWN"}})

corroboration_score = min(1.0, unique_families / corroboration_max_families)
# corroboration_max_families = 4 (konfigurasi: config/confidence.yaml)
```

**Anti-inflation**: artikel dari source_family yang sama dihitung sebagai satu keluarga.

### 2.3 claim_consistency_score

```python
total_primary_claims = len(primary_claims)
conflicting_claims = len([c for c in primary_claims if c.role == "CONFLICTING"])

if total_primary_claims == 0:
    claim_consistency_score = 0.0
else:
    conflict_ratio = conflicting_claims / total_primary_claims
    claim_consistency_score = max(0.0, 1.0 - (conflict_ratio * 2))
    # Konflik < 10%: skor penuh; > 50%: skor nol
```

### 2.4 official_confirmation_score

```python
has_official = any(
    c.source_family.startswith("GOV_") and c.source_tier == "TIER_1"
    for c in claims
)
official_confirmation_score = 1.0 if has_official else 0.0
```

### 2.5 temporal_consistency_score

```python
# Persentase klaim temporal yang berhasil dinormalisasi (event_time tidak null)
total_temporal = len([c for c in claims if c.event_time_raw])
resolved = len([c for c in claims if c.event_time is not None])

if total_temporal == 0:
    temporal_consistency_score = 0.5  # tidak ada klaim temporal → netral
else:
    temporal_consistency_score = resolved / total_temporal
```

---

## 3. Bobot Default (config/confidence.yaml)

```yaml
confidence:
  weights:
    source_quality: 0.30
    corroboration: 0.25
    claim_consistency: 0.20
    official_confirmation: 0.15
    temporal_consistency: 0.10
  thresholds:
    high: 0.70   # confidence_score >= 0.70 → bucket HIGH
    medium: 0.45  # 0.45 <= score < 0.70 → MEDIUM
                  # score < 0.45 → LOW
  corroboration_max_families: 4
```

---

## 4. evidence_status dan verification_level

Diturunkan dari komponen confidence menggunakan tabel pemetaan (bukan dari confidence_score secara langsung):

| Kondisi | evidence_status | verification_level |
|---|---|---|
| Ada sumber resmi GOV_* Tier 1 | `SUPPORTED` | `OFFICIAL_PRIMARY` |
| ≥ 2 source_family unik, tidak ada resmi | `SUPPORTED` | `INDEPENDENTLY_CORROBORATED` |
| 1 source_family, tidak ada konflik | `SUPPORTED` | `SINGLE_SOURCE` |
| Ada `Conflict` record belum resolved | `CONFLICTING` | (tergantung sumber konflik) |
| Artikel diretraksi / klaim ditarik | `RETRACTED` | — |
| Klaim terlalu sedikit untuk sintesis | `INSUFFICIENT` | `SINGLE_SOURCE` |

---

## 5. Bucket HIGH/MEDIUM/LOW (Display Only)

```python
def confidence_bucket(score: float) -> str:
    if score >= config.thresholds.high:
        return "HIGH"
    elif score >= config.thresholds.medium:
        return "MEDIUM"
    else:
        return "LOW"
```

Bucket ini **hanya** digunakan untuk tampilan UI. Logic internal selalu menggunakan `confidence_score` numerik.

---

## 6. Explainability

Setiap `EventSnapshot` menyimpan komponen skor untuk explainability:

```json
{
  "confidence_score": 0.74,
  "confidence_bucket": "HIGH",
  "confidence_components": {
    "source_quality": 0.85,
    "corroboration": 0.75,
    "claim_consistency": 0.80,
    "official_confirmation": 1.0,
    "temporal_consistency": 0.67
  },
  "evidence_status": "SUPPORTED",
  "verification_level": "OFFICIAL_PRIMARY"
}
```

UI Processing & Evidence screen menampilkan sinyal confidence ini (tanpa chain-of-thought Gemini).

---

## 7. Aturan Penting

- Event dengan `confidence_score < 0.45` (LOW): ditampilkan dengan label "⚠ Belum terverifikasi"
- Event dengan `evidence_status = CONFLICTING`: ditampilkan dengan konflik eksplisit
- Event dengan `evidence_status = RETRACTED`: ditandai "DICABUT" dan tidak tampil di overview utama
- **Confidence tidak pernah menyebabkan event hilang dari list** — hanya mengubah label visual
