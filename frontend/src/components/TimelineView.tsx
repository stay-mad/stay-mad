"use client";

import React from "react";
import { TimelineEntry } from "@/lib/types";
import { Language } from "@/lib/i18n";

interface TimelineViewProps {
  entries: TimelineEntry[];
  onSelectClaim: (claimId: string) => void;
  lang?: Language;
}

export function TimelineView({ entries, onSelectClaim, lang = "id" }: TimelineViewProps) {
  if (!entries || entries.length === 0) {
    return (
      <div className="rounded-2xl border-[1.5px] border-[var(--line)] bg-[var(--surface)] p-8 text-center text-xs text-[var(--ink2)] font-sans">
        {lang === "en"
          ? "No chronological timeline entries published for this snapshot yet."
          : "Belum ada entri linimasa yang dipublikasi untuk snapshot ini."}
      </div>
    );
  }

  // Sort ascending by order_index
  const sorted = [...entries].sort((a, b) => a.order_index - b.order_index);

  return (
    <div className="relative pl-6 sm:pl-8 before:absolute before:bottom-3 before:left-2 sm:before:left-2.5 before:top-3 before:w-[2px] before:bg-[var(--ink)] space-y-8 py-2">
      {sorted.map((item, idx) => {
        return (
          <div key={item.id || idx} className="relative group">
            {/* Timeline node circle: 3px border per DESIGN.md */}
            <div className="absolute -left-[27px] sm:-left-[31px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full border-[3px] border-[var(--ink)] bg-[var(--bg)] transition-colors group-hover:border-[var(--accent)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
            </div>

            {/* Unboxed Layout (Tanpa kartu berbingkai per item, per DESIGN.md Section 7) */}
            <div className="grid grid-cols-1 sm:grid-cols-[160px_1fr] gap-2 sm:gap-6 items-start pb-6 border-b border-[var(--line)]">
              {/* Kolom Waktu di kiri (mono, qualifier presisi di bawahnya) */}
              <div className="space-y-0.5">
                <div className="font-mono text-xs sm:text-sm font-semibold text-[var(--ink)]">
                  {item.display_time || (lang === "en" ? "Time under confirmation" : "Waktu konfirmasi")}
                </div>
                {item.event_time_qualifier && (
                  <div className="text-[11px] font-mono text-[var(--ink2)] italic">
                    {item.event_time_qualifier}
                  </div>
                )}
                <div className="text-[10px] text-[var(--ink2)] font-mono opacity-60">
                  #{item.order_index + 1}
                </div>
              </div>

              {/* Teks Klaim serif 19px di kanan + Chip bukti di bawahnya */}
              <div className="space-y-2.5">
                <p className="font-serif text-[17px] sm:text-[19px] leading-[1.6] text-[var(--ink)]">
                  {item.description}
                </p>

                {/* Chip bukti: mono 12.5px, accent, tint bg, line border, radius 8px */}
                {item.evidence_claim_ids && item.evidence_claim_ids.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-xs text-[var(--ink2)] font-sans">
                      {lang === "en" ? "Citations:" : "Sitasi Bukti:"}
                    </span>
                    {item.evidence_claim_ids.map((cid, cIdx) => (
                      <button
                        key={cIdx}
                        onClick={() => onSelectClaim(cid)}
                        className="font-mono text-[12.5px] font-medium text-[var(--accent)] bg-[var(--tint)] hover:bg-[var(--hover)] border-[1.5px] border-[var(--line)] px-2.5 py-0.5 rounded-lg min-h-[28px] transition-colors inline-flex items-center gap-1 shadow-2xs"
                        title={lang === "en" ? "View source evidence span" : "Buka kutipan sumber verbatim"}
                      >
                        [{lang === "en" ? "Bukti" : "Bukti"} #{cid.slice(0, 8)}]
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
