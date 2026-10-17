# H. Actionability Algorithm — Stay Mad §53-H

> Aturan source-gating yang ketat. ACTION REQUIRED/RECOMMENDED hanya dari sumber resmi.
> Sistem tidak pernah menginvent saran darurat, medis, hukum, atau keselamatan.

---

## 1. Prinsip

- Actionability mengklasifikasikan apakah pengguna perlu melakukan sesuatu sekarang.
- Level `ACTION REQUIRED` dan `ACTION RECOMMENDED` **hanya** dapat dihasilkan jika ada klaim dari sumber resmi.
- Teks aksi harus grounded pada evidence; tidak dikarang dari konteks umum.
- Contoh "Check on vulnerable family members" (Master Spec §22) **melanggar kontrak addendum** (Addendum §5.6, Conflict Resolution #2). Fixture hanya berisi action yang bersumber resmi.

---

## 2. Level Klasifikasi

| Level | Makna |
|---|---|
| `ACTION_REQUIRED` | Tindakan segera diperlukan; sumber resmi darurat |
| `ACTION_RECOMMENDED` | Tindakan disarankan; sumber resmi |
| `OPTIONAL` | Tindakan bisa dilakukan; bukan darurat |
| `INFORMATIONAL` | Tidak ada aksi spesifik; update situasi saja |
| `NO_IMMEDIATE_ACTION` | Tidak ada aksi yang diperlukan saat ini |

---

## 3. Gating Rules

### Gate 1: Source Authorization

```python
def is_official_emergency_source(claim: Claim) -> bool:
    """Sumber yang boleh mentrigger ACTION REQUIRED / RECOMMENDED."""
    AUTHORIZED_FAMILIES = {
        "GOV_BMKG",    # BMKG (cuaca, gempa)
        "GOV_BPBD_DKI", # BPBD DKI Jakarta
        "GOV_BNPB",    # BNPB Indonesia
        "GOV_SETKAB",  # Sekretariat Kabinet (kebijakan darurat)
        # Tambah via ADR jika ada sumber resmi baru
    }
    return (
        claim.source_family in AUTHORIZED_FAMILIES
        and claim.source_tier == "TIER_1"
    )
```

### Gate 2: Claim Grounding

Teks aksi **wajib** mereferensikan minimal satu `claim_id` yang:
1. Berasal dari sumber yang lulus Gate 1
2. Memiliki `source_span` verbatim yang mengandung instruksi/arahan

### Gate 3: No Inference

Aksi tidak boleh diinferensikan dari konteks umum. Contoh yang **dilarang**:
- ❌ "Pantau keluarga yang rentan" (dikarang, tidak ada perintah resmi)
- ❌ "Jauhi genangan air" (saran umum tanpa rujukan resmi spesifik)

Contoh yang **diizinkan**:
- ✅ "Warga diminta mengungsi dari RW 05 Kelurahan Cipinang Melayu" (klaim BPBD DKI verbatim)
- ✅ "Hindari Jl. Raya Bogor karena jalur terputus" (pernyataan resmi Dishub DKI)

---

## 4. Decision Tree

```
Apakah ada klaim ACTION-relevant dari sumber AUTHORIZED (Gate 1)?
├── TIDAK → level = NO_IMMEDIATE_ACTION atau INFORMATIONAL
└── YA
    ├── Apakah klaim menyebutkan ancaman keselamatan jiwa / evakuasi wajib?
    │   └── YA → level = ACTION_REQUIRED
    ├── Apakah klaim menyebutkan rekomendasi resmi tindakan pencegahan?
    │   └── YA → level = ACTION_RECOMMENDED
    └── Apakah klaim hanya menyebutkan update situasi tanpa arahan?
        └── YA → level = INFORMATIONAL
```

---

## 5. Output dari Gemini Synthesize (Call Type 3)

Gemini menghasilkan `suggested_actions[]` dalam schema yang tervalidasi:

```json
{
  "suggested_actions": [
    {
      "action_level": "ACTION_REQUIRED",
      "action_text": "Warga RW 05 Cipinang Melayu diminta segera mengungsi ke Posko BPBD.",
      "requires_official_source": true,
      "evidence_claim_ids": ["uuid-claim-bpbd-001"]
    }
  ]
}
```

Post-processing validasi (sebelum `Action` record dipersist):

```python
def validate_action(action: dict, claims: Dict[str, Claim]) -> bool:
    if action["action_level"] in ("ACTION_REQUIRED", "ACTION_RECOMMENDED"):
        for claim_id in action["evidence_claim_ids"]:
            claim = claims.get(claim_id)
            if not claim or not is_official_emergency_source(claim):
                # Downgrade ke INFORMATIONAL atau reject
                return False
    return True
```

---

## 6. Fallback Behavior

| Kondisi | Output |
|---|---|
| Tidak ada sumber resmi | `NO_IMMEDIATE_ACTION` — tidak ada teks aksi |
| Sumber resmi ada tapi ambigu | `INFORMATIONAL` dengan teks "Pantau perkembangan resmi di [URL sumber]" |
| Gate validation gagal | `INFORMATIONAL`, bukan downgrade tersembunyi |
| Gemini Synthesize gagal | `NO_IMMEDIATE_ACTION`, tidak ada teks aksi diinvent |

---

## 7. Evaluation Gate

Dari Addendum §8: "The unsupported-action rate must be zero."

- Setiap `Action` record dengan level `ACTION_REQUIRED` atau `ACTION_RECOMMENDED` diaudit oleh evaluator.
- Evaluator memverifikasi bahwa semua `evidence_claim_ids` merujuk ke sumber AUTHORIZED.
- `test_acc_06_prompt_injection_safety` mencakup kasus: artikel berisi instruksi jahat TIDAK menghasilkan `ACTION REQUIRED`.

---

## 8. Konfigurasi (config/actionability.yaml)

```yaml
actionability:
  authorized_source_families:
    - GOV_BMKG
    - GOV_BPBD_DKI
    - GOV_BNPB
    - GOV_SETKAB
  # Tambah via ADR + update sumber di docs/sources.md
  unsupported_action_rate_target: 0.0   # evaluasi requirement
  informational_fallback_text: "Pantau informasi resmi dari sumber terpercaya."
```
