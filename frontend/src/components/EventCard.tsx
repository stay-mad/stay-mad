"use client";

import React from "react";
import {
  AlertCircle,
  Calendar,
  ChevronRight,
  MapPin,
  ShieldAlert,
} from "lucide-react";
import { EventSummary } from "@/lib/types";
import {
  formatWibDateTime,
  getCategoryLabel,
  getCategoryStyle,
  getConfidenceBadge,
  getUrgencyBadge,
  getVerificationBadge,
} from "@/lib/utils";
import { Language } from "@/lib/i18n";

interface EventCardProps {
  event: EventSummary;
  isLead?: boolean;
  lang?: Language;
}

export function EventCard({ event, isLead = false, lang = "id" }: EventCardProps) {
  const catStyle = getCategoryStyle(event.category);
  const urgency = getUrgencyBadge(event.urgency_score, event.importance_score, lang);
  const verification = getVerificationBadge(
    event.confidence_signals.verification_level,
    lang
  );
  const confidence = getConfidenceBadge(
    event.confidence_signals.confidence_bucket,
    event.confidence_signals.confidence_score,
    lang
  );
  const isConflicting =
    event.confidence_signals.evidence_status === "CONFLICTING";
  const isUrgentAction =
    event.actionability_level === "ACTION_REQUIRED" ||
    event.actionability_level === "ACTION_RECOMMENDED";

  // Refined left accent bar for high-priority stories
  const leftBorderColor =
    event.urgency_score >= 0.8
      ? "border-l-4 border-l-red-600 dark:border-l-red-500"
      : event.urgency_score >= 0.6
      ? "border-l-4 border-l-amber-600 dark:border-l-amber-500"
      : "border-l-[1.5px]";

  return (
    <a
      href={`/events/${event.id}`}
      className={`group relative flex flex-col justify-between rounded-xl sm:rounded-2xl border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 sm:p-6 transition-all duration-200 hover:border-[var(--border-strong)] hover:shadow-md ${leftBorderColor} ${
        isLead ? "bg-gradient-to-br from-[var(--bg-surface)] to-[var(--bg-subtle)]/30" : ""
      }`}
    >
      <div>
        {/* Top Eyebrow Meta: Category Pill + Location + Verification Tier */}
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 text-xs border-b border-[var(--border-subtle)]/50">
          <div className="flex flex-wrap items-center gap-2">
            {/* Category tag */}
            <span
              className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-0.5 text-[11px] font-semibold border ${catStyle.bg} ${catStyle.text} ${catStyle.border}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${catStyle.dot}`} />
              {getCategoryLabel(event.category, lang)}
            </span>

            {/* Urgency indicator */}
            <span className={`text-[11px] font-bold tracking-wide ${urgency.text}`}>
              {urgency.label}
            </span>
          </div>

          {/* Verification Badge */}
          <span
            className="text-[11px] text-[var(--text-muted)] font-medium bg-[var(--bg-subtle)] px-2 py-0.5 rounded border border-[var(--border-subtle)]"
            title={verification.label}
          >
            {verification.label}
          </span>
        </div>

        {/* Serif Headline (NYT Editorial Style) */}
        <h3
          className={`font-serif font-black text-[var(--text-primary)] group-hover:text-[var(--accent-primary)] transition-colors tracking-tight ${
            isLead
              ? "text-2xl sm:text-3xl leading-[1.2] mt-3.5 mb-2.5"
              : "text-lg sm:text-[21px] leading-[1.25] mt-3 mb-2"
          }`}
        >
          {event.headline}
        </h3>

        {/* Quiet Conflict or Emergency Alerts */}
        {(isConflicting || isUrgentAction) && (
          <div className="mt-2.5 mb-2 flex flex-wrap gap-2 text-xs">
            {isConflicting && (
              <span className="inline-flex items-center gap-1.5 rounded-md bg-amber-50 dark:bg-amber-950/40 px-2.5 py-1 text-[11px] font-semibold text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-800">
                <AlertCircle className="h-3.5 w-3.5 text-amber-700 dark:text-amber-400" />
                {lang === "en" ? "Divergent Claims Reported" : "Ada Perbedaan Klaim Antar-Berita"}
              </span>
            )}
            {isUrgentAction && (
              <span className="inline-flex items-center gap-1.5 rounded-md bg-red-50 dark:bg-red-950/40 px-2.5 py-1 text-[11px] font-semibold text-red-900 dark:text-red-200 border border-red-300 dark:border-red-800">
                <ShieldAlert className="h-3.5 w-3.5 text-red-700 dark:text-red-400" />
                {lang === "en" ? "Official Safety Protocol" : "Instruksi Keselamatan Otoritas"}
              </span>
            )}
          </div>
        )}

        {/* Verbatim Grounded Quote / Lead Excerpt */}
        {event.confidence_signals.signals_text?.length > 0 && (
          <p
            className={`mt-2.5 text-xs text-[var(--text-secondary)] line-clamp-2 border-l-2 border-[var(--border-strong)]/60 pl-3 italic font-serif leading-relaxed ${
              isLead ? "text-sm text-[var(--text-secondary)] line-clamp-3" : ""
            }`}
          >
            &ldquo;{event.confidence_signals.signals_text[0]}&rdquo;
          </p>
        )}
      </div>

      {/* Footer Lineage: Location · Confidence · WIB Time · Read Link */}
      <div className="mt-4 border-t border-[var(--border-subtle)]/80 pt-3 text-xs text-[var(--text-muted)]">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {/* Metadata String */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 font-semibold text-[var(--text-primary)]">
              <MapPin className="h-3.5 w-3.5 text-[var(--text-muted)]" />
              {event.primary_location?.canonical_name || (lang === "en" ? "National" : "Nasional")}
            </span>
            <span className="text-[var(--border-strong)]">·</span>
            <span className="font-mono text-[11px] text-[var(--text-secondary)] font-medium">
              {confidence.label}
            </span>
            <span className="text-[var(--border-strong)]">·</span>
            <span className="flex items-center gap-1 text-[11px] font-mono">
              <Calendar className="h-3 w-3" />
              {formatWibDateTime(event.last_processed_at, lang)}
            </span>
          </div>

          {/* Read CTA */}
          <div className="inline-flex items-center gap-1 text-xs font-bold text-[var(--accent-primary)] group-hover:translate-x-0.5 transition-transform">
            <span>{lang === "en" ? "Report" : "Laporan"}</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </div>
    </a>
  );
}
