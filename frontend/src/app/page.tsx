"use client";

import React, { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  Building2,
  ChevronLeft,
  ChevronRight,
  CloudRain,
  Compass,
  FileText,
  Layers,
  MapPin,
  RefreshCw,
  ShieldCheck,
  Train,
} from "lucide-react";
import { AlertBanner } from "@/components/AlertBanner";
import { EventCard } from "@/components/EventCard";
import { Navbar } from "@/components/Navbar";
import { api } from "@/lib/api";
import {
  DataMode,
  EventCategory,
  EventSummary,
  EventSummaryStats,
} from "@/lib/types";
import { Language, getTranslation } from "@/lib/i18n";

const ITEMS_PER_PAGE = 12;

function SituationalOverviewContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Read initial states from URL query parameters (or defaults)
  const initialPage = Math.max(1, parseInt(searchParams.get("page") || "1", 10));
  const initialCategory = searchParams.get("category") || "all";
  const initialLocation = searchParams.get("location") || "";
  const initialQuery = searchParams.get("q") || "";

  const [dataMode, setDataMode] = useState<DataMode>("live");

  const [lang, setLang] = useState<Language>(() => {
    const urlLang = searchParams.get("lang");
    if (urlLang === "en" || urlLang === "id") return urlLang;
    return "id";
  });

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

  const [selectedCategory, setSelectedCategory] = useState<string>(initialCategory);
  const [selectedLocation, setSelectedLocation] = useState<string>(initialLocation);
  const [searchQuery, setSearchQuery] = useState<string>(initialQuery);
  const [page, setPage] = useState<number>(initialPage);

  const [events, setEvents] = useState<EventSummary[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [summaryStats, setSummaryStats] = useState<EventSummaryStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState<number>(0);

  const t = getTranslation(lang);

  // Sync state changes to browser URL query params
  const updateUrlParams = (
    newPage: number,
    newCat: string,
    newLoc: string,
    newQ: string
  ) => {
    const params = new URLSearchParams();
    if (newPage > 1) params.set("page", String(newPage));
    if (newCat && newCat !== "all") params.set("category", newCat);
    if (newLoc) params.set("location", newLoc);
    if (newQ.trim()) params.set("q", newQ.trim());

    const qs = params.toString();
    const newPath = qs ? `/?${qs}` : "/";
    router.replace(newPath, { scroll: false });
  };

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

  const handleCategoryChange = (catId: string) => {
    setSelectedCategory(catId);
    setPage(1);
    updateUrlParams(1, catId, selectedLocation, searchQuery);
  };

  const handleLocationChange = (loc: string) => {
    setSelectedLocation(loc);
    setPage(1);
    updateUrlParams(1, selectedCategory, loc, searchQuery);
  };

  const handleSearchChange = (q: string) => {
    setSearchQuery(q);
    setPage(1);
    updateUrlParams(1, selectedCategory, selectedLocation, q);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    updateUrlParams(newPage, selectedCategory, selectedLocation, searchQuery);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const fetchEvents = () => {
    setIsLoading(true);
    setReloadKey((k) => k + 1);
  };

  // Main API Data Fetching with Server-Side Pagination & Filtering
  useEffect(() => {
    let ignore = false;

    async function load() {
      setIsLoading(true);
      try {
        const categoryParam =
          selectedCategory !== "all"
            ? (selectedCategory as EventCategory)
            : undefined;

        const offset = (page - 1) * ITEMS_PER_PAGE;

        const res = await api.listEvents({
          category: categoryParam,
          location: selectedLocation || undefined,
          data_mode: dataMode,
          q: searchQuery.trim() || undefined,
          limit: ITEMS_PER_PAGE,
          offset: offset,
        });

        if (!ignore) {
          setEvents(res.events || []);
          setTotalCount(res.total || 0);
          setSummaryStats(res.summary_stats || null);
          setErrorMsg(null);
        }
      } catch (err: unknown) {
        if (!ignore) {
          console.error("Gagal memuat event:", err);
          const msg =
            err instanceof Error
              ? err.message
              : "Gagal menghubungi backend Stay Mad (Port 8080). Pastikan backend aktif dengan perintah `make run-api`.";
          setErrorMsg(msg);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      ignore = true;
    };
  }, [dataMode, selectedCategory, selectedLocation, searchQuery, page, reloadKey]);

  // Urgent Events with ACTION_REQUIRED for alert banner
  const urgentEvents = useMemo(() => {
    return events.filter((ev) => ev.actionability_level === "ACTION_REQUIRED");
  }, [events]);

  // Derived pagination calculations
  const totalPages = Math.max(1, Math.ceil(totalCount / ITEMS_PER_PAGE));
  const startItem = totalCount === 0 ? 0 : (page - 1) * ITEMS_PER_PAGE + 1;
  const endItem = Math.min(page * ITEMS_PER_PAGE, totalCount);

  const categories = [
    { id: "all", label: t.allCategories, icon: Layers },
    {
      id: "disaster_and_weather",
      label: t.catDisaster,
      icon: CloudRain,
    },
    {
      id: "transportation_and_infrastructure",
      label: t.catTransport,
      icon: Train,
    },
    {
      id: "government_and_public_policy",
      label: t.catPolicy,
      icon: Building2,
    },
  ];

  // Quick Region Shortcuts
  const regionShortcuts = [
    { label: t.allRegions, value: "" },
    { label: "DKI Jakarta", value: "DKI Jakarta" },
    { label: "Jakarta Timur", value: "Jakarta Timur" },
    { label: "DI Yogyakarta", value: "DI Yogyakarta" },
  ];

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)]">
      {/* Two-Tier Editorial Header */}
      <Navbar
        currentMode={dataMode}
        onModeChange={handleModeChange}
        selectedLocation={selectedLocation}
        onLocationChange={handleLocationChange}
        lang={lang}
        onLangChange={handleLangChange}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
      />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Main Section Header */}
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 border-b-[1.5px] border-[var(--border-subtle)] pb-6 mb-7">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-[var(--accent-primary)] mb-1.5 font-bold">
              <Compass className="h-4 w-4" />
              <span>
                {lang === "en"
                  ? "Wire Desk · Situational Intelligence"
                  : "Ruang Redaksi · Situational Intelligence"}
              </span>
              <span
                className="text-[10px] text-[var(--text-muted)] border border-[var(--border-subtle)] rounded px-1.5 py-0.2"
                title="Sesuai Spesifikasi Master Spec §23 (Layar 1)"
              >
                §23
              </span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-serif font-black text-[var(--text-primary)] tracking-tight">
              {t.overviewTitle}
            </h1>
            <p className="mt-1.5 text-xs sm:text-sm text-[var(--text-secondary)] max-w-2xl leading-relaxed">
              {t.overviewSubtitle}
            </p>
          </div>

          {/* Quick Refresh & Scope Indicator */}
          <div className="flex items-center gap-3">
            {selectedLocation && (
              <span className="inline-flex items-center gap-1 rounded-lg border-[1.5px] border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 px-2.5 py-1 text-xs font-semibold text-emerald-800 dark:text-emerald-300">
                <MapPin className="h-3 w-3" />
                {selectedLocation}
              </span>
            )}
            <button
              onClick={fetchEvents}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 rounded-lg border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)] transition-all disabled:opacity-50 shadow-xs"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`}
              />
              <span>{isLoading ? t.refreshing : t.refresh}</span>
            </button>
          </div>
        </div>

        {/* Emergency Alert Banner for high-severity actions */}
        <div className="mb-6">
          <AlertBanner urgentEvents={urgentEvents} lang={lang} />
        </div>

        {/* 2-COLUMN NEWSPAPER SPLIT LAYOUT */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* LEFT / MAIN COLUMN (approx 68% width - 8 cols) */}
          <div className="lg:col-span-8 space-y-6">
            {/* Category Underline Navigation Tabs */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b-[1.5px] border-[var(--border-subtle)] pb-2">
              <div className="flex flex-wrap items-center gap-1 sm:gap-2">
                {categories.map((cat) => {
                  const Icon = cat.icon;
                  const isActive = selectedCategory === cat.id;
                  return (
                    <button
                      key={cat.id}
                      onClick={() => handleCategoryChange(cat.id)}
                      className={`inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold transition-all border-b-2 -mb-2.5 ${
                        isActive
                          ? "border-[var(--accent-primary)] text-[var(--text-primary)] font-bold"
                          : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      <span>{cat.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Active Search Badge (if search query is active) */}
              {searchQuery && (
                <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                  <span>
                    {lang === "en" ? "Filter:" : "Kata kunci:"}{" "}
                    <strong className="text-[var(--text-primary)]">&ldquo;{searchQuery}&rdquo;</strong>
                  </span>
                  <button
                    onClick={() => handleSearchChange("")}
                    className="text-[11px] underline hover:text-[var(--text-primary)]"
                  >
                    {lang === "en" ? "Clear" : "Hapus"}
                  </button>
                </div>
              )}
            </div>

            {/* Error / Fallback State */}
            {errorMsg && (
              <div className="rounded-xl border-[1.5px] border-l-4 border-l-amber-600 border-amber-300 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/30 p-4 text-xs">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-4 w-4 text-amber-700 dark:text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-amber-900 dark:text-amber-200">
                      {lang === "en" ? "System in Fallback Mode" : "Operasi Dalam Mode Fallback"}
                    </h4>
                    <p className="mt-1 text-stone-700 dark:text-stone-300 leading-relaxed">
                      {errorMsg}
                    </p>
                    <div className="mt-2.5 flex items-center gap-3">
                      <button
                        onClick={fetchEvents}
                        className="rounded-md bg-amber-200 dark:bg-amber-900/60 px-3 py-1 text-xs font-semibold text-amber-900 dark:text-amber-100 hover:bg-amber-300"
                      >
                        {t.refresh}
                      </button>
                      <span className="text-[11px] text-[var(--text-muted)] font-mono">
                        `make run-api`
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Event List / Grid */}
            {isLoading ? (
              <div className="space-y-4">
                {/* Lead Skeleton */}
                <div className="h-56 rounded-2xl border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 animate-pulse space-y-3">
                  <div className="h-3 w-32 bg-[var(--bg-subtle)] rounded" />
                  <div className="h-7 w-3/4 bg-[var(--bg-subtle)] rounded" />
                  <div className="h-4 w-full bg-[var(--bg-subtle)] rounded" />
                </div>
                {/* 2-Column Grid Skeletons */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="h-44 rounded-xl border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 animate-pulse space-y-3"
                    >
                      <div className="h-3 w-24 bg-[var(--bg-subtle)] rounded" />
                      <div className="h-5 w-4/5 bg-[var(--bg-subtle)] rounded" />
                      <div className="h-3 w-full bg-[var(--bg-subtle)] rounded" />
                    </div>
                  ))}
                </div>
              </div>
            ) : events.length > 0 ? (
              <div className="space-y-5">
                {/* On Page 1 without search filter, highlight top story as Lead Card */}
                {page === 1 && !searchQuery ? (
                  <>
                    <EventCard
                      key={events[0].id}
                      event={events[0]}
                      isLead={true}
                      lang={lang}
                    />
                    {events.length > 1 && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                        {events.slice(1).map((ev) => (
                          <EventCard key={ev.id} event={ev} lang={lang} />
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  /* Standard 2-column grid for paged / searched results */
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    {events.map((ev) => (
                      <EventCard key={ev.id} event={ev} lang={lang} />
                    ))}
                  </div>
                )}

                {/* NUMBERED PAGINATION CONTROLS (Item A2) */}
                <div className="mt-8 border-t-[1.5px] border-[var(--border-subtle)] pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                  {/* Results Count Text */}
                  <div className="text-xs text-[var(--text-secondary)] font-medium">
                    {t.showingRange
                      .replace("{start}", String(startItem))
                      .replace("{end}", String(endItem))
                      .replace("{total}", String(totalCount))}
                  </div>

                  {/* Pagination Buttons */}
                  <div className="flex items-center gap-1.5">
                    {/* Previous Button */}
                    <button
                      id="btn-prev-page"
                      onClick={() => handlePageChange(page - 1)}
                      disabled={page <= 1}
                      className="inline-flex items-center gap-1 rounded-lg border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-semibold text-[var(--text-primary)] hover:border-[var(--border-strong)] disabled:opacity-40 disabled:pointer-events-none transition-all shadow-xs"
                      title={t.prevPage}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      <span className="hidden sm:inline">{t.prevPage}</span>
                    </button>

                    {/* Numbered Page Buttons */}
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => {
                      const isActive = pageNum === page;
                      return (
                        <button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          className={`min-w-[34px] h-[34px] rounded-lg border-[1.5px] text-xs font-mono font-bold transition-all shadow-xs ${
                            isActive
                              ? "border-[var(--text-primary)] bg-[var(--text-primary)] text-[var(--bg-canvas)]"
                              : "border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]"
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}

                    {/* Next Button */}
                    <button
                      id="btn-next-page"
                      onClick={() => handlePageChange(page + 1)}
                      disabled={page >= totalPages}
                      className="inline-flex items-center gap-1 rounded-lg border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-semibold text-[var(--text-primary)] hover:border-[var(--border-strong)] disabled:opacity-40 disabled:pointer-events-none transition-all shadow-xs"
                      title={t.nextPage}
                    >
                      <span className="hidden sm:inline">{t.nextPage}</span>
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              /* Empty Results State */
              <div className="rounded-2xl border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] p-12 text-center text-xs space-y-3">
                <Layers className="h-9 w-9 mx-auto text-[var(--text-muted)]" />
                <h3 className="text-base font-serif font-black text-[var(--text-primary)]">
                  {t.emptyEvents}
                </h3>
                <p className="text-[var(--text-muted)] max-w-md mx-auto">
                  {t.emptyEventsSub}
                </p>
                <div className="pt-2">
                  <button
                    onClick={() => {
                      setSelectedCategory("all");
                      setSelectedLocation("");
                      setSearchQuery("");
                      setPage(1);
                      updateUrlParams(1, "all", "", "");
                    }}
                    className="inline-flex items-center gap-1.5 rounded-lg border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-3.5 py-1.5 text-xs font-semibold text-[var(--text-primary)] hover:border-[var(--border-strong)] transition-all shadow-xs"
                  >
                    {lang === "en" ? "Reset All Filters" : "Reset Semua Filter"}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT / SIDEBAR COLUMN (approx 32% width - 4 cols) */}
          <aside className="lg:col-span-4 space-y-6">
            {/* Situational Summary Desk (KPI Cards) */}
            <div className="rounded-2xl border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 sm:p-6 shadow-xs space-y-5">
              <div>
                <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-[var(--accent-primary)] font-bold">
                  <FileText className="h-3.5 w-3.5" />
                  <span>{t.summaryDesk}</span>
                </div>
                <h2 className="font-serif font-bold text-lg text-[var(--text-primary)] mt-1 tracking-tight">
                  {lang === "en" ? "Scope Intelligence" : "Pemantauan Agregat"}
                </h2>
                <p className="text-[11px] text-[var(--text-secondary)] mt-0.5 leading-relaxed">
                  {t.summaryDeskSubtitle}
                </p>
              </div>

              {/* 4 Aggregate Numbers (Calm editorial strip with 1px divider per DESIGN.md) */}
              <div className="grid grid-cols-2 divide-x divide-y divide-[var(--line)] border-t-[1.5px] border-b border-[var(--ink)] py-2">
                {/* Total Events */}
                <div className="p-3">
                  <div className="text-[11px] font-sans font-medium text-[var(--ink2)]">
                    {t.kpiTotal}
                  </div>
                  <div className="font-serif text-3xl font-semibold text-[var(--ink)] mt-1">
                    {summaryStats ? summaryStats.total : totalCount}
                  </div>
                  <div className="text-[10px] text-[var(--ink2)] mt-0.5">
                    {t.kpiTotalSub}
                  </div>
                </div>

                {/* Need to Know / Urgent */}
                <div className="p-3">
                  <div className="text-[11px] font-sans font-medium text-[var(--ink2)]">
                    {t.kpiNeedToKnow}
                  </div>
                  <div className={`font-serif text-3xl font-semibold mt-1 ${
                    (summaryStats?.need_to_know || 0) > 0 ? "text-[var(--warn)]" : "text-[var(--ink)]"
                  }`}>
                    {summaryStats ? summaryStats.need_to_know : 0}
                  </div>
                  <div className="text-[10px] text-[var(--ink2)] mt-0.5">
                    {t.kpiNeedToKnowSub}
                  </div>
                </div>

                {/* Official Primary */}
                <div className="p-3">
                  <div className="text-[11px] font-sans font-medium text-[var(--ink2)]">
                    {t.kpiOfficial}
                  </div>
                  <div className="font-serif text-3xl font-semibold text-[var(--ink)] mt-1">
                    {summaryStats ? summaryStats.official_primary : 0}
                  </div>
                  <div className="text-[10px] text-[var(--ink2)] mt-0.5">
                    {t.kpiOfficialSub}
                  </div>
                </div>

                {/* Conflicting Claims */}
                <div className="p-3">
                  <div className="text-[11px] font-sans font-medium text-[var(--ink2)]">
                    {t.kpiConflicts}
                  </div>
                  <div className={`font-serif text-3xl font-semibold mt-1 ${
                    (summaryStats?.conflicts || 0) > 0 ? "text-[var(--warn)]" : "text-[var(--ink)]"
                  }`}>
                    {summaryStats ? summaryStats.conflicts : 0}
                  </div>
                  <div className="text-[10px] text-[var(--ink2)] mt-0.5">
                    {t.kpiConflictsSub}
                  </div>
                </div>
              </div>
            </div>

            {/* Regional Spotlight Desk */}
            <div className="rounded-2xl border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 sm:p-6 shadow-xs space-y-3.5">
              <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-[var(--accent-primary)] font-bold">
                <MapPin className="h-3.5 w-3.5" />
                <span>{t.regionFilter}</span>
              </div>
              <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                {lang === "en"
                  ? "Select a region to focus situational coverage on localized urban reporting."
                  : "Pilih wilayah untuk memusatkan pemantauan pada peristiwa perkotaan setempat."}
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                {regionShortcuts.map((r) => {
                  const isSelected = selectedLocation === r.value;
                  return (
                    <button
                      key={r.value}
                      onClick={() => handleLocationChange(r.value)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold border-[1.5px] transition-all shadow-xs ${
                        isSelected
                          ? "border-[var(--text-primary)] bg-[var(--text-primary)] text-[var(--bg-canvas)] font-bold"
                          : "border-[var(--border-subtle)] bg-[var(--bg-canvas)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]"
                      }`}
                    >
                      {r.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Editorial Lineage & Integrity Disclosure */}
            <div className="rounded-2xl border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-subtle)]/40 p-5 text-xs space-y-2.5">
              <div className="flex items-center gap-2 font-bold text-[var(--text-primary)]">
                <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <span>{t.editorialMethodology}</span>
              </div>
              <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed font-sans">
                {t.editorialMethodologyText}
              </p>
              <div className="pt-1 border-t border-[var(--border-subtle)]/60 text-[10px] text-[var(--text-muted)] font-mono flex items-center justify-between">
                <span>DEC-0003 Strict Sourcing</span>
                <span>DEC-0006 Anti-Hallucination</span>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

export default function SituationalOverviewPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs font-mono text-[var(--text-muted)]">Loading Situational Overview...</div>}>
      <SituationalOverviewContent />
    </Suspense>
  );
}
