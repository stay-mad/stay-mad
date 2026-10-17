"use client";

import React from "react";
import { ProcessingResponse } from "@/lib/types";
import { Language } from "@/lib/i18n";

interface PipelineFunnelProps {
  data: ProcessingResponse;
  lang?: Language;
}

export function PipelineFunnel({ data, lang = "id" }: PipelineFunnelProps) {
  const steps = [
    {
      title: lang === "en" ? "Articles Ingested & Analyzed" : "Artikel Berita Dianalisis",
      count: data.articles_analyzed,
      unit: lang === "en" ? "versions" : "versi artikel",
      description:
        lang === "en"
          ? "Raw ingested articles from verified RSS feeds and official press releases."
          : "Penyerapan artikel berita terverifikasi dari RSS dan feed resmi.",
    },
    {
      title: lang === "en" ? "Atomic Claims Extracted" : "Klaim Atomik Terekstraksi",
      count: data.claims_extracted,
      unit: lang === "en" ? "grounded claims" : "butir klaim fakta",
      description:
        lang === "en"
          ? "Grounded verbatim text spans, numbers, and timestamps extracted without fabrication."
          : "Ekstraksi kutipan verbatim, angka, lokasi, dan waktu tanpa halusinasi.",
    },
    {
      title: lang === "en" ? "Candidate Events Evaluated" : "Kandidat Klaster Dievaluasi",
      count: data.candidate_events_considered,
      unit: lang === "en" ? "candidates" : "kandidat klaster",
      description:
        lang === "en"
          ? "Hard constraint gating (temporal, geo, taxonomy) and pgvector semantic embeddings."
          : "Penyaringan batasan keras (waktu, lokasi, taksonomi) dan embedding semantik pgvector.",
    },
    {
      title: lang === "en" ? "Timeline Points Constructed" : "Entri Linimasa Terbentuk",
      count: data.timeline_entries,
      unit: lang === "en" ? "timeline nodes" : "peristiwa kronologis",
      description:
        lang === "en"
          ? "Chronological reconstruction with precision temporal qualifiers and source lineage."
          : "Rekonstruksi kronologis urutan waktu WIB dengan precision qualifier.",
    },
    {
      title: lang === "en" ? "Factual Discrepancies Detected" : "Konflik Faktual Terdeteksi",
      count: data.conflicts_detected,
      unit: lang === "en" ? "divergences" : "pertentangan klaim",
      description:
        lang === "en"
          ? "Cross-article numerical and categorical claim discrepancies highlighted for review."
          : "Deteksi perbedaan angka dan klaim antar laporan media yang disajikan transparan.",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header telemetry info */}
      <div className="border-b-[1.5px] border-[var(--ink)] pb-4">
        <h3 className="font-serif text-2xl font-bold text-[var(--ink)]">
          {lang === "en" ? "Processing Funnel & Telemetry" : "Corong Pemrosesan AI & Telemetri"}
        </h3>
        <p className="text-xs text-[var(--ink2)] mt-1 font-sans">
          {lang === "en"
            ? "Exact step-by-step telemetry counters sourced directly from processing run: "
            : "Metrik kuantitatif berurutan bersumber langsung dari run pemrosesan: "}
          <span className="font-mono text-[var(--ink)] font-semibold">{data.processing_run_id}</span>
        </p>
      </div>

      {/* Numbered List Layout (DESIGN.md Section 7: aturan 3px di atas item pertama, 1px antar item, angka besar serif 56px di kiri 84px) */}
      <div className="border-t-[3px] border-[var(--ink)] divide-y divide-[var(--line)]">
        {steps.map((step, idx) => {
          return (
            <div
              key={idx}
              className="grid grid-cols-[84px_1fr] gap-4 sm:gap-6 py-6 items-baseline"
            >
              {/* Kolom Kiri: Angka besar serif 56px rata kanan */}
              <div className="text-right">
                <span className="font-serif text-4xl sm:text-[54px] leading-none font-semibold text-[var(--ink)]">
                  {step.count}
                </span>
              </div>

              {/* Kolom Kanan: Judul sans 17px/600 + satuan kecil redup, deskripsi 14.5px ink2 */}
              <div className="space-y-1">
                <div className="flex flex-wrap items-baseline gap-2">
                  <h4 className="font-sans text-[16px] sm:text-[17px] font-semibold text-[var(--ink)]">
                    {step.title}
                  </h4>
                  <span className="text-[11px] font-mono text-[var(--ink2)] opacity-80">
                    ({step.unit})
                  </span>
                </div>
                <p className="text-[14px] sm:text-[14.5px] text-[var(--ink2)] leading-relaxed font-sans">
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
