"use client";

import React from "react";
import { ExternalLink } from "lucide-react";
import { SourceItem, SourcesResponse } from "@/lib/types";
import { formatWibDateTime } from "@/lib/utils";
import { Language } from "@/lib/i18n";

interface SourcesViewProps {
  data: SourcesResponse;
  lang?: Language;
}

export function SourcesView({ data, lang = "id" }: SourcesViewProps) {
  const sources = data.sources || [];

  // Group sources by source_family
  const familyMap: Record<string, SourceItem[]> = {};
  sources.forEach((s) => {
    const fam = s.source_family || (lang === "en" ? "OTHER" : "LAINNYA");
    if (!familyMap[fam]) familyMap[fam] = [];
    familyMap[fam].push(s);
  });

  const families = Object.keys(familyMap);

  return (
    <div className="space-y-6 text-xs font-sans">
      {/* Header explanation on source family & anti-inflation */}
      <div className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-5 sm:p-6 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="font-sans text-[11px] font-semibold text-[var(--ink2)] uppercase tracking-wider block">
              {lang === "en" ? "Lineage & Provenance" : "Provenans & Lineage Berita"}
            </span>
            <h4 className="font-serif font-bold text-lg text-[var(--ink)] mt-0.5">
              {lang === "en"
                ? "Media Family Grouping (Anti-Inflation Sourcing)"
                : "Pengelompokan Keluarga Media (Anti-Inflation Sourcing)"}
            </h4>
            <p className="text-xs text-[var(--ink2)] mt-1 max-w-xl leading-relaxed">
              {lang === "en"
                ? "Articles from the same publishing conglomerate are strictly clustered to avoid double-counting consensus."
                : "Artikel dari konglomerasi media yang sama dikelompokkan agar tidak dihitung sebagai suara konsensus independen ganda."}
              <span
                className="ml-1.5 cursor-help font-mono text-[10px] border-b border-dotted border-[var(--line)]"
                title="Kepatuhan Kebijakan DEC-0003"
              >
                DEC-0003
              </span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-[var(--tint)] border border-[var(--line)] px-3 py-1.5 font-mono text-xs font-semibold text-[var(--ink)]">
              {data.unique_source_families} {lang === "en" ? "Families" : "Grup Media"}
            </div>
            <div className="rounded-lg bg-[var(--tint)] border border-[var(--line)] px-3 py-1.5 font-mono text-xs font-medium text-[var(--ink2)]">
              {sources.length} {lang === "en" ? "Articles" : "Artikel"}
            </div>
          </div>
        </div>
      </div>

      {/* Grouped by Source Family (Daftar bergaris per DESIGN.md Section 7) */}
      <div className="space-y-5">
        {families.map((fam) => {
          const items = familyMap[fam];
          const isGov = fam.startsWith("GOV_");
          return (
            <div
              key={fam}
              className="rounded-2xl border-[1.5px] border-[var(--line)] bg-[var(--surface)] p-5 sm:p-6 space-y-4"
            >
              {/* Family Header */}
              <div className="flex items-center justify-between border-b-[1.5px] border-[var(--ink)] pb-3">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`rounded-md px-2 py-0.5 text-[10px] font-mono font-bold border ${
                      isGov
                        ? "bg-[var(--tint)] text-[var(--accent)] border-[var(--accent)]/50"
                        : "bg-[var(--tint)] text-[var(--ink)] border-[var(--line)]"
                    }`}
                  >
                    {isGov ? "GOV" : "MEDIA"}
                  </span>
                  <h5 className="font-serif font-bold text-lg text-[var(--ink)]">
                    {fam}
                  </h5>
                  <span className="text-xs text-[var(--ink2)] font-mono">
                    · {items.length} {lang === "en" ? "articles" : "artikel"}
                  </span>
                </div>

                <span className="text-[11px] font-mono text-[var(--ink2)]">
                  {isGov
                    ? (lang === "en" ? "Official Government Authority" : "Institusi Pemerintah Resmi")
                    : (lang === "en" ? "Media Conglomerate" : "Konglomerasi Media")}
                </span>
              </div>

              {/* Articles under this family */}
              <div className="divide-y divide-[var(--line)]">
                {items.map((art, aIdx) => (
                  <div
                    key={aIdx}
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 py-3.5 first:pt-1 last:pb-0"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-serif font-bold text-base text-[var(--ink)]">
                          {art.name}
                        </span>
                        <span
                          className={`rounded-md px-2 py-0.5 text-[10px] font-mono font-semibold border ${
                            art.source_tier === "TIER_1"
                              ? "bg-[var(--tint)] text-[var(--accent)] border-[var(--accent)]/40"
                              : "bg-[var(--tint)] text-[var(--ink2)] border-[var(--line)]"
                          }`}
                        >
                          {art.source_tier}
                        </span>
                      </div>
                      <p className="text-xs text-[var(--ink2)] font-mono mt-1">
                        {lang === "en" ? "Published" : "Dipublikasikan"}: {formatWibDateTime(art.published_time, lang)}
                      </p>
                    </div>

                    <a
                      href={art.article_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 rounded-lg border-[1.5px] border-[var(--ink)] bg-[var(--surface)] hover:bg-[var(--tint)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] transition-colors shadow-2xs self-start sm:self-auto"
                    >
                      <span>{lang === "en" ? "Read Original" : "Buka Berita Asli"}</span>
                      <ExternalLink className="h-3.5 w-3.5 text-[var(--ink2)]" />
                    </a>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
