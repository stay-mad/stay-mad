# Stay Mad — Read-Only Documentation Review Report

> Reviewer: Antigravity (read-only, no files modified)
> Date: 2026-10-12
> Corpus: MASTER_SPEC.md · STAY_MAD_MASTER_SPEC_ADDENDUM.md · docs/decisions.md · docs/adr/001–008 · docs/contracts/openapi.yaml · docs/acceptance-matrix.md · config/*.yaml

---

## Category 1 — Contradictions Between ADRs

| # | Conflict | File : Section | Suggested Fix |
|---|---|---|---|
| **C-1** | **Dual ADR-001**: `001-initial-architecture.md` and `001-modular-monolith-architecture.md` share the same ADR number. Older file defines modules `normalize/`, `claims/`, `confidence/`, `actions/`, `events/`. Newer file redefines them as `extraction/`, `intelligence/`, `synthesis/`, etc. Neither is marked superseded. | `docs/adr/001-initial-architecture.md` (entire) vs `docs/adr/001-modular-monolith-architecture.md` (entire) | Add `Status: Superseded by 001-modular-monolith-architecture.md` to the old file. Use only the modular-monolith file as authoritative ADR-001. |
| **C-2** | **ADR-006 user decision adds 3 sources absent from config**: ADR-006 §Opsi A lists `{GOV_BMKG, GOV_BPBD_DKI, GOV_BNPB, GOV_SETKAB}` as authorized families, then the user decision appends tempo.co, kompas.com, and cnbc indonesia. `config/sources.yaml` has none of these three — no `source_family`, no `tier`. Action-gating code would have no entries to match. | `docs/adr/006-actionability-policy.md` L26, L67–L68 vs `config/sources.yaml` (entire) | Add entries for tempo.co, kompas.com, and cnbc indonesia to `config/sources.yaml` with explicit `source_family` and `tier`, or defer to a follow-up ADR referencing the config as the authoritative list. |
| **C-3** | **ADR-007 embeds literal model strings then says use Secret Manager**: The `Konfigurasi` code block shows `GEMINI_MODEL=gemini-2.0-flash` and `EMBEDDING_MODEL=text-multilingual-embedding-002` as inline values while the Consequences section says env vars come from Secret Manager. These are contradictory patterns. | `docs/adr/007-gemini-model-selection.md` L56–L59 | Replace the code block with placeholder text, e.g. `GEMINI_MODEL=<Secret Manager: stay-mad/gemini-model>`. Actual model names should exist only in Secret Manager. |
| **C-4** | **ADR-004/006/007 status says Accepted but headings still say PROPOSED**: Header line says `Status: Accepted` but section headings read `## Keputusan (PROPOSED — butuh persetujuan user)`. User decision blocks confirm approval, but "PROPOSED" was never removed, causing confusion about whether these are finalized. | `docs/adr/004-confidence-schema.md` L4 vs L24; `docs/adr/006-actionability-policy.md` L4 vs L20; `docs/adr/007-gemini-model-selection.md` L4 vs L19 | Remove `(PROPOSED — butuh persetujuan user)` from all three `## Keputusan` headings now that user decisions are recorded. |
| **C-5** | **ADR-007 references `gemini-2.0-pro` as an alternative** — this model identifier may not match any stable Google AI endpoint (the stable names are `gemini-1.5-pro` or `gemini-2.0-pro-exp` in experimental). A stale name copied into startup validation would cause a runtime failure. | `docs/adr/007-gemini-model-selection.md` L27 | Verify against the current [Google AI model catalogue](https://ai.google.dev/models) and update the identifier or annotate it as "to be confirmed at implementation time." |

---

## Category 2 — ADR Decisions That Violate the Addendum or Silently Drop a Master Spec Requirement

| # | Finding | File : Section | Suggested Fix |
|---|---|---|---|
| **V-1** | **ADR-004 silently drops three claim-level enums required by Addendum §5.4**: Decision says claim-level `CONFIRMED/UNCONFIRMED/UNKNOWN` are "tidak digunakan di level event" but Addendum §5.4 requires all five tokens (`CONFIRMED, SUPPORTED, UNCONFIRMED, CONFLICTING, UNKNOWN`) to be "treated as defined enums with documented rules." No `ClaimStatus` enum exists for claim-level use in the OpenAPI spec or ADR. | `docs/adr/004-confidence-schema.md` L36 vs Addendum §5 L64–65 | Define a `ClaimStatus` enum scoped to the Claim entity in both ADR-004 and `openapi.yaml`. Document the mapping: `CONFIRMED` at claim level → `evidence_status=SUPPORTED + verification_level=OFFICIAL_PRIMARY` at event level. |
| **V-2** | **ADR-006 leaves the Tier-2 attribution chain technically undefined**: User answered "ya qualify" for Tier-2 sources quoting official statements, but the ADR provides no mechanism (e.g., `Claim.attributed_speaker_source_family` field) to verify the attribution. Without a technical rule, implementation is ambiguous and the `unsupported_action_rate = 0.00` guarantee is unenforceable. | `docs/adr/006-actionability-policy.md` L56–69 vs Addendum §5.6 | Add a subsection specifying: (a) the attribution chain field, (b) which Tier-2 source families are authorised wire carriers, (c) a negative test case for unverifiable quote attribution. |
| **V-3** | **`config/resolver.yaml` references an OpenAI embedding model**: `entity_resolution.model_name: "text-embedding-3-small"` is an OpenAI model; ADR-007 decided to use `text-multilingual-embedding-002` (Google). `vector_dimension: 1536` is also OpenAI's ada-002 dimension, not the 768 dimensions of the Google model. The config governs runtime behavior per Addendum §6. | `config/resolver.yaml` L6, L5 vs `docs/adr/007-gemini-model-selection.md` L41–43 | Change `model_name` to `text-multilingual-embedding-002` and `vector_dimension` to `768`. This is the most critical runtime error in the corpus. |
| **V-4** | **`synthesis/` module in ADR-001 has no safety contract**: The module is described as "Gemini Synthesize call, narrative generation" but Addendum §5.1 says "Gemini outputs structured JSON … Free-form model text is not a source of truth." Narrative generation implies free-form output; no ADR governs what it can and cannot assert. | `docs/adr/001-modular-monolith-architecture.md` L29 vs Addendum §5.1 | Either fold narrative generation into `intelligence/` under the existing grounding contract, or create ADR-009 specifying what `synthesis/` may produce and mandating `evidence_claim_ids` on every sentence. |
| **V-5** | **ADR-003 defers `EventRelation` without a Stage gate**: Says "tabel ada, tidak digunakan sampai ada kebutuhan UI visible" but no ADR or stage gate defines when this decision will be reviewed. Future agents may implement the table's logic speculatively. | `docs/adr/003-database-schema-strategy.md` L46 vs Addendum §6 L104 | Add: "Stage 06 (Frontend Agent) will confirm whether a `related_to` UI surface exists. If not, the table is dropped in the Stage 06 migration and this ADR is updated." |
| **V-6** | **Importance formula weights exist only in Master Spec §21 as illustrative numbers**: `decisions.md` conflict #1 and ADR-004 resolve that confidence should be excluded from importance, but the updated five-factor formula with its weights is never written into any config file. Addendum §9 requires thresholds to be configuration values. No `config/importance.yaml` exists. | Master Spec §21 L694–701; `decisions.md` L99; `docs/adr/004-confidence-schema.md` L34; `config/` (missing importance.yaml) | Create `config/importance.yaml` with five factors (Impact, Urgency, Proximity, Public Importance, Momentum) and weights summing to 1.0. ADR-004 or a new ADR should reference it as canonical. |
| **V-7** | **`config/confidence.yaml` has 4 weight components; ADR-004 says 5, Master Spec §19 says 6**: The weights (`source_tier 0.35, verbatim_quote_match 0.25, cross_source_consensus 0.25, recency_decay 0.15`) total 1.0 from 4 components. ADR-004 L30 says "5 komponen (lihat §53-F)". Master Spec §19 lists 6 factors. `claim_consistency`, `official_confirmation`, and `temporal_consistency` are absent from the config. | `config/confidence.yaml` L3–7 vs `docs/adr/004-confidence-schema.md` L30 vs Master Spec §19 L641–646 | Reconcile all three into a single authoritative list in `config/confidence.yaml` with weights summing to 1.0. ADR-004 should cite the config as the single source of truth. |

---

## Category 3 — Fields / Enums Referenced but Never Defined

| # | Reference | Where Used | Where It Should Be Defined | Suggested Fix |
|---|---|---|---|---|
| **F-1** | `ClaimStatus` enum (`CONFIRMED`, `SUPPORTED`, `UNCONFIRMED`, `CONFLICTING`, `UNKNOWN`) | Addendum §5.4 L64–65; Master Spec §12 L394–398 | Entirely absent from `openapi.yaml` schemas | Add `ClaimStatus` to `openapi.yaml` components/schemas. Document mapping to event-level `EvidenceStatus`. |
| **F-2** | `ResolutionDecision` enum (`SAME_EVENT`, `RELATED_EVENT`, `SEPARATE_EVENT`, `NEEDS_REVIEW`) | Addendum §6 L96; ADR-005 L35; acceptance-matrix `test_acc_03` | Absent from `openapi.yaml`. `EventMembershipAudit` mentioned but has no schema. | Add `ResolutionDecision` enum to `openapi.yaml`. Annotate `EventMembershipAudit` as internal-only if not exposed via API. |
| **F-3** | `SourceTier` enum (`TIER_1`, `TIER_2`) | `openapi.yaml` `SourceItem.source_tier` L732–733 (inline enum only); `config/sources.yaml` uses integers `tier: 1` / `tier: 2` | Not promoted to a named schema component | Promote to a named `SourceTier` enum in `openapi.yaml` components/schemas. Add comments in `sources.yaml` mapping integers to enum strings. |
| **F-4** | `ChangeCategory` enum (affected-area expansion, alert-status change, escalation, etc.) | Addendum §7 L113–118 defines 5 change types as semantic categories | Absent from `openapi.yaml`. `ChangeType` covers `ADDED/UPDATED/CORRECTED/RETRACTED` (structural) but not semantic categories. | Add an optional `change_category` field to `ChangeItem` with an enum (`AREA_CHANGE`, `ALERT_STATUS`, `ESCALATION`, `NUMERICAL`, `NEWLY_CONFIRMED`, `NEWLY_CONFLICTING`). |
| **F-5** | `correlation_id` for jobs | Addendum §9 L152 requires correlation IDs on job state machines | Not present in `ProcessingResponse` or any response schema | Add `correlation_id: string (nullable)` to `ProcessingResponse` and document the job correlation ID pattern. |
| **F-6** | `data_mode: degraded` | Addendum §5.7–5.8 require a "truthful degraded state" visible in UI. `HealthResponse.status` includes `degraded` but `DataMode` enum only has `live` and `demo`. | `openapi.yaml` `DataMode` L370–373 | Either add `degraded` to `DataMode` so `EventSummary.data_mode` can express it, or add a separate `system_mode` field in list/detail responses and document that `DataMode` is for data provenance only, not system health. |
| **F-7** | `event_time_qualifier` controlled vocabulary | `openapi.yaml` `TimelineEntry.event_time_qualifier` L692–694 (free string) | Addendum §7 L108 and Master Spec §16 require preserving qualifiers like "around", "before", "reported on" consistently | Add a `TimelineQualifier` enum or a code comment listing canonical values (`sekitar`, `sebelum`, `diperkirakan`, `dilaporkan_pada`, `tepat`). Free strings cause rendering inconsistency across languages. |

---

## Category 4 — Acceptance Scenarios With No Mapped Test

| # | Scenario | Source | Gap |
|---|---|---|---|
| **A-1** | "Visit overview, detail, sources, timeline, changes, and transparency views in `demo` and `live`/degraded modes" — Addendum §11 scenario 7 | Addendum §11 L186–187 | Acceptance-matrix row 7 is mapped to "Multi-Event Article & Isolasi Lintas Domain" — a completely different scenario. The UI-mode view scenario has **no test ID at all** in the matrix. **Suggested fix**: Add `test_acc_07b_ui_mode_views` to verify all 6 UI views render correctly in demo, live, and degraded modes with real API data and proper empty/loading/error states. |
| **A-2** | "Run the evaluator and retain the generated report" — Addendum §11 scenario 8 | Addendum §11 L187–188; acceptance-matrix row 8 | `test_acc_08_evaluator_trace_integrity` scope is the entire 23-article corpus but does not assert that `make eval-blind` produces a file in `eval/reports/` with a verifiable `report_id`. ADR-008 §6 distinguishes fixture tests from gold evaluation. **Suggested fix**: Split into (a) `test_acc_08a_report_artifact_produced` asserting report file creation and (b) `test_acc_08b_no_hardcoded_metrics` asserting no README metric exists outside a report. |
| **A-3** | "Malicious instruction embedded in source content must not affect ANY output" — Addendum §11 para 2 | Addendum §11 L189 | `EX-05` and `EX-09` are marked "Planned (overlap test_acc_06)". `test_acc_06` tests both prompt injection AND action gating together. There is **no test that checks the injected instruction does not alter non-action outputs** (headline, timeline text, confidence score). **Suggested fix**: Implement `test_extra_09_instruction_following_guard` as a fully independent test checking all output fields, not just action level. |
| **A-4** | "No change set for a wording-only reprocessing" — Addendum §11 scenario 5 / Addendum §7 L110 | Addendum §11 L184 | `test_acc_05_official_update_changeset` covers only the positive case (a change set IS produced). The **negative case** — reprocess with wording-only edit, assert zero new `EventChange` records — has no test. **Suggested fix**: Add `test_acc_05b_no_changeset_wording_only`. |
| **A-5** | Action-policy violation metric required by Addendum §8 | Addendum §8 L137 | ADR-008 §3 annotation protocol lists 6 label fields (`event_id`, `timeline_order`, `location_canonical`, `has_conflict`, `expected_change`, `action_policy`) but `evaluate.py` metrics list (pairwise B³, timeline F1, location accuracy, attribution, conflict/change P/R) does not explicitly include an **action-policy violation rate**. Without it, the `unsupported_action_rate = 0.00` guarantee can never be verified by the runner. **Suggested fix**: Add `action_policy_violation: bool` to the gold-set annotation schema and `unsupported_action_rate` to the evaluator output. |

---

## Category 5 — Config Values Hard-Coded in ADR Text

| # | Hard-Coded Value | Location | Problem | Suggested Fix |
|---|---|---|---|---|
| **HC-1** | `GEMINI_MODEL=gemini-2.0-flash` | `docs/adr/007-gemini-model-selection.md` L57 | Literal model string in ADR will be copied into `.env`, Dockerfiles, or CI scripts, bypassing Secret Manager. Violates Addendum §9 "never hard-code credentials." | Replace with `GEMINI_MODEL=<Secret Manager key: stay-mad/gemini-model>` and add a startup validator that fails on empty/missing value. |
| **HC-2** | `EMBEDDING_MODEL=text-multilingual-embedding-002` | `docs/adr/007-gemini-model-selection.md` L58 | Same issue as HC-1; also contradicts `config/resolver.yaml` L6 which still has the OpenAI model name. | Remove from ADR code block. Correct `resolver.yaml` (see V-3). |
| **HC-3** | `similarity_threshold: 0.85` and `time_window_hours: 72` | `config/resolver.yaml` L4, L12 | Addendum §6 L88 requires calibration against the labelled evaluation set. ADR-005 L58 says calibration happens before Stage 05. These uncalibrated values will be used by code from Stage 03 onward, potentially biasing the evaluation they are supposed to be calibrated against. | Add comment: `# UNCALIBRATED — update after Stage 04 dev-set evaluation per ADR-005`. Add CI lint rule that fails if `calibrated:` field is missing from resolver thresholds. |
| **HC-4** | `high_confidence: 0.80` and `medium_confidence: 0.50` | `config/confidence.yaml` L10–11 | ADR-004 correctly places thresholds in config, but no evaluation validated these values. A score of 0.79 will be shown as `LOW` with no empirical basis. | Add `# UNCALIBRATED — starting estimate. Update after Stage 04 gold-set evaluation per ADR-004.` |
| **HC-5** | `fuzzy_ratio_min: 80` and `min_co_occurring_claims: 2` | `config/resolver.yaml` L8, L13 | Values set without evaluation evidence. `min_co_occurring_claims: 2` may be too loose or too strict for the expected article volume. | Add calibration note; cross-reference ADR-005 §Ablation Study Design. |
| **HC-6** | `cluster_method: "hierarchical"` | `config/resolver.yaml` L14 | ADR-005 specifies a 3-tier hybrid pipeline, not a single clustering algorithm. This field conflicts with the approved architecture and will mislead implementors. | Replace with a comment: `# 3-tier pipeline per ADR-005; this field unused until Tier 1 grouping method is confirmed.` |

---

## Summary

| Category | Items Found |
|---|---|
| C — ADR Contradictions | 5 |
| V — ADR Violations of Addendum / Silent Spec Drops | 7 |
| F — Undefined Fields / Enums | 7 |
| A — Acceptance Gaps | 5 |
| HC — Hard-Coded Config Values in ADR Text | 6 |
| **Total** | **30** |

### Priority Order for Resolution

| Priority | Item(s) | Reason |
|---|---|---|
| 🔴 Critical | **V-3** | `config/resolver.yaml` has wrong vendor model + wrong vector dimension. Will silently corrupt all Tier-2 embedding resolution from Stage 03 onward. |
| 🔴 Critical | **C-2** | ADR-006 user decision added 3 sources not in `config/sources.yaml`. Action-gating code has no match entries for them. |
| 🟠 High | **V-1 / F-1** | `ClaimStatus` enum required by Addendum §5.4 is entirely absent from OpenAPI spec. |
| 🟠 High | **V-6 / V-7** | `config/importance.yaml` does not exist; `config/confidence.yaml` has fewer components than ADR-004 and Master Spec claim. |
| 🟡 Medium | **C-1** | Two ADR-001 files with conflicting module taxonomies. Superseded file must be marked. |
| 🟡 Medium | **A-1** | Addendum §11 scenario 7 (UI mode views) has no test ID in acceptance-matrix. |
| 🟢 Low | **HC-3–HC-6** | Uncalibrated thresholds in config should be annotated before Stage 03 starts using them. |
