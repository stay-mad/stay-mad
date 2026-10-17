"use client";

import React from "react";
import { AlertCircle } from "lucide-react";
import { ConflictItem } from "@/lib/types";
import { Language } from "@/lib/i18n";

interface ConflictsViewProps {
  conflicts: ConflictItem[];
  onSelectClaim: (claimId: string) => void;
  lang?: Language;
}

export function ConflictsView({ conflicts, onSelectClaim, lang = "id" }: ConflictsViewProps) {
  if (!conflicts || conflicts.length === 0) return null;

  return (
    <div className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-6 space-y-5">
      {/* Editorial Header (DESIGN.md: judul tegas, tanpa warna alarm, warn sebagai penanda saja) */}
      <div className="border-b-[1.5px] border-[var(--line)] pb-4">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[var(--warn)] shrink-0" />
          <h4 className="font-serif text-lg font-bold text-[var(--ink)]">
            {lang === "en" ? "Transparansi Perbedaan Klaim Antar-Berita" : "Transparansi Perbedaan Klaim Antar-Berita"}
          </h4>
          <span
            className="cursor-help text-[10px] font-mono text-[var(--ink2)] border-b border-dotted border-[var(--line)] ml-auto"
            title="Kepatuhan Addendum §5.8 (Objective Conflict Tracking)"
          >
            §5.8
          </span>
        </div>
        <p className="text-xs text-[var(--ink2)] mt-1 font-sans leading-relaxed">
          {lang === "en"
            ? "Contrasting data points reported across media outlets presented transparently without premature reconciliation."
            : "Sistem mendeteksi pertentangan angka dan data antar-media tanpa menutup-nutupi ketidakpastian fakta."}
        </p>
      </div>

      {/* Dueling Values List */}
      <div className="space-y-4">
        {conflicts.map((cf) => (
          <div
            key={cf.id}
            className="rounded-xl border border-[var(--line)] bg-[var(--bg)] p-4 space-y-3"
          >
            <div className="flex items-center justify-between pb-2 border-b border-[var(--line)] text-xs">
              <span className="font-sans font-semibold text-[var(--ink)]">
                {lang === "en" ? "Field" : "Bidang"}: <span className="font-mono text-[11px] text-[var(--ink2)]">{cf.field_name}</span>
              </span>
              <span
                className={`rounded-md px-2 py-0.5 text-[10px] font-mono font-medium border ${
                  cf.resolved
                    ? "bg-[var(--tint)] text-[var(--accent)] border-[var(--accent)]/40"
                    : "bg-[var(--warnbg)] text-[var(--warn)] border-[var(--warn)]/40"
                }`}
              >
                {cf.resolved
                  ? (lang === "en" ? "✓ Resolved by Official Update" : "✓ Terselesaikan Update Resmi")
                  : (lang === "en" ? "⚠️ Active Divergence" : "⚠️ Perbedaan Aktif")}
              </span>
            </div>

            {cf.context && (
              <p className="text-xs text-[var(--ink2)] italic font-serif leading-relaxed">
                &ldquo;{cf.context}&rdquo;
              </p>
            )}

            {/* Dua kolom bergaris versi A vs B berdampingan (seperti koreksi redaksi koran) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-[var(--line)] border border-[var(--line)] rounded-lg bg-[var(--surface)]">
              <div className="p-3.5 space-y-1.5">
                <span className="text-[10px] font-mono text-[var(--ink2)] uppercase tracking-wider block">
                  {lang === "en" ? "Report Version A" : "Laporan Versi A"}:
                </span>
                <p className="font-serif font-bold text-base text-[var(--ink)]">{cf.value_a}</p>
                <button
                  onClick={() => onSelectClaim(cf.claim_a_id)}
                  className="font-mono text-[11px] font-medium text-[var(--accent)] hover:underline inline-flex items-center gap-1 pt-1"
                >
                  [{lang === "en" ? "Bukti" : "Bukti"} #{cf.claim_a_id.slice(0, 8)}]
                </button>
              </div>

              <div className="p-3.5 space-y-1.5">
                <span className="text-[10px] font-mono text-[var(--ink2)] uppercase tracking-wider block">
                  {lang === "en" ? "Report Version B" : "Laporan Versi B"}:
                </span>
                <p className="font-serif font-bold text-base text-[var(--ink)]">{cf.value_b}</p>
                <button
                  onClick={() => onSelectClaim(cf.claim_b_id)}
                  className="font-mono text-[11px] font-medium text-[var(--accent)] hover:underline inline-flex items-center gap-1 pt-1"
                >
                  [{lang === "en" ? "Bukti" : "Bukti"} #{cf.claim_b_id.slice(0, 8)}]
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
