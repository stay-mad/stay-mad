"use client";

import React from "react";
import { Flame } from "lucide-react";
import { Language } from "@/lib/i18n";

interface ImportanceBreakdownProps {
  importanceScore: number;
  urgencyScore: number;
  lang?: Language;
}

export function ImportanceBreakdown({
  importanceScore,
  urgencyScore,
  lang = "id",
}: ImportanceBreakdownProps) {
  const overallPct = Math.round(importanceScore * 100);
  const urgencyPct = Math.round(urgencyScore * 100);

  return (
    <div className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-6 shadow-xs space-y-5">
      <div className="border-b-[1.5px] border-[var(--line)] pb-4">
        <div className="flex items-center justify-between gap-2">
          <span className="font-sans text-xs font-semibold text-[var(--ink2)] tracking-wide">
            {lang === "en" ? "Prioritization Scoring" : "Model Prioritas Terbitan"}
          </span>
          <span
            className="cursor-help text-[10px] font-mono text-[var(--ink2)] border-b border-dotted border-[var(--line)]"
            title="Kepatuhan Standar: DEC-0008 & Master Spec §21"
          >
            §21
          </span>
        </div>

        <div className="flex items-baseline gap-3 mt-2">
          <span className="font-serif text-4xl font-semibold tracking-tight text-[var(--ink)]">
            {overallPct}%
          </span>
          <span className="text-xs font-mono text-[var(--ink2)]">
            ({importanceScore.toFixed(2)} / 1.00)
          </span>
        </div>

        <p className="text-xs text-[var(--ink2)] mt-1.5 leading-relaxed font-sans">
          {lang === "en"
            ? "Deterministic editorial ranking based on public impact and time urgency."
            : "Penentuan peringkat prioritas redaksi berdasarkan skala dampak dan desakan waktu."}
        </p>
      </div>

      <div className="space-y-4">
        {/* Metric 1: Importance */}
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between text-xs">
            <span className="font-sans font-semibold text-[var(--ink)]">
              {lang === "en" ? "Public Importance Score" : "Tingkat Kepentingan Publik"}
            </span>
            <span className="font-mono text-xs text-[var(--ink)] font-medium">
              {overallPct}% · {importanceScore.toFixed(2)}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--tint)]">
            <div
              className="h-full rounded-full bg-[var(--ink)] transition-all duration-300"
              style={{ width: `${Math.max(overallPct, 2)}%` }}
            />
          </div>
          <p className="text-[11px] text-[var(--ink2)] leading-relaxed">
            {lang === "en"
              ? "Assesses systemic severity, geographical relevance, and population disruption."
              : "Menilai tingkat keparahan sistemik, cakupan wilayah, dan gangguan warga."}
          </p>
        </div>

        {/* Metric 2: Urgency */}
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between text-xs">
            <span className="font-sans font-semibold text-[var(--ink)]">
              {lang === "en" ? "Time Urgency Score" : "Tingkat Urgensi Waktu"}
            </span>
            <span className="font-mono text-xs text-[var(--ink)] font-medium">
              {urgencyPct}% · {urgencyScore.toFixed(2)}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--tint)]">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                urgencyScore >= 0.75
                  ? "bg-[var(--warn)]"
                  : "bg-[var(--accent)]"
              }`}
              style={{ width: `${Math.max(urgencyPct, 2)}%` }}
            />
          </div>
          <p className="text-[11px] text-[var(--ink2)] leading-relaxed">
            {lang === "en"
              ? "Measures need for immediate protective action or emergency mitigation."
              : "Kebutuhan tindakan pelindungan atau mitigasi darurat segera."}
          </p>
        </div>
      </div>
    </div>
  );
}
