"use client";

import React from "react";
import {
  AlertTriangle,
  GitCommit,
  History,
  MinusCircle,
  PlusCircle,
  RefreshCw,
} from "lucide-react";
import { ChangeCategory, ChangesResponse, ChangeType } from "@/lib/types";
import { Language } from "@/lib/i18n";

interface ChangesViewProps {
  data: ChangesResponse;
  onSelectClaim: (claimId: string) => void;
  lang?: Language;
}

export function ChangesView({ data, onSelectClaim, lang = "id" }: ChangesViewProps) {
  const changes = data.changes || [];

  if (changes.length === 0) {
    return (
      <div className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-10 text-center text-xs text-[var(--ink2)] space-y-2">
        <History className="h-6 w-6 mx-auto text-[var(--ink2)] opacity-60" />
        <h4 className="font-serif font-semibold text-sm text-[var(--ink)]">
          {lang === "en" ? "No Material Changes Recorded" : "Belum Ada Perubahan Material"}
        </h4>
        <p className="text-xs text-[var(--ink2)] max-w-md mx-auto leading-relaxed">
          {lang === "en"
            ? "No material factual changes recorded across snapshots yet (Addendum §7: Only corroborated factual updates are recorded)."
            : "Belum ada perubahan material yang tercatat antar snapshot (Addendum §7: Hanya perubahan faktual terbukti yang dicatat)."}
        </p>
      </div>
    );
  }

  const getChangeTypeBadge = (type: ChangeType) => {
    switch (type) {
      case "ADDED":
        return {
          label: lang === "en" ? "NEW FACT" : "FAKTA BARU",
          bg: "bg-[var(--tint)]",
          text: "text-[var(--accent)]",
          border: "border-[var(--accent)]",
          icon: PlusCircle,
        };
      case "UPDATED":
        return {
          label: lang === "en" ? "UPDATED" : "DIPERBARUI",
          bg: "bg-[var(--tint)]",
          text: "text-[var(--ink)]",
          border: "border-[var(--line)]",
          icon: RefreshCw,
        };
      case "CORRECTED":
        return {
          label: lang === "en" ? "CORRECTED" : "DIKOREKSI",
          bg: "bg-[var(--warnbg)]",
          text: "text-[var(--warn)]",
          border: "border-[var(--warn)]",
          icon: AlertTriangle,
        };
      case "RETRACTED":
        return {
          label: lang === "en" ? "RETRACTED" : "DICABUT / DIRALAT",
          bg: "bg-[var(--dangerbg)]",
          text: "text-[var(--danger)]",
          border: "border-[var(--danger)]",
          icon: MinusCircle,
        };
    }
  };

  const getCategoryLabel = (cat?: ChangeCategory | null) => {
    switch (cat) {
      case "AREA_CHANGE":
        return lang === "en" ? "Affected Area Change" : "Perubahan Cakupan Wilayah";
      case "ALERT_STATUS":
        return lang === "en" ? "Alert Level Change" : "Perubahan Status Siaga";
      case "ESCALATION":
        return lang === "en" ? "Situation Escalation" : "Eskalasi Situasi";
      case "NUMERICAL":
        return lang === "en" ? "Numerical / Statistics Update" : "Pembaruan Angka / Statistik";
      case "NEWLY_CONFIRMED":
        return lang === "en" ? "Newly Confirmed by Authorities" : "Terkonfirmasi Resmi Baru";
      case "NEWLY_CONFLICTING":
        return lang === "en" ? "New Claim Conflict" : "Konflik Klaim Terdeteksi";
      default:
        return lang === "en" ? "Material Change" : "Perubahan Material";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-6 shadow-xs">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--accent)] mb-1">
            <GitCommit className="h-4 w-4" />
            <span className="font-semibold">MATERIAL DELTA AUDIT</span>
          </div>
          <h3 className="font-serif font-bold text-xl text-[var(--ink)] tracking-tight">
            {lang === "en" ? "Material Changes Log (What Changed)" : "Riwayat Perubahan Material (What Changed)"}
          </h3>
          <p className="text-xs text-[var(--ink2)] mt-1 leading-relaxed max-w-xl">
            {lang === "en"
              ? "Factual delta comparison across snapshots. Semantic changes without corroboration are excluded."
              : "Perbandingan delta antar-snapshot berurutan. Perubahan gaya bahasa tanpa bukti tidak dicatat."}
          </p>
        </div>

        <div className="rounded-xl bg-[var(--tint)] border-[1.5px] border-[var(--line)] px-4 py-2 text-center">
          <div className="font-serif text-2xl font-bold text-[var(--ink)]">
            {data.material_change_count}
          </div>
          <div className="font-sans text-[11px] text-[var(--ink2)] font-medium">
            {lang === "en" ? "Factual Deltas" : "Perubahan Faktual"}
          </div>
        </div>
      </div>

      {/* Changes List */}
      <div className="space-y-4">
        {changes.map((chg) => {
          const badge = getChangeTypeBadge(chg.change_type);
          const Icon = badge.icon;
          return (
            <div
              key={chg.id}
              className="rounded-2xl border-[1.5px] border-[var(--line)] hover:border-[var(--ink)] bg-[var(--surface)] p-6 transition-colors space-y-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] pb-3">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-bold border-[1.5px] ${badge.bg} ${badge.text} ${badge.border}`}
                  >
                    <Icon className="h-3 w-3" />
                    {badge.label}
                  </span>

                  <span className="text-xs font-semibold text-[var(--ink)]">
                    {getCategoryLabel(chg.change_category)}
                  </span>
                </div>

                {chg.field_name && (
                  <span className="font-mono text-[11px] text-[var(--ink2)] bg-[var(--tint)] px-2 py-0.5 rounded border border-[var(--line)]">
                    Field: {chg.field_name}
                  </span>
                )}
              </div>

              {/* Before vs After */}
              {(chg.before_value || chg.after_value) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {chg.before_value && (
                    <div className="rounded-xl border border-[var(--line)] bg-[var(--tint)]/50 p-4 space-y-1">
                      <span className="text-[11px] font-mono text-[var(--ink2)] uppercase tracking-wider block">
                        {lang === "en" ? "Previous State" : "Keadaan Sebelumnya"}
                      </span>
                      <p className="font-serif text-sm text-[var(--ink2)] leading-relaxed">
                        {chg.before_value}
                      </p>
                    </div>
                  )}

                  {chg.after_value && (
                    <div className="rounded-xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-4 space-y-1">
                      <span className="text-[11px] font-mono text-[var(--accent)] uppercase tracking-wider font-semibold block">
                        {lang === "en" ? "Updated State" : "Pembaruan Terkini"}
                      </span>
                      <p className="font-serif text-sm font-medium text-[var(--ink)] leading-relaxed">
                        {chg.after_value}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Grounding Claim Chips */}
              {chg.evidence_claim_ids && chg.evidence_claim_ids.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 border-t border-[var(--line)] pt-3 text-xs">
                  <span className="text-[11px] text-[var(--ink2)] font-sans">
                    {lang === "en" ? "Supporting Citations:" : "Klaim Bukti Pendukung:"}
                  </span>
                  {chg.evidence_claim_ids.map((cid, i) => (
                    <button
                      key={i}
                      onClick={() => onSelectClaim(cid)}
                      className="font-mono text-[12px] font-semibold text-[var(--accent)] hover:text-[var(--ink)] inline-flex items-center px-2 py-0.5 rounded-lg bg-[var(--tint)] border-[1.5px] border-[var(--line)] hover:border-[var(--ink)] transition-colors min-h-[28px]"
                    >
                      [{lang === "en" ? "Evidence" : "Bukti"} #{cid.slice(0, 8)}]
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
