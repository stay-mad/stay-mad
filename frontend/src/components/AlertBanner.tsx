"use client";

import React from "react";
import { ArrowRight, AlertCircle } from "lucide-react";
import { EventSummary } from "@/lib/types";
import { Language } from "@/lib/i18n";

interface AlertBannerProps {
  urgentEvents: EventSummary[];
  lang?: Language;
}

export function AlertBanner({ urgentEvents, lang = "id" }: AlertBannerProps) {
  if (!urgentEvents || urgentEvents.length === 0) return null;

  const topEvent = urgentEvents[0];

  return (
    <div className="relative rounded-[4px] border-l-4 border-l-red-600 border border-red-200 dark:border-red-900/60 bg-red-50/70 dark:bg-red-950/30 p-4 transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[3px] bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300">
            <AlertCircle className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold tracking-wider uppercase text-red-700 dark:text-red-300">
                {lang === "en" ? "OFFICIAL NOTICE: ACTION REQUIRED" : "PERINGATAN RESMI: TINDAKAN DARURAT"}
              </span>
              <span className="text-[11px] text-stone-500 dark:text-stone-400">·</span>
              <span className="text-[11px] text-stone-600 dark:text-stone-300">
                {lang === "en" ? "Government Authority" : "Otoritas Terverifikasi"}
              </span>
            </div>
            <h4 className="mt-0.5 text-sm font-serif font-bold text-stone-900 dark:text-stone-100">
              {topEvent.headline}
            </h4>
            <p className="text-xs text-stone-600 dark:text-stone-300 line-clamp-1 mt-0.5">
              {topEvent.confidence_signals.signals_text[0] ||
                (lang === "en" ? "Follow safety guidance from BPBD/BNPB." : "Ikuti protokol evakuasi dan instruksi keselamatan dari BPBD/BNPB.")}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 sm:self-center">
          <a
            href={`/events/${topEvent.id}`}
            className="inline-flex items-center gap-1.5 rounded-[4px] bg-red-700 hover:bg-red-800 text-white px-3 py-1.5 text-xs font-medium transition-colors"
          >
            <span>{lang === "en" ? "Read Instructions" : "Lihat Instruksi Resmi"}</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}
