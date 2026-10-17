"use client";

import React from "react";
import { ExternalLink, X } from "lucide-react";
import { SourceItem } from "@/lib/types";
import { Language, getTranslation } from "@/lib/i18n";

interface EvidencePopoverProps {
  claimId: string;
  source?: SourceItem;
  quoteSpan?: string;
  onClose: () => void;
  lang?: Language;
}

export function EvidencePopover({
  claimId,
  source,
  quoteSpan,
  onClose,
  lang = "id",
}: EvidencePopoverProps) {
  const t = getTranslation(lang);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 backdrop-blur-[2px] p-4 transition-all"
      onClick={onClose}
    >
      {/* Editor Note Modal per DESIGN.md Section 7: latar surface, border 1.5px ink, radius 12px */}
      <div
        className="relative w-full max-w-lg rounded-xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-6 shadow-md"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b-[1.5px] border-[var(--line)] pb-3">
          <div>
            <span className="font-sans text-[11px] font-semibold text-[var(--ink2)] uppercase tracking-wider block">
              {lang === "en" ? "Editor's Note · Grounded Citation" : "Catatan Editor · Sitasi Verbatim"}
            </span>
            <h3 className="font-serif font-bold text-lg text-[var(--ink)] mt-0.5">
              {t.evidenceTitle}
            </h3>
            <p className="text-[11px] font-mono text-[var(--ink2)] mt-0.5">
              Claim ID: #{claimId.slice(0, 8)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[var(--ink2)] hover:bg-[var(--tint)] hover:text-[var(--ink)] transition-colors border border-[var(--line)]"
            title={lang === "en" ? "Close" : "Tutup"}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="mt-4 space-y-4 text-xs font-sans">
          {/* Kutipan sumber dalam serif per DESIGN.md */}
          <div className="space-y-1">
            <span className="text-[10px] font-mono text-[var(--ink2)] uppercase tracking-wider">
              {t.evidenceOriginalQuote}
            </span>
            <div className="rounded-lg border-[1.5px] border-[var(--line)] bg-[var(--tint)]/50 p-4 border-l-4 border-l-[var(--accent)]">
              <p className="font-serif text-[16px] sm:text-[17px] leading-[1.6] text-[var(--ink)] italic">
                &ldquo;{quoteSpan || (lang === "en" ? "Verbatim evidence span verified directly from indexed source article." : "Kutipan klaim diverifikasi langsung dari laporan resmi/artikel terindeks.")}&rdquo;
              </p>
            </div>
          </div>

          {/* Source Attribution details */}
          <div className="rounded-lg border border-[var(--line)] bg-[var(--bg)] p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-[var(--ink2)]">{t.evidencePublisher}:</span>
              <span className="text-xs font-serif font-bold text-[var(--ink)]">
                {source?.name || (lang === "en" ? "Official Accredited Media" : "Sumber Berita Terakreditasi")}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[11px] text-[var(--ink2)]">
                {lang === "en" ? "Credibility Tier" : "Klasifikasi Kredibilitas"}:
              </span>
              <span className="font-mono text-[11px] font-medium text-[var(--accent)]">
                {source?.source_tier === "TIER_1"
                  ? (lang === "en" ? "Tier 1: Primary Government Authority" : "Tier 1: Otoritas Resmi Pemerintah")
                  : (lang === "en" ? "Tier 2: Verified National Press" : "Tier 2: Media Pers Nasional Terdaftar")}
              </span>
            </div>

            {source?.source_family && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-[var(--ink2)]">
                  {lang === "en" ? "Media Conglomerate Family" : "Keluarga Sindikasi (Group)"}:
                </span>
                <span className="font-mono text-[11px] text-[var(--ink)]">
                  {source.source_family}
                </span>
              </div>
            )}
          </div>

          {/* Action to original URL */}
          <div className="pt-2">
            <a
              href={source?.article_url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--ink)] text-[var(--bg)] py-2.5 text-xs font-semibold hover:bg-[var(--accent)] transition-colors shadow-2xs"
            >
              <span>{t.evidenceOpenOriginal}</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
            <p className="mt-2 text-center text-[10px] text-[var(--ink2)]">
              {lang === "en"
                ? "Full article copyright resides with publisher (DEC-0003: Strict Sourcing & Minimization)."
                : "Stay Mad tidak menyimpan salinan artikel utuh (DEC-0003: Strict Sourcing & Minimization)."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
