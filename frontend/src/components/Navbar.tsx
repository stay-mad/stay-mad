"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertTriangle,
  Clock,
  Database,
  MapPin,
  Search,
} from "lucide-react";
import { DataMode } from "@/lib/types";
import { api } from "@/lib/api";
import { Language, getTranslation } from "@/lib/i18n";

interface NavbarProps {
  currentMode: DataMode;
  onModeChange: (mode: DataMode) => void;
  selectedLocation: string;
  onLocationChange: (loc: string) => void;
  lang?: Language;
  onLangChange?: (lang: Language) => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

export function Navbar({
  currentMode,
  onModeChange,
  selectedLocation,
  onLocationChange,
  lang = "id",
  onLangChange,
  searchQuery,
  onSearchChange,
}: NavbarProps) {
  const [wibTime, setWibTime] = useState<string>("");
  const [dateDisplay, setDateDisplay] = useState<string>("");
  const [systemHealth, setSystemHealth] = useState<"ok" | "degraded" | "error" | "loading">("loading");
  const pathname = usePathname();
  const t = getTranslation(lang);

  // Realtime WIB Clock & Editorial Date (DEC-0001: Asia/Jakarta timezone)
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const timeFormatted = new Intl.DateTimeFormat(lang === "en" ? "en-US" : "id-ID", {
        timeZone: "Asia/Jakarta",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }).format(now);
      setWibTime(`${timeFormatted} WIB`);

      const dateFormatted = new Intl.DateTimeFormat(lang === "en" ? "en-US" : "id-ID", {
        timeZone: "Asia/Jakarta",
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      }).format(now);
      setDateDisplay(dateFormatted);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [lang]);

  // System Health Check
  useEffect(() => {
    let mounted = true;
    api
      .getHealth()
      .then((res) => {
        if (mounted) setSystemHealth(res.status);
      })
      .catch(() => {
        if (mounted) setSystemHealth("degraded");
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <header className="sticky top-0 z-40 bg-[var(--bg-surface)]/98 backdrop-blur-md transition-colors duration-200 border-b-[1.5px] border-[var(--border-subtle)] shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
      {/* TIER 1: Editorial Masthead & Main Navigation */}
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 border-b border-[var(--border-subtle)]/70">
        {/* Brand Masthead */}
        <div className="flex items-center gap-6 sm:gap-8">
          <Link href="/" className="group flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--text-primary)] text-[var(--bg-canvas)] font-serif font-black text-base tracking-tighter shadow-sm transition-transform group-hover:scale-105">
              SM
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif font-black tracking-tight text-[var(--text-primary)] text-xl sm:text-2xl leading-none">
                  STAY MAD
                </span>
                <span className="rounded-md bg-[var(--bg-subtle)] px-1.5 py-0.5 text-[10px] font-mono font-semibold text-[var(--text-muted)] border border-[var(--border-subtle)]">
                  v0.1
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <p className="text-[11px] text-[var(--text-muted)] hidden sm:block font-sans">
                  {t.brandSubtitle}
                </p>
                {dateDisplay && (
                  <>
                    <span className="hidden sm:inline text-[var(--border-subtle)]">·</span>
                    <span className="hidden lg:inline text-[11px] font-mono text-[var(--text-secondary)]">
                      {dateDisplay}
                    </span>
                  </>
                )}
              </div>
            </div>
          </Link>

          {/* Primary Nav Links (Single Clean Bilingual Label) */}
          <nav className="hidden md:flex items-center gap-1 border-l-[1.5px] border-[var(--border-subtle)] pl-6">
            <Link
              href="/"
              className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold tracking-wide transition-all ${
                pathname === "/"
                  ? "text-[var(--text-primary)] bg-[var(--bg-subtle)] shadow-xs"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]/60"
              }`}
            >
              {lang === "en" ? "Overview" : "Ikhtisar"}
            </Link>
            <Link
              href="/sources"
              className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold tracking-wide transition-all ${
                pathname === "/sources"
                  ? "text-[var(--text-primary)] bg-[var(--bg-subtle)] shadow-xs"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]/60"
              }`}
            >
              {lang === "en" ? "Sources & Policy" : "Sumber & Kebijakan"}
            </Link>
          </nav>
        </div>

        {/* Global Mode & Language Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Language Toggle (ID / EN) */}
          {onLangChange && (
            <div className="flex items-center rounded-lg border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-canvas)] p-0.5 text-[11px] font-mono">
              <button
                id="btn-lang-id"
                type="button"
                onClick={() => onLangChange("id")}
                className={`rounded-md px-2.5 py-1 transition-all ${
                  lang === "id"
                    ? "bg-[var(--bg-surface)] text-[var(--text-primary)] font-bold shadow-xs"
                    : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                }`}
                title="Bahasa Indonesia"
              >
                ID
              </button>
              <span className="text-[var(--border-subtle)] px-0.5">|</span>
              <button
                id="btn-lang-en"
                type="button"
                onClick={() => onLangChange("en")}
                className={`rounded-md px-2.5 py-1 transition-all ${
                  lang === "en"
                    ? "bg-[var(--bg-surface)] text-[var(--text-primary)] font-bold shadow-xs"
                    : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                }`}
                title="English Language"
              >
                EN
              </button>
            </div>
          )}

          {/* Data Mode Segmented Control */}
          <div className="flex items-center rounded-lg border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-canvas)] p-0.5 text-xs">
            <button
              id="btn-mode-live"
              onClick={() => onModeChange("live")}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 transition-all ${
                currentMode === "live"
                  ? "bg-[var(--bg-surface)] text-emerald-700 dark:text-emerald-400 font-bold shadow-xs"
                  : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              }`}
              title="Mode Data Aktual dari feed berita terverifikasi"
            >
              <span className="h-2 w-2 rounded-full bg-emerald-600 dark:bg-emerald-400 animate-pulse" />
              <span className="font-mono text-[11px] tracking-wide">LIVE</span>
            </button>
            <button
              id="btn-mode-demo"
              onClick={() => onModeChange("demo")}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 transition-all ${
                currentMode === "demo"
                  ? "bg-[var(--bg-surface)] text-stone-900 dark:text-stone-100 font-bold shadow-xs"
                  : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              }`}
              title="Mode Data Demo (23 Seed Articles)"
            >
              <Database className="h-3 w-3" />
              <span className="font-mono text-[11px] tracking-wide">DEMO</span>
            </button>
            <button
              id="btn-mode-fallback"
              onClick={() => onModeChange("degraded")}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 transition-all ${
                currentMode === "degraded"
                  ? "bg-[var(--bg-surface)] text-amber-800 dark:text-amber-400 font-bold shadow-xs"
                  : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              }`}
              title="Mode Degraded (Simulasi fallback)"
            >
              <AlertTriangle className="h-3 w-3" />
              <span className="font-mono text-[11px] tracking-wide">FALLBACK</span>
            </button>
          </div>
        </div>
      </div>

      {/* TIER 2: Editorial Utility & Live Status Strip */}
      <div className="bg-[var(--bg-subtle)]/40 px-4 py-2 sm:px-6">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-y-2 gap-x-4 text-xs">
          {/* Left: Region Select & Real-time Live Metrics */}
          <div className="flex items-center gap-2 overflow-x-auto py-0.5 max-w-full scrollbar-none">
            {/* Region Dropdown Selector */}
            <div className="flex items-center gap-1.5 rounded-lg border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2.5 py-1 shadow-xs">
              <MapPin className="h-3.5 w-3.5 text-[var(--accent-primary)] shrink-0" />
              <select
                id="select-region"
                value={selectedLocation}
                onChange={(e) => onLocationChange(e.target.value)}
                className="bg-transparent text-[var(--text-primary)] font-semibold focus:outline-none cursor-pointer text-xs pr-1"
              >
                <option value="" className="bg-[var(--bg-surface)] text-[var(--text-primary)]">
                  {t.allRegions} (Nasional)
                </option>
                <option value="DKI Jakarta" className="bg-[var(--bg-surface)] text-[var(--text-primary)]">
                  DKI Jakarta (Provinsi)
                </option>
                <option value="Jakarta Timur" className="bg-[var(--bg-surface)] text-[var(--text-primary)]">
                  Jakarta Timur (Kota)
                </option>
                <option value="DI Yogyakarta" className="bg-[var(--bg-surface)] text-[var(--text-primary)]">
                  DI Yogyakarta
                </option>
              </select>
            </div>

            {/* WIB Clock (White-space nowrap to prevent wrap jitter) */}
            <div className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2.5 py-1 font-mono text-[11px] text-[var(--text-secondary)] whitespace-nowrap shadow-xs">
              <Clock className="h-3 w-3 text-[var(--text-muted)] shrink-0" />
              <span className="whitespace-nowrap font-medium">{wibTime || "Memuat WIB..."}</span>
            </div>

            {/* Backend API Status (White-space nowrap) */}
            <div
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-mono border whitespace-nowrap shadow-xs ${
                systemHealth === "ok"
                  ? "border-emerald-200 dark:border-emerald-900/60 text-emerald-800 dark:text-emerald-300 bg-emerald-50/60 dark:bg-emerald-950/20"
                  : "border-amber-200 dark:border-amber-900/60 text-amber-800 dark:text-amber-300 bg-amber-50/60 dark:bg-amber-950/20"
              }`}
              title="Status koneksi REST API port 8080"
            >
              <span
                className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                  systemHealth === "ok" ? "bg-emerald-600 dark:bg-emerald-400" : "bg-amber-600 dark:bg-amber-400"
                }`}
              />
              <span className="whitespace-nowrap font-medium">
                {systemHealth === "ok" ? "API 8080 · OK" : "API Fallback"}
              </span>
            </div>
          </div>

          {/* Right: Quick Search Input (if provided) */}
          {onSearchChange !== undefined && (
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--text-muted)] pointer-events-none" />
              <input
                id="navbar-search-input"
                type="text"
                value={searchQuery ?? ""}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder={t.searchPlaceholder}
                className="w-full rounded-lg border-[1.5px] border-[var(--border-subtle)] bg-[var(--bg-surface)] pl-8 pr-3 py-1 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none shadow-xs transition-colors"
              />
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
