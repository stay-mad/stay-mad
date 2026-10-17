"use client";

import React, { Suspense, useEffect, use, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Cpu,
  Eye,
  GitCommit,
  MapPin,
  Newspaper,
  Share2,
  ShieldAlert,
} from "lucide-react";
import { ConfidenceBreakdown } from "@/components/ConfidenceBreakdown";
import { ConflictsView } from "@/components/ConflictsView";
import { EvidencePopover } from "@/components/EvidencePopover";
import { ImportanceBreakdown } from "@/components/ImportanceBreakdown";
import { Navbar } from "@/components/Navbar";
import { PipelineFunnel } from "@/components/PipelineFunnel";
import { SourcesView } from "@/components/SourcesView";
import { TimelineView } from "@/components/TimelineView";
import { ChangesView } from "@/components/ChangesView";
import { api } from "@/lib/api";
import {
  AnalysisResponse,
  ChangesResponse,
  DataMode,
  EventDetailResponse,
  ProcessingResponse,
  SourcesResponse,
  TimelineResponse,
} from "@/lib/types";
import {
  formatWibDateTime,
  getActionabilityBadge,
  getCategoryLabel,
  getUrgencyBadge,
  getVerificationBadge,
} from "@/lib/utils";
import { Language, getTranslation } from "@/lib/i18n";

type ActiveTab = "overview" | "timeline" | "sources" | "changes" | "processing";

function EventDetailContent({ params }: { params: Promise<{ id: string }> }) {
  const unwrappedParams = use(params);
  const eventId = unwrappedParams.id;

  const [dataMode, setDataMode] = useState<DataMode>("live");
  const [selectedLocation, setSelectedLocation] = useState<string>("");
  const [lang, setLang] = useState<Language>("id");
  const [activeTab, setActiveTab] = useState<ActiveTab>("overview");

  // Hydration safety: sync saved client preferences after mount
  useEffect(() => {
    const savedMode = localStorage.getItem("staymad_datamode") as DataMode | null;
    if (savedMode === "live" || savedMode === "demo" || savedMode === "degraded") {
      setDataMode(savedMode);
    }
    const savedLang = localStorage.getItem("staymad_lang") as Language | null;
    if (savedLang === "id" || savedLang === "en") {
      setLang(savedLang);
    }
  }, []);

  const handleModeChange = (mode: DataMode) => {
    setDataMode(mode);
    if (typeof window !== "undefined") {
      localStorage.setItem("staymad_datamode", mode);
    }
  };

  const handleLangChange = (newLang: Language) => {
    setLang(newLang);
    if (typeof window !== "undefined") {
      localStorage.setItem("staymad_lang", newLang);
    }
  };

  const [event, setEvent] = useState<EventDetailResponse | null>(null);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [sources, setSources] = useState<SourcesResponse | null>(null);
  const [changes, setChanges] = useState<ChangesResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [processing, setProcessing] = useState<ProcessingResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Evidence Popover State
  const [activeEvidenceClaimId, setActiveEvidenceClaimId] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<boolean>(false);

  const t = getTranslation(lang);

  useEffect(() => {
    if (!eventId) return;

    let isMounted = true;

    // Fetch all related endpoints concurrently
    Promise.allSettled([
      api.getEvent(eventId),
      api.getEventTimeline(eventId),
      api.getEventSources(eventId),
      api.getEventChanges(eventId),
      api.getEventAnalysis(eventId),
      api.getEventProcessing(eventId),
    ]).then(([evRes, tlRes, srcRes, chgRes, anRes, procRes]) => {
      if (!isMounted) return;

      if (evRes.status === "fulfilled") {
        setEvent(evRes.value);
        setErrorMsg(null);
      } else {
        setErrorMsg(lang === "en" ? "Event not found or connection error." : "Peristiwa tidak ditemukan atau terjadi kesalahan koneksi.");
      }

      if (tlRes.status === "fulfilled") setTimeline(tlRes.value);
      if (srcRes.status === "fulfilled") setSources(srcRes.value);
      if (chgRes.status === "fulfilled") setChanges(chgRes.value);
      if (anRes.status === "fulfilled") setAnalysis(anRes.value);
      if (procRes.status === "fulfilled") setProcessing(procRes.value);

      setIsLoading(false);
    });

    return () => {
      isMounted = false;
    };
  }, [eventId, lang]);

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    }
  };

  // Find source matching claim id if possible
  const selectedClaimSource = React.useMemo(() => {
    if (!activeEvidenceClaimId || !sources?.sources) return undefined;
    return sources.sources[0];
  }, [activeEvidenceClaimId, sources]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)]">
        <Navbar
          currentMode={dataMode}
          onModeChange={setDataMode}
          selectedLocation={selectedLocation}
          onLocationChange={setSelectedLocation}
          lang={lang}
          onLangChange={setLang}
        />
        <div className="mx-auto max-w-[1120px] px-4 sm:px-6 py-12 space-y-6 animate-pulse">
          <div className="h-4 w-32 bg-[var(--tint)] rounded" />
          <div className="h-12 w-3/4 bg-[var(--tint)] rounded" />
          <div className="h-4 w-1/2 bg-[var(--tint)] rounded" />
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-10 mt-8">
            <div className="h-96 bg-[var(--surface)] border-[1.5px] border-[var(--line)] rounded-2xl" />
            <div className="h-96 bg-[var(--surface)] border-[1.5px] border-[var(--line)] rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  if (errorMsg || !event) {
    return (
      <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)]">
        <Navbar
          currentMode={dataMode}
          onModeChange={setDataMode}
          selectedLocation={selectedLocation}
          onLocationChange={setSelectedLocation}
          lang={lang}
          onLangChange={setLang}
        />
        <div className="mx-auto max-w-xl px-4 py-16 text-center text-xs">
          <div className="rounded-2xl border-[1.5px] border-[var(--danger)] bg-[var(--dangerbg)] p-8 space-y-3">
            <h2 className="text-lg font-serif font-bold text-[var(--danger)]">
              {lang === "en" ? "Failed to Load Event" : "Gagal Memuat Peristiwa"}
            </h2>
            <p className="text-sm text-[var(--ink2)]">{errorMsg}</p>
            <div className="pt-3">
              <Link
                href="/"
                className="inline-block rounded-xl bg-[var(--ink)] text-[var(--bg)] px-5 py-2.5 text-xs font-semibold hover:bg-[var(--accent)] transition-colors"
              >
                {t.backToOverview}
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const urgency = getUrgencyBadge(event.urgency_score, event.importance_score, lang);
  const verification = getVerificationBadge(
    event.confidence_signals.verification_level,
    lang
  );
  const actionability = getActionabilityBadge(event.actionability_level, lang);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)] font-sans">
      <Navbar
        currentMode={dataMode}
        onModeChange={handleModeChange}
        selectedLocation={selectedLocation}
        onLocationChange={setSelectedLocation}
        lang={lang}
        onLangChange={handleLangChange}
      />

      {/* Main Container max-w-[1120px] per DESIGN.md §5 */}
      <main className="mx-auto max-w-[1120px] px-4 sm:px-6 py-8 space-y-8">
        {/* Navigation & Utility Header */}
        <div className="flex items-center justify-between text-xs">
          <Link
            href="/"
            className="inline-flex items-center gap-2 font-medium text-[var(--ink2)] hover:text-[var(--ink)] transition-colors group"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
            <span className="font-semibold">{t.backToOverview}</span>
          </Link>

          <div className="flex items-center gap-2">
            <button
              onClick={handleShare}
              className="inline-flex items-center gap-1.5 rounded-[10px] border-[1.5px] border-[var(--ink)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--ink)] hover:bg-[var(--hover)] transition-colors"
            >
              <Share2 className="h-3.5 w-3.5 text-[var(--ink2)]" />
              <span>{copyFeedback ? t.linkCopied : t.share}</span>
            </button>
            <button
              onClick={() => setActiveTab("processing")}
              className="inline-flex items-center gap-1.5 rounded-[10px] border-[1.5px] border-[var(--line)] bg-[var(--tint)] px-3 py-1.5 text-xs font-mono font-medium text-[var(--ink)] hover:border-[var(--ink)] transition-colors"
              title="Audit Transparansi Pemrosesan AI (Screen 3 / Addendum §5.8)"
            >
              <Cpu className="h-3.5 w-3.5 text-[var(--accent)]" />
              <span>{lang === "en" ? "AI Audit" : "Audit AI"}</span>
            </button>
          </div>
        </div>

        {/* Article Header (Masthead): Max 2 visual pills per DESIGN.md §7, Newsreader clamp headline */}
        <header className="border-b-[1.5px] border-[var(--line)] pb-6 space-y-3">
          {/* 2 Pills Max per DESIGN.md: Urgensi (warn) and Verified (accent) */}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="inline-flex items-center gap-1 rounded-full px-3 py-0.5 text-xs font-bold border-[1.5px] border-[var(--warn)] text-[var(--warn)] bg-[var(--warnbg)]"
            >
              {urgency.label}
            </span>

            <span
              className="inline-flex items-center gap-1 rounded-full px-3 py-0.5 text-xs font-semibold border-[1.5px] border-[var(--accent)] text-[var(--accent)] bg-[var(--tint)]"
            >
              {verification.label}
            </span>
          </div>

          {/* Headline: clamp(32px, 5.2vw, 52px), line-height 1.1, max-w ~20ch */}
          <h1 className="font-serif font-semibold text-[clamp(32px,5.2vw,52px)] leading-[1.1] tracking-[-0.018em] max-w-[20ch] text-[var(--ink)] pt-1">
            {event.headline}
          </h1>

          {/* Plain Meta Text separated by dots */}
          <div className="flex flex-wrap items-center gap-y-1 gap-x-3 text-xs text-[var(--ink2)] font-sans pt-1">
            <div className="flex items-center gap-1 font-semibold text-[var(--ink)]">
              <MapPin className="h-3.5 w-3.5 text-[var(--ink2)]" />
              <span>{event.primary_location?.canonical_name || "Indonesia"}</span>
            </div>
            <span>·</span>
            <span>{getCategoryLabel(event.category, lang)}</span>
            <span>·</span>
            <div className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 text-[var(--ink2)]" />
              <span>
                {t.updatedAt}: {formatWibDateTime(event.last_processed_at, lang)}
              </span>
            </div>
            <span>·</span>
            <div className="font-mono text-[11px] text-[var(--ink2)] opacity-80">
              Run: {event.processing_run_id.slice(0, 8)} / Snap: {event.snapshot_id.slice(0, 8)}
            </div>
          </div>
        </header>

        {/* Official Emergency Action Banner (DESIGN.md §7: dangerbg, border 1.5px danger, serif title, 16px text) */}
        {actionability.isUrgent && (
          <section className="rounded-2xl border-[1.5px] border-[var(--danger)] bg-[var(--dangerbg)] p-6 text-xs space-y-3">
            <div className="flex items-start gap-3.5">
              <ShieldAlert className="h-6 w-6 text-[var(--danger)] shrink-0 mt-0.5" />
              <div className="space-y-2">
                <div className="inline-flex items-center rounded-md bg-[var(--danger)] text-white px-2.5 py-0.5 text-[11px] font-bold tracking-wide">
                  {actionability.label}
                </div>
                <h4 className="font-serif font-bold text-lg text-[var(--ink)]">
                  {t.officialInstructions}
                </h4>
                {event.actions && event.actions.length > 0 ? (
                  <ul className="space-y-2 text-base font-sans text-[var(--ink)]">
                    {event.actions.map((act, idx) => (
                      <li key={idx} className="flex items-start gap-2.5">
                        <span className="text-[var(--danger)] font-bold">•</span>
                        <span>{act.action_text}</span>
                        {act.evidence_claim_ids?.map((cid, cIdx) => (
                          <button
                            key={cIdx}
                            onClick={() => setActiveEvidenceClaimId(cid)}
                            className="font-mono text-[12px] font-semibold text-[var(--danger)] underline hover:opacity-80 inline-flex items-center ml-1"
                          >
                            [{lang === "en" ? "Evidence" : "Bukti"} #{cid.slice(0, 8)}]
                          </button>
                        ))}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-base font-sans text-[var(--ink)]">
                    {lang === "en"
                      ? "Follow official safety and evacuation instructions from BPBD / BNPB."
                      : "Patuhi instruksi resmi dari BPBD / BNPB terkait jalur evakuasi dan mitigasi risiko."}
                  </p>
                )}
              </div>
            </div>
          </section>
        )}

        {/* 5 Tabs Bar: border-b 1.5px --ink, active tab bg --ink text --bg rounded-t-10px */}
        <div className="border-b-[1.5px] border-[var(--ink)]">
          <nav className="flex gap-1 overflow-x-auto -mb-[1.5px] pb-[1px]" role="tablist">
            <button
              role="tab"
              aria-selected={activeTab === "overview"}
              onClick={() => setActiveTab("overview")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-sans transition-colors whitespace-nowrap rounded-t-[10px] ${
                activeTab === "overview"
                  ? "bg-[var(--ink)] text-[var(--bg)] font-semibold border-t-[1.5px] border-x-[1.5px] border-[var(--ink)]"
                  : "text-[var(--ink2)] hover:text-[var(--ink)] hover:bg-[var(--hover)] font-medium"
              }`}
            >
              <Eye className="h-3.5 w-3.5" />
              <span>1. {t.tabOverview}</span>
            </button>

            <button
              role="tab"
              aria-selected={activeTab === "timeline"}
              onClick={() => setActiveTab("timeline")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-sans transition-colors whitespace-nowrap rounded-t-[10px] ${
                activeTab === "timeline"
                  ? "bg-[var(--ink)] text-[var(--bg)] font-semibold border-t-[1.5px] border-x-[1.5px] border-[var(--ink)]"
                  : "text-[var(--ink2)] hover:text-[var(--ink)] hover:bg-[var(--hover)] font-medium"
              }`}
            >
              <Clock className="h-3.5 w-3.5" />
              <span>2. {t.tabTimeline}</span>
              {timeline?.entries?.length ? (
                <span className={`px-1.5 py-0.2 rounded-full font-mono text-[10px] ${
                  activeTab === "timeline"
                    ? "bg-[var(--bg)] text-[var(--ink)]"
                    : "bg-[var(--tint)] text-[var(--ink2)]"
                }`}>
                  {timeline.entries.length}
                </span>
              ) : null}
            </button>

            <button
              role="tab"
              aria-selected={activeTab === "sources"}
              onClick={() => setActiveTab("sources")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-sans transition-colors whitespace-nowrap rounded-t-[10px] ${
                activeTab === "sources"
                  ? "bg-[var(--ink)] text-[var(--bg)] font-semibold border-t-[1.5px] border-x-[1.5px] border-[var(--ink)]"
                  : "text-[var(--ink2)] hover:text-[var(--ink)] hover:bg-[var(--hover)] font-medium"
              }`}
            >
              <Newspaper className="h-3.5 w-3.5" />
              <span>3. {t.tabSources}</span>
              {sources?.sources?.length ? (
                <span className={`px-1.5 py-0.2 rounded-full font-mono text-[10px] ${
                  activeTab === "sources"
                    ? "bg-[var(--bg)] text-[var(--ink)]"
                    : "bg-[var(--tint)] text-[var(--ink2)]"
                }`}>
                  {sources.sources.length}
                </span>
              ) : null}
            </button>

            <button
              role="tab"
              aria-selected={activeTab === "changes"}
              onClick={() => setActiveTab("changes")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-sans transition-colors whitespace-nowrap rounded-t-[10px] ${
                activeTab === "changes"
                  ? "bg-[var(--ink)] text-[var(--bg)] font-semibold border-t-[1.5px] border-x-[1.5px] border-[var(--ink)]"
                  : "text-[var(--ink2)] hover:text-[var(--ink)] hover:bg-[var(--hover)] font-medium"
              }`}
            >
              <GitCommit className="h-3.5 w-3.5" />
              <span>4. {t.tabChanges}</span>
              {changes?.material_change_count ? (
                <span className={`px-1.5 py-0.2 rounded-full font-mono text-[10px] font-bold ${
                  activeTab === "changes"
                    ? "bg-[var(--accent)] text-[var(--bg)]"
                    : "bg-[var(--tint)] text-[var(--accent)]"
                }`}>
                  {changes.material_change_count}
                </span>
              ) : null}
            </button>

            <button
              role="tab"
              aria-selected={activeTab === "processing"}
              onClick={() => setActiveTab("processing")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-sans transition-colors whitespace-nowrap rounded-t-[10px] ${
                activeTab === "processing"
                  ? "bg-[var(--ink)] text-[var(--bg)] font-semibold border-t-[1.5px] border-x-[1.5px] border-[var(--ink)]"
                  : "text-[var(--ink2)] hover:text-[var(--ink)] hover:bg-[var(--hover)] font-medium"
              }`}
            >
              <Cpu className="h-3.5 w-3.5" />
              <span>5. {t.tabProcessing}</span>
            </button>
          </nav>
        </div>

        {/* Tab 1: Editorial 2-Column Split (Article + Sticky 340px Sidebar, 56px gap) */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-8 lg:gap-14 items-start">
            {/* Left Column: Editorial Reading (3.5px rule on top, sentence-case titles, 19px serif body) */}
            <div className="space-y-10">
              {/* Conflicts Callout if any */}
              {analysis?.conflicts && analysis.conflicts.length > 0 && (
                <ConflictsView
                  conflicts={analysis.conflicts}
                  onSelectClaim={(cid) => setActiveEvidenceClaimId(cid)}
                  lang={lang}
                />
              )}

              {/* 3.5px rule on top of article reading section per DESIGN.md §4 */}
              <div className="border-t-[3.5px] border-[var(--ink)] pt-6 space-y-9">
                {/* Section 1: Apa yang terjadi */}
                <article className="space-y-3">
                  <h2 className="font-sans text-[15px] font-semibold text-[var(--ink2)] flex items-baseline">
                    <span>{t.whatHappened}</span>
                    {lang === "id" && (
                      <small className="text-xs text-[var(--ink2)] opacity-75 font-normal ml-2">
                        What happened
                      </small>
                    )}
                  </h2>
                  <div className="font-serif text-[19px] leading-[1.7] text-[var(--ink)] max-w-[68ch]">
                    <p>{event.what_happened.text || (lang === "en" ? "No narrative details." : "Tidak ada rincian narasi.")}</p>
                  </div>

                  {/* Evidence Citations */}
                  {event.what_happened.evidence_claim_ids &&
                    event.what_happened.evidence_claim_ids.length > 0 && (
                      <div className="flex flex-wrap items-center gap-2 pt-2 text-xs">
                        <span className="text-[11px] text-[var(--ink2)] font-sans">
                          {lang === "en" ? "Supporting Citations:" : "Klaim Bukti Pendukung:"}
                        </span>
                        {event.what_happened.evidence_claim_ids.map((cid, i) => (
                          <button
                            key={i}
                            onClick={() => setActiveEvidenceClaimId(cid)}
                            className="font-mono text-[12.5px] text-[var(--accent)] bg-[var(--tint)] border-[1.5px] border-[var(--line)] rounded-lg px-2.5 py-0.5 min-h-[28px] hover:border-[var(--ink)] hover:text-[var(--ink)] transition-colors inline-flex items-center"
                            title={lang === "en" ? "Inspect original source quotation" : "Klik untuk melihat teks kutipan asli dan sumber"}
                          >
                            [{lang === "en" ? "Evidence" : "Bukti"} #{cid.slice(0, 8)}]
                          </button>
                        ))}
                      </div>
                    )}
                </article>

                {/* Section 2: Mengapa ini penting */}
                {event.why_it_matters?.text && (
                  <article className="border-t border-[var(--line)] pt-7 space-y-3">
                    <h2 className="font-sans text-[15px] font-semibold text-[var(--ink2)] flex items-baseline">
                      <span>{t.whyItMatters}</span>
                      {lang === "id" && (
                        <small className="text-xs text-[var(--ink2)] opacity-75 font-normal ml-2">
                          Why it matters
                        </small>
                      )}
                    </h2>
                    <div className="font-serif text-[19px] leading-[1.7] text-[var(--ink)] max-w-[68ch]">
                      <p>{event.why_it_matters.text}</p>
                    </div>

                    {event.why_it_matters.evidence_claim_ids &&
                      event.why_it_matters.evidence_claim_ids.length > 0 && (
                        <div className="flex flex-wrap items-center gap-2 pt-2 text-xs">
                          <span className="text-[11px] text-[var(--ink2)] font-sans">
                            {lang === "en" ? "Supporting Citations:" : "Klaim Bukti:"}
                          </span>
                          {event.why_it_matters.evidence_claim_ids.map((cid, i) => (
                            <button
                              key={i}
                              onClick={() => setActiveEvidenceClaimId(cid)}
                              className="font-mono text-[12.5px] text-[var(--accent)] bg-[var(--tint)] border-[1.5px] border-[var(--line)] rounded-lg px-2.5 py-0.5 min-h-[28px] hover:border-[var(--ink)] hover:text-[var(--ink)] transition-colors inline-flex items-center"
                            >
                              [{lang === "en" ? "Evidence" : "Bukti"} #{cid.slice(0, 8)}]
                            </button>
                          ))}
                        </div>
                      )}
                  </article>
                )}

                {/* Section 3: Siapa yang terdampak */}
                {event.who_is_affected?.text && (
                  <article className="border-t border-[var(--line)] pt-7 space-y-3">
                    <h2 className="font-sans text-[15px] font-semibold text-[var(--ink2)] flex items-baseline">
                      <span>{t.whoIsAffected}</span>
                      {lang === "id" && (
                        <small className="text-xs text-[var(--ink2)] opacity-75 font-normal ml-2">
                          Who is affected
                        </small>
                      )}
                    </h2>
                    <div className="font-serif text-[19px] leading-[1.7] text-[var(--ink)] max-w-[68ch]">
                      <p>{event.who_is_affected.text}</p>
                    </div>

                    {event.who_is_affected.evidence_claim_ids &&
                      event.who_is_affected.evidence_claim_ids.length > 0 && (
                        <div className="flex flex-wrap items-center gap-2 pt-2 text-xs">
                          <span className="text-[11px] text-[var(--ink2)] font-sans">
                            {lang === "en" ? "Supporting Citations:" : "Klaim Bukti:"}
                          </span>
                          {event.who_is_affected.evidence_claim_ids.map((cid, i) => (
                            <button
                              key={i}
                              onClick={() => setActiveEvidenceClaimId(cid)}
                              className="font-mono text-[12.5px] text-[var(--accent)] bg-[var(--tint)] border-[1.5px] border-[var(--line)] rounded-lg px-2.5 py-0.5 min-h-[28px] hover:border-[var(--ink)] hover:text-[var(--ink)] transition-colors inline-flex items-center"
                            >
                              [{lang === "en" ? "Evidence" : "Bukti"} #{cid.slice(0, 8)}]
                            </button>
                          ))}
                        </div>
                      )}
                  </article>
                )}

                {/* Section 4: Fakta belum terkonfirmasi */}
                {event.what_is_unknown?.text && (
                  <div className="border-t border-[var(--line)] pt-7 space-y-2">
                    <h2 className="font-sans text-[15px] font-semibold text-[var(--ink2)] flex items-baseline">
                      <span>{t.whatIsUnknown}</span>
                      {lang === "id" && (
                        <small className="text-xs text-[var(--ink2)] opacity-75 font-normal ml-2">
                          What is unknown
                        </small>
                      )}
                    </h2>
                    <blockquote className="border-l-[3px] border-[var(--line)] pl-4 py-1 font-serif italic text-base text-[var(--ink2)] leading-relaxed max-w-[68ch]">
                      &ldquo;{event.what_is_unknown.text}&rdquo;
                    </blockquote>
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Sticky 340px Editorial Sidebar */}
            <aside className="lg:sticky lg:top-6 space-y-6">
              <ConfidenceBreakdown signals={event.confidence_signals} lang={lang} />
              <ImportanceBreakdown
                importanceScore={event.importance_score}
                urgencyScore={event.urgency_score}
                lang={lang}
              />
            </aside>
          </div>
        )}

        {/* Tab 2: Linimasa Kronologis */}
        {activeTab === "timeline" && (
          <div className="space-y-6">
            <TimelineView
              entries={timeline?.entries || []}
              onSelectClaim={(cid) => setActiveEvidenceClaimId(cid)}
              lang={lang}
            />
          </div>
        )}

        {/* Tab 3: Sumber Berita & Keluarga Media */}
        {activeTab === "sources" && sources && (
          <div className="space-y-6">
            <SourcesView data={sources} lang={lang} />
          </div>
        )}

        {/* Tab 4: Riwayat Perubahan Material */}
        {activeTab === "changes" && changes && (
          <div className="space-y-6">
            <ChangesView
              data={changes}
              onSelectClaim={(cid) => setActiveEvidenceClaimId(cid)}
              lang={lang}
            />
          </div>
        )}

        {/* Tab 5: Processing & AI Audit Transparency */}
        {activeTab === "processing" && processing && (
          <div className="space-y-8">
            {/* Top Funnel Diagram */}
            <PipelineFunnel data={processing} lang={lang} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
              {/* Confidence Breakdown Model */}
              <ConfidenceBreakdown
                signals={processing.confidence_signals || event.confidence_signals}
                lang={lang}
              />

              {/* Resolution Decision Audit Log Card */}
              <div className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-6 space-y-5">
                <div className="border-b-[1.5px] border-[var(--line)] pb-4">
                  <div className="flex items-center gap-2 text-xs font-mono text-[var(--accent)] mb-1">
                    <Cpu className="h-4 w-4" />
                    <span className="font-semibold">RESOLVER TELEMETRY</span>
                  </div>
                  <h3 className="text-lg font-serif font-bold text-[var(--ink)]">
                    {lang === "en" ? "Event Resolution Audit Log" : "Audit Resolusi Keanggotaan Event"}
                  </h3>
                  <p className="text-xs text-[var(--ink2)] mt-1 leading-relaxed">
                    {lang === "en"
                      ? "Auditable resolver decision telemetry without internal chain-of-thought exposure."
                      : "Menampilkan jalur klasifikasi resolver tanpa membocorkan internal chain-of-thought."}
                    <span
                      className="ml-1 cursor-help font-mono border-b border-dotted border-[var(--ink2)]"
                      title="Kepatuhan Addendum §5.8 (Conflict #7)"
                    >
                      [Addendum §5.8]
                    </span>
                  </p>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between rounded-xl border border-[var(--line)] bg-[var(--tint)]/50 p-3">
                    <span className="text-[var(--ink2)] font-medium">
                      {lang === "en" ? "Resolver Tier:" : "Tingkat Resolver (Tier Digunakan):"}
                    </span>
                    <span className="font-bold text-[var(--accent)] font-mono">
                      {processing.resolution_tier_used || "TIER_1 (Deterministik)"}
                    </span>
                  </div>

                  <div className="rounded-xl border border-[var(--line)] bg-[var(--tint)]/50 p-3 space-y-1.5">
                    <span className="text-[var(--ink2)] block font-medium">
                      {lang === "en" ? "Decision Reason Codes:" : "Kode Alasan Keputusan:"}
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {processing.decision_reason_codes &&
                      processing.decision_reason_codes.length > 0 ? (
                        processing.decision_reason_codes.map((code, idx) => (
                          <span
                            key={idx}
                            className="rounded-lg bg-[var(--surface)] border-[1.5px] border-[var(--line)] px-2 py-0.5 font-mono text-[var(--ink)] font-semibold text-[11px]"
                          >
                            {code}
                          </span>
                        ))
                      ) : (
                        <span className="font-mono text-[var(--ink2)] text-[11px]">
                          [&apos;LOC_MATCH&apos;, &apos;CORROBORATED&apos;]
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-[var(--line)] bg-[var(--tint)]/50 p-3 font-mono text-[11px]">
                    <span className="text-[var(--ink2)]">Gemini Model:</span>
                    <span className="text-[var(--ink)] font-semibold">{processing.model_version}</span>
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-[var(--line)] bg-[var(--tint)]/50 p-3 font-mono text-[11px]">
                    <span className="text-[var(--ink2)]">Prompt Version:</span>
                    <span className="text-[var(--ink)] font-semibold">{processing.prompt_version}</span>
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-[var(--line)] bg-[var(--tint)]/50 p-3 font-mono text-[11px]">
                    <span className="text-[var(--ink2)]">JSON Schema Version:</span>
                    <span className="text-[var(--ink)] font-semibold">{processing.schema_version}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Evidence Popover Modal / Drawer */}
        {activeEvidenceClaimId && (
          <EvidencePopover
            claimId={activeEvidenceClaimId}
            source={selectedClaimSource}
            onClose={() => setActiveEvidenceClaimId(null)}
            lang={lang}
          />
        )}
      </main>
    </div>
  );
}

export default function EventDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[var(--bg)] flex items-center justify-center text-xs text-[var(--ink2)]">
          Memuat rincian peristiwa...
        </div>
      }
    >
      <EventDetailContent params={params} />
    </Suspense>
  );
}
