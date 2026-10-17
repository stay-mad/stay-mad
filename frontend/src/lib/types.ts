/**
 * Frontend TypeScript types aligned with docs/contracts/openapi.yaml
 * and backend/staymad/api/schemas.py.
 */

export type EventCategory =
  | "disaster_and_weather"
  | "transportation_and_infrastructure"
  | "government_and_public_policy";

export type DataMode = "live" | "demo" | "degraded";

export type GeoLevel = "city" | "province" | "country" | "continent" | "world";

export type EvidenceStatus =
  | "SUPPORTED"
  | "CONFLICTING"
  | "INSUFFICIENT"
  | "RETRACTED";

export type VerificationLevel =
  | "OFFICIAL_PRIMARY"
  | "INDEPENDENTLY_CORROBORATED"
  | "SINGLE_SOURCE";

export type ConfidenceBucket = "HIGH" | "MEDIUM" | "LOW";

export type ActionabilityLevel =
  | "ACTION_REQUIRED"
  | "ACTION_RECOMMENDED"
  | "OPTIONAL"
  | "INFORMATIONAL"
  | "NO_IMMEDIATE_ACTION";

export type TimelinePrecision =
  | "EXACT"
  | "APPROXIMATE"
  | "DAY"
  | "RANGE"
  | "UNKNOWN";

export type TimelineQualifier =
  | "sekitar"
  | "sebelum"
  | "diperkirakan"
  | "dilaporkan_pada"
  | "tepat";

export type ChangeType = "ADDED" | "UPDATED" | "CORRECTED" | "RETRACTED";

export type ChangeCategory =
  | "AREA_CHANGE"
  | "ALERT_STATUS"
  | "ESCALATION"
  | "NUMERICAL"
  | "NEWLY_CONFIRMED"
  | "NEWLY_CONFLICTING";

export type ClaimStatus =
  | "CONFIRMED"
  | "SUPPORTED"
  | "UNCONFIRMED"
  | "CONFLICTING"
  | "UNKNOWN";

export type ResolutionDecision =
  | "SAME_EVENT"
  | "RELATED_EVENT"
  | "SEPARATE_EVENT"
  | "NEEDS_REVIEW";

export type SourceTier = "TIER_1" | "TIER_2";

export interface Location {
  id?: string | null;
  city?: string | null;
  district?: string | null;
  province?: string | null;
  country?: string;
  geo_level: GeoLevel;
  canonical_name: string;
}

export interface ConfidenceComponents {
  source_quality: number;
  corroboration: number;
  claim_consistency: number;
  official_confirmation: number;
  temporal_consistency: number;
}

export interface ConfidenceSignals {
  confidence_score: number;
  confidence_bucket: ConfidenceBucket;
  evidence_status: EvidenceStatus;
  verification_level: VerificationLevel;
  components?: ConfidenceComponents | null;
  signals_text: string[];
}

export interface EventSummary {
  id: string;
  category: EventCategory;
  headline: string;
  primary_location?: Location | null;
  time_window_start?: string | null;
  time_window_end?: string | null;
  confidence_signals: ConfidenceSignals;
  importance_score: number;
  urgency_score: number;
  actionability_level: ActionabilityLevel;
  snapshot_id: string;
  data_mode: DataMode;
  last_processed_at: string;
  processing_run_id: string;
}

export interface EventSummaryStats {
  total: number;
  need_to_know: number;
  official_primary: number;
  conflicts: number;
}

export interface EventListResponse {
  events: EventSummary[];
  total: number;
  limit: number;
  offset: number;
  data_mode: DataMode;
  summary_stats?: EventSummaryStats;
}

export interface EvidenceField {
  text?: string | null;
  evidence_claim_ids: string[];
}

export interface ActionItem {
  action_level: ActionabilityLevel;
  action_text: string;
  evidence_claim_ids: string[];
}

export interface EventDetailResponse {
  id: string;
  snapshot_id: string;
  category: EventCategory;
  headline: string;
  primary_location?: Location | null;
  time_window_start?: string | null;
  what_happened: EvidenceField;
  why_it_matters?: EvidenceField | null;
  who_is_affected?: EvidenceField | null;
  what_is_unknown?: EvidenceField | null;
  conflict_summary?: EvidenceField | null;
  actions: ActionItem[];
  confidence_signals: ConfidenceSignals;
  importance_score: number;
  urgency_score: number;
  actionability_level: ActionabilityLevel;
  data_mode: DataMode;
  last_processed_at: string;
  processing_run_id: string;
}

export interface TimelineEntry {
  id: string;
  event_time?: string | null;
  display_time?: string | null;
  event_time_precision: TimelinePrecision;
  event_time_qualifier?: TimelineQualifier | string | null;
  description: string;
  evidence_claim_ids: string[];
  order_index: number;
}

export interface TimelineResponse {
  event_id: string;
  snapshot_id: string;
  entries: TimelineEntry[];
  processing_run_id: string;
}

export interface SourceItem {
  source_id: string;
  name: string;
  source_tier: SourceTier;
  source_family: string;
  article_url: string;
  published_time?: string | null;
  article_version_id: string;
}

export interface SourcesResponse {
  event_id: string;
  sources: SourceItem[];
  unique_source_families: number;
  processing_run_id: string;
}

export interface ChangeItem {
  id: string;
  change_type: ChangeType;
  change_category?: ChangeCategory | null;
  field_name?: string | null;
  before_value?: string | null;
  after_value?: string | null;
  evidence_claim_ids: string[];
}

export interface ChangesResponse {
  event_id: string;
  from_snapshot_id?: string | null;
  to_snapshot_id: string;
  changes: ChangeItem[];
  material_change_count: number;
}

export interface ConflictItem {
  id: string;
  field_name: string;
  claim_a_id: string;
  claim_b_id: string;
  value_a: string;
  value_b: string;
  context?: string | null;
  resolved: boolean;
}

export interface AnalysisResponse {
  event_id: string;
  snapshot_id: string;
  conflicts: ConflictItem[];
  confidence_signals: ConfidenceSignals;
  claim_count: number;
  conflicting_claim_count: number;
  processing_run_id: string;
}

export interface ProcessingResponse {
  event_id: string;
  snapshot_id: string;
  processing_run_id: string;
  correlation_id?: string | null;
  articles_analyzed: number;
  claims_extracted: number;
  candidate_events_considered: number;
  timeline_entries: number;
  conflicts_detected: number;
  decision_reason_codes: string[];
  resolution_tier_used: string;
  confidence_signals: ConfidenceSignals;
  model_version: string;
  prompt_version: string;
  schema_version: string;
  last_processed_at: string;
  data_mode: DataMode;
}

export interface HealthResponse {
  status: "ok" | "degraded" | "error";
  database: "connected" | "disconnected";
  gemini?: "reachable" | "unreachable" | "not_checked";
  fixture_mode: boolean;
  environment: "production" | "staging" | "development" | "test";
  version: string;
  details?: string | null;
}
