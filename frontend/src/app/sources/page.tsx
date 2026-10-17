"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ExternalLink,
  FileCheck,
  Lock,
  Newspaper,
  Scale,
  Users,
  CheckCircle2,
} from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { DataMode } from "@/lib/types";
import { Language, getTranslation } from "@/lib/i18n";

export default function SourceLineagePage() {
  const [dataMode, setDataMode] = useState<DataMode>("live");
  const [selectedLocation, setSelectedLocation] = useState<string>("");
  const [lang, setLang] = useState<Language>("id");

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

  const handleLanguageChange = (newLang: Language) => {
    setLang(newLang);
    if (typeof window !== "undefined") {
      localStorage.setItem("staymad_lang", newLang);
    }
  };

  const t = getTranslation(lang);

  // Trusted sources registry directly from docs/sources.md and DEC-0003
  const trustedSources = [
    {
      name: "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
      url: "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json",
      type: "API Publik",
      tier: "Tier 1",
      family: "GOV_BMKG",
      notes: "Domain publik / data terbuka pemerintah RI. Parameter cuaca & gempa permanen.",
      retention: "Parameter bencana dan metadata disimpan permanen.",
    },
    {
      name: "BPBD DKI Jakarta (Badan Penanggulangan Bencana Daerah)",
      url: "https://bpbd.jakarta.go.id/berita",
      type: "Resmi Pemerintah",
      tier: "Tier 1",
      family: "GOV_BPBD_DKI",
      notes: "Portal resmi Pemprov DKI Jakarta (UU KIP). Status siaga banjir dan keselamatan publik.",
      retention: "Status siaga dan wilayah terdampak. Teks penuh maksimal 30 hari.",
    },
    {
      name: "BNPB Indonesia (Badan Nasional Penanggulangan Bencana)",
      url: "https://bnpb.go.id/berita",
      type: "Resmi Pemerintah",
      tier: "Tier 1",
      family: "GOV_BNPB",
      notes: "Informasi resmi kebencanaan nasional. Hak cipta BNPB RI untuk kepentingan publik.",
      retention: "Nomor siaran pers, data korban/kerusakan, dan tautan resmi.",
    },
    {
      name: "Sekretariat Kabinet RI",
      url: "https://setkab.go.id/berita",
      type: "Resmi Pemerintah",
      tier: "Tier 1",
      family: "GOV_SETKAB",
      notes: "Publikasi resmi regulasi dan kebijakan presiden RI (UU KIP).",
      retention: "Nomor regulasi, ringkasan kebijakan, kutipan resmi, dan URL rilis.",
    },
    {
      name: "LKBN ANTARA",
      url: "https://www.antaranews.com/rss/terkini.xml",
      type: "RSS Feed",
      tier: "Tier 1",
      family: "LKBN_ANTARA",
      notes: "Kantor Berita Nasional BUMN. Penggunaan RSS publik untuk ringkasan wajar.",
      retention: "Klaim kutipan dan URL asli. Teks penuh dihapus setelah 7 hari.",
    },
    {
      name: "Kompas.com",
      url: "https://news.kompas.com/rss",
      type: "RSS Feed",
      tier: "Tier 1",
      family: "KOMPAS_GRAMEDIA",
      notes: "Lisensi KG Media. Feed publik berita umum dan nasional kompas.com.",
      retention: "Kutipan bukti klaim dan URL rujukan utama.",
    },
    {
      name: "CNN Indonesia",
      url: "https://www.cnnindonesia.com/nasional/rss",
      type: "RSS Feed",
      tier: "Tier 2",
      family: "TRANSMEDIA",
      notes: "Lisensi Transmedia / WarnerMedia. Satu grup redaksi dengan Detikcom.",
      retention: "Metadata klaim terverifikasi dan URL sumber asli.",
    },
    {
      name: "Detikcom",
      url: "https://news.detik.com/berita/rss",
      type: "RSS Feed",
      tier: "Tier 2",
      family: "TRANSMEDIA",
      notes: "Lisensi Transmedia. Sindikasi dengan CNN Indonesia dikelompokkan ke TRANSMEDIA.",
      retention: "Kutipan bukti klaim dan tautan permanen.",
    },
    {
      name: "Republika",
      url: "https://republika.co.id/rss",
      type: "RSS Feed",
      tier: "Tier 2",
      family: "MAHAKA_MEDIA",
      notes: "Lisensi Mahaka Media. Feed publik berita umum dan nasional.",
      retention: "Metadata, klaim, dan URL asli.",
    },
    {
      name: "Tempo.co",
      url: "https://rss.tempo.co/nasional",
      type: "RSS Feed",
      tier: "Tier 2",
      family: "TEMPO_INTI_MEDIA",
      notes: "Lisensi Tempo Inti Media. Dilarang scrape artikel penuh tanpa izin.",
      retention: "Metadata dan ringkasan klaim rujukan.",
    },
    {
      name: "CNBC Indonesia",
      url: "https://www.cnbcindonesia.com/news/rss",
      type: "RSS Feed",
      tier: "Tier 2",
      family: "TRANSMEDIA",
      notes: "Lisensi Transmedia / NBCUniversal. Berita ekonomi dan transportasi.",
      retention: "Metadata klaim dan tautan asli.",
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)] flex flex-col font-sans">
      <Navbar
        currentMode={dataMode}
        onModeChange={handleModeChange}
        selectedLocation={selectedLocation}
        onLocationChange={setSelectedLocation}
        lang={lang}
        onLangChange={handleLanguageChange}
      />

      <main className="flex-1 mx-auto max-w-[1120px] w-full px-4 sm:px-6 py-8 space-y-10">
        {/* Navigation Breadcrumb */}
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-xs font-medium text-[var(--ink2)] hover:text-[var(--ink)] transition-colors group"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
            <span className="font-semibold">{t.backToOverview}</span>
          </Link>
        </div>

        {/* Page Header - Editorial Layout per DESIGN.md §7 */}
        <header className="border-b-[1.5px] border-[var(--line)] pb-8 space-y-3">
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--accent)] font-semibold">
            <Scale className="h-4 w-4" />
            <span>STANDAR AKREDITASI REDAKSI (DEC-0003)</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-serif font-bold text-[var(--ink)] tracking-tight">
            {t.sourcesPageTitle}
          </h1>

          <p className="font-serif italic text-base text-[var(--ink2)]">
            {lang === "id"
              ? "Sourcing Policy & Data Lineage (Strict Sourcing Allowlist per DEC-0003)"
              : "Kebijakan Sumber & Provenance Data (Strict Sourcing Allowlist per DEC-0003)"}
          </p>

          <p className="text-sm font-serif text-[var(--ink)] max-w-3xl leading-relaxed pt-1">
            {t.sourcesPageSubtitle}
          </p>
        </header>

        {/* Core Principles Grid - Restrained Paper Cards */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Principle 1 */}
          <div className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-6 space-y-3 shadow-xs">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--line)] bg-[var(--tint)] text-[var(--accent)]">
                <Lock className="h-4 w-4" />
              </div>
              <h2 className="text-sm font-serif font-bold text-[var(--ink)]">
                {t.sourcesPrinciple1Title}
              </h2>
            </div>
            <p className="text-xs text-[var(--ink2)] leading-relaxed font-sans">
              {t.sourcesPrinciple1Desc}
            </p>
          </div>

          {/* Principle 2 */}
          <div className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-6 space-y-3 shadow-xs">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--line)] bg-[var(--tint)] text-[var(--warn)]">
                <Users className="h-4 w-4" />
              </div>
              <h2 className="text-sm font-serif font-bold text-[var(--ink)]">
                {t.sourcesPrinciple2Title}
              </h2>
            </div>
            <p className="text-xs text-[var(--ink2)] leading-relaxed font-sans">
              {t.sourcesPrinciple2Desc}
            </p>
          </div>

          {/* Principle 3 */}
          <div className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] p-6 space-y-3 shadow-xs">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--line)] bg-[var(--tint)] text-[var(--ink)]">
                <FileCheck className="h-4 w-4" />
              </div>
              <h2 className="text-sm font-serif font-bold text-[var(--ink)]">
                {t.sourcesPrinciple3Title}
              </h2>
            </div>
            <p className="text-xs text-[var(--ink2)] leading-relaxed font-sans">
              {t.sourcesPrinciple3Desc}
            </p>
          </div>
        </section>

        {/* Sources Registry Table - Clean Newspaper Directory Format */}
        <section className="rounded-2xl border-[1.5px] border-[var(--ink)] bg-[var(--surface)] overflow-hidden shadow-xs">
          <div className="border-b-[1.5px] border-[var(--ink)] p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--tint)]/40">
            <div>
              <h2 className="text-lg font-serif font-bold text-[var(--ink)] flex items-center gap-2.5">
                <Newspaper className="h-5 w-5 text-[var(--accent)]" />
                <span>{t.sourcesRegistryTitle}</span>
              </h2>
              <p className="text-xs text-[var(--ink2)] mt-1">
                {lang === "id"
                  ? `Total ${trustedSources.length} lembaga pemerintah dan organisasi media resmi yang terdaftar.`
                  : `Total ${trustedSources.length} government agencies and verified media organizations registered.`}
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-full border-[1.5px] border-[var(--accent)] bg-[var(--tint)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {t.sourcesVerifiedBadge}
            </span>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[var(--tint)] text-[var(--ink2)] uppercase font-mono text-[11px] tracking-wider border-b-[1.5px] border-[var(--line)]">
                <tr>
                  <th className="px-5 py-3.5">{t.sourcesColName}</th>
                  <th className="px-5 py-3.5">{t.sourcesColTier}</th>
                  <th className="px-5 py-3.5">{t.sourcesColFamily}</th>
                  <th className="px-5 py-3.5">{t.sourcesColType}</th>
                  <th className="px-5 py-3.5">{t.sourcesColPolicy}</th>
                  <th className="px-5 py-3.5 text-right">{t.sourcesColLink}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)] text-[var(--ink)] font-sans">
                {trustedSources.map((src, idx) => (
                  <tr key={idx} className="hover:bg-[var(--hover)] transition-colors">
                    <td className="px-5 py-4 font-medium">
                      <div className="font-serif text-[15px] font-semibold text-[var(--ink)] leading-snug">
                        {src.name}
                      </div>
                      <div className="text-[12px] text-[var(--ink2)] font-serif italic mt-0.5">
                        {src.notes}
                      </div>
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      <span
                        className={`inline-block rounded-md px-2 py-0.5 font-mono text-[11px] font-bold border-[1.5px] ${
                          src.tier === "Tier 1"
                            ? "bg-[var(--tint)] text-[var(--ink)] border-[var(--ink)]"
                            : "bg-[var(--tint)]/50 text-[var(--ink2)] border-[var(--line)]"
                        }`}
                      >
                        {src.tier}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-mono text-[12px] text-[var(--ink2)] whitespace-nowrap">
                      {src.family}
                    </td>
                    <td className="px-5 py-4 text-[12px] text-[var(--ink2)] whitespace-nowrap">
                      {src.type}
                    </td>
                    <td className="px-5 py-4 text-[12px] text-[var(--ink2)] max-w-xs">
                      <div className="line-clamp-2 leading-relaxed">{src.retention}</div>
                    </td>
                    <td className="px-5 py-4 text-right whitespace-nowrap">
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[var(--accent)] hover:text-[var(--ink)] font-mono text-[12px] font-semibold underline underline-offset-4 transition-colors"
                      >
                        {t.sourcesOpenLink}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
