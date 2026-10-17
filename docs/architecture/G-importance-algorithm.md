# G. Importance Algorithm — Stay Mad §53-G

> Importance adalah field TERPISAH dari confidence dan urgency (Addendum §5, decisions.md Conflict #1).
> Event berdampak tinggi tapi tidak pasti **tidak diturunkan diam-diam** peringkatnya.
> Bobot di config/importance.yaml, bukan hard-coded.

---

## 1. Prinsip

- **Importance** mengukur relevansi dan dampak nyata event terhadap pengguna di Jakarta/Indonesia.
- **Importance ≠ Trending**: viral tidak otomatis penting.
- **Importance ≠ Confidence**: event uncertain dengan dampak tinggi tetap penting — ditampilkan dengan label uncertainty, bukan disembunyikan.
- Semua komponen dapat dijelaskan kepada pengguna ("WHY YOU ARE SEEING THIS").

---

## 2. Komponen Importance Score

```
importance_score = w_impact     * impact_score
                 + w_urgency    * urgency_score
                 + w_proximity  * proximity_score
                 + w_public_imp * public_importance_score
                 + w_momentum   * momentum_score
```

**Catatan**: `confidence_score` TIDAK termasuk dalam importance formula (Conflict Resolution #1).

### 2.1 impact_score

Berdasarkan kategori event dan signal klaim:

| Sinyal | Skor |
|---|---|
| Ada korban jiwa / evakuasi massal | 1.0 |
| Infrastruktur kritis terdampak (rel, jalan tol, bandara) | 0.85 |
| Siaga Darurat Bencana (Siaga 1/2 BPBD) | 0.80 |
| Gangguan transportasi signifikan (> 50% kapasitas) | 0.65 |
| Kebijakan publik dengan dampak luas | 0.60 |
| Gangguan layanan publik minor | 0.40 |
| Informatif, dampak tidak langsung | 0.20 |

Mapping ini dikonfigurasi di `config/importance.yaml` bukan di kode.

### 2.2 urgency_score

Terpisah dari confidence; mengukur **seberapa mendesak** event memerlukan perhatian pengguna sekarang:

```python
def urgency_score(event: Event) -> float:
    now = datetime.utcnow()
    hours_since_latest_update = (now - event.updated_at).total_seconds() / 3600

    if event.actionability_level in ("ACTION_REQUIRED", "ACTION_RECOMMENDED"):
        recency_factor = max(0.0, 1.0 - hours_since_latest_update / 24)
        return min(1.0, 0.70 + recency_factor * 0.30)
    elif hours_since_latest_update < 2:
        return 0.60  # event sangat baru
    elif hours_since_latest_update < 8:
        return 0.40
    elif hours_since_latest_update < 24:
        return 0.20
    else:
        return 0.05
```

### 2.3 proximity_score

Relevansi geografis terhadap lokasi default (Jakarta) atau pilihan pengguna:

| Lokasi Event | Skor |
|---|---|
| Kota yang sama (mis. Jakarta) | 1.0 |
| Provinsi yang sama (DKI Jakarta) | 0.75 |
| Indonesia (nasional) | 0.50 |
| Asia Tenggara | 0.25 |
| Internasional | 0.10 |

### 2.4 public_importance_score

Mengukur tingkat kepentingan publik berdasarkan:

```python
def public_importance_score(event: Event, claims: List[Claim]) -> float:
    score = 0.0
    # Sumber resmi pemerintah memberikan bobot tinggi
    if any(c.source_family.startswith("GOV_") for c in claims):
        score += 0.40
    # Jumlah unique source families (corroboration proxy)
    families = len({c.source_family for c in claims})
    score += min(0.40, families * 0.10)
    # Kategori inherent importance
    category_base = {
        "DISASTER_AND_WEATHER": 0.20,
        "TRANSPORTATION_AND_INFRASTRUCTURE": 0.15,
        "GOVERNMENT_AND_PUBLIC_POLICY": 0.15,
    }.get(event.category, 0.10)
    score += category_base
    return min(1.0, score)
```

### 2.5 momentum_score

Mengukur tingkat perkembangan event (developing vs stale):

```python
def momentum_score(event: Event) -> float:
    snapshots_last_6h = count_snapshots(event_id=event.id, since_hours=6)
    new_claims_last_6h = count_new_claims(event_id=event.id, since_hours=6)

    snapshot_signal = min(1.0, snapshots_last_6h / 3)
    claim_signal = min(1.0, new_claims_last_6h / 10)
    return 0.5 * snapshot_signal + 0.5 * claim_signal
```

---

## 3. Bobot Default (config/importance.yaml)

```yaml
importance:
  weights:
    impact: 0.30
    urgency: 0.20
    proximity: 0.15
    public_importance: 0.15
    momentum: 0.20
  # Catatan: tidak ada komponen confidence — terpisah per Addendum §5
  labels:
    high: 0.70     # importance_score >= 0.70
    medium: 0.40   # 0.40 <= score < 0.70
    low: 0.0       # score < 0.40
```

---

## 4. Labels Tampilan

Berdasarkan kombinasi importance + urgency + actionability:

| Kondisi | Label UI |
|---|---|
| `importance >= 0.70` AND `urgency >= 0.60` | 🔴 NEED TO KNOW |
| `importance >= 0.70` AND `urgency < 0.60` | 📌 HIGH IMPACT |
| `actionability = ACTION_REQUIRED` | ⚠ ACTION REQUIRED |
| `momentum >= 0.60` | 📈 DEVELOPING |
| `importance < 0.40` AND `momentum < 0.30` | ℹ INFORMATIONAL |

---

## 5. Explainability (WHY YOU ARE SEEING THIS)

Untuk setiap event, komponen skor disimpan di snapshot dan ditampilkan di UI:

```json
{
  "importance_score": 0.78,
  "urgency_score": 0.65,
  "importance_components": {
    "impact": 0.85,
    "urgency": 0.65,
    "proximity": 1.0,
    "public_importance": 0.70,
    "momentum": 0.50
  },
  "importance_signals": [
    "⚠ Siaga darurat bencana aktif",
    "📍 Relevan untuk Jakarta",
    "⏱ Berkembang dalam 2 jam terakhir",
    "✓ Dikonfirmasi sumber resmi BPBD"
  ]
}
```

---

## 6. Aturan Penting

- Importance score dihitung deterministik dari komponen di atas; Gemini **tidak terlibat** dalam importance calculation.
- Perubahan bobot harus dikalibrasi terhadap labeled evaluation set dan dicatat dalam ADR.
- Confidence LOW **tidak** menyebabkan importance diturunkan — confidence ditampilkan terpisah sebagai label uncertainty.
