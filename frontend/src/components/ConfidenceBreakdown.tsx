"use client";

import React from "react";
import { CheckCircle2, ShieldCheck } from "lucide-react";
import { ConfidenceSignals } from "@/lib/types";
import { getConfidenceBadge, getVerificationBadge } from "@/lib/utils";
import { Language } from "@/lib/i18n";

interface ConfidenceBreakdownProps {
  signals: ConfidenceSignals;
  lang?: Language;
}

export function ConfidenceBreakdown({ signals, lang = "id" }: ConfidenceBreakdownProps) {
  const badge = getConfidenceBadge(signals.confidence_bucket, signals.confidence_score, lang);
  const verBadge = getVerificationBadge(signals.verification_level, lang);

  // Overall Confidence Score (0..100)
  const overallPct = Math.round(signals.confidence_score * 100);

  // 5 Components (DEC-0008, Addendum §5, Master Spec §19)
  const componentsList = [
    {
      name: lang === "en" ? "Source Quality" : "Kualitas Sumber",
      weight: 30,
      score: signals.components?.source_quality ?? 0,
      description:
        lang === "en"
          ? "Reputation of publishing authorities (Tier 1 vs Tier 2)"
          : "Reputasi kredibilitas penerbit (Tier 1 vs Tier 2)",
    },
    {
      name: lang === "en" ? "Independent Corroboration" : "Koroborasi Independen",
      weight: 25,
      score: signals.components?.corroboration ?? 0,
      description:
        lang === "en"
          ? "Cross-conglomerate confirmation from distinct media families"
          : "Dukungan lintas keluarga konglomerasi media berbeda",
    },
    {
      name: lang === "en" ? "Claim Consistency" : "Konsistensi Klaim",
      weight: 20,
      score: signals.components?.claim_consistency ?? 0,
      description:
        lang === "en"
          ? "Absence of unresolved factual claim divergences"
          : "Ketiadaan pertentangan klaim/angka yang tak terselesaikan",
    },
    {
      name: lang === "en" ? "Official Confirmation" : "Konfirmasi Resmi",
      weight: 15,
      score: signals.components?.official_confirmation ?? 0,
      description:
        lang === "en"
          ? "Formal validation by government authorities (BPBD/BMKG/etc.)"
          : "Konfirmasi otoritas institusi berwenang (BPBD/BMKG/dll)",
    },
    {
      name: lang === "en" ? "Temporal Consistency" : "Konsistensi Temporal",
      weight: 10,
      score: signals.components?.temporal_consistency ?? 0,
      description:
        lang === "en"
          ? "Chronological coherence of timeline entries and reporting order"
          : "Kesesuaian urutan kronologis linimasa dan waktu lapor",
    },
  ];

  return (
    <div className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-6 shadow-xs space-y-6">
      {/* Title & Large Serif Score (DESIGN.md Section 7) */}
      <div className="border-b-[1.5px] border-[var(--line)] pb-5">
        <div className="flex items-center justify-between gap-2">
          <span className="font-sans text-xs font-semibold text-[var(--ink2)] tracking-wide">
            {lang === "en" ? "Model Keyakinan Fakta" : "Model Keyakinan Fakta"}
          </span>
          <span
            className="cursor-help text-[10px] font-mono text-[var(--ink2)] border-b border-dotted border-[var(--line)]"
            title="Kepatuhan Standar: DEC-0006, DEC-0008, & Master Spec §19"
          >
            §19
          </span>
        </div>

        {/* Big Serif Score + Badge */}
        <div className="flex items-baseline gap-3 mt-2">
          <span className="font-serif text-5xl font-semibold tracking-tight text-[var(--ink)]">
            {overallPct}%
          </span>
          <div>
            <span
              className={`inline-block text-xs font-bold uppercase tracking-wider ${
                signals.confidence_bucket === "HIGH"
                  ? "text-[var(--accent)]"
                  : signals.confidence_bucket === "MEDIUM"
                  ? "text-[var(--warn)]"
                  : "text-[var(--ink2)]"
              }`}
            >
              {badge.label}
            </span>
            <div className="text-[11px] text-[var(--ink2)] font-sans">
              {verBadge.label}
            </div>
          </div>
        </div>

        <p className="text-xs text-[var(--ink2)] mt-2 leading-relaxed">
          {lang === "en"
            ? "Deterministic 5-component weighted formula without black-box scoring."
            : "Formula deterministik 5 komponen pembobotan terbuka tanpa estimasi semu."}
        </p>
      </div>

      {/* 5 Components (Bars 8-10px rounded, no text collision) */}
      <div className="space-y-4">
        {componentsList.map((comp, idx) => {
          const pct = Math.round(comp.score * 100);
          const points = (comp.score * (comp.weight / 100) * 100).toFixed(1);
          return (
            <div key={idx} className="space-y-1.5">
              {/* Row 1: Component Name & Mono Value */}
              <div className="flex items-baseline justify-between gap-2 text-xs">
                <span className="font-sans font-semibold text-[var(--ink)]">
                  {comp.name}
                </span>
                <span className="font-mono text-xs text-[var(--ink)] whitespace-nowrap font-medium">
                  {pct}% · {points} {lang === "en" ? "pts" : "poin"}
                </span>
              </div>

              {/* Row 2: Weight subtext */}
              <div className="text-[10px] text-[var(--ink2)] font-sans">
                {lang === "en" ? "Bobot" : "Bobot"} {comp.weight}%
              </div>

              {/* 8-10px Rounded Bar per DESIGN.md */}
              <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--tint)]">
                <div
                  className="h-full rounded-full bg-[var(--accent)] transition-all duration-300"
                  style={{ width: `${Math.max(pct, 2)}%` }}
                />
              </div>

              {/* Row 3: Description */}
              <p className="text-[11px] text-[var(--ink2)] leading-relaxed">
                {comp.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Grounded Evidence Signals */}
      {signals.signals_text && signals.signals_text.length > 0 && (
        <div className="rounded-xl border-[1.5px] border-[var(--line)] bg-[var(--tint)]/50 p-4 space-y-2">
          <div className="text-[11px] font-sans font-semibold text-[var(--ink2)] uppercase tracking-wider">
            {lang === "en" ? "Sinyal Bukti Terverifikasi" : "Sinyal Bukti Terverifikasi"}
          </div>
          <ul className="space-y-2 text-xs text-[var(--ink)]">
            {signals.signals_text.map((sig, i) => (
              <li key={i} className="flex items-start gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[var(--accent)] mt-0.5" />
                <span className="leading-relaxed font-sans">{sig}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
