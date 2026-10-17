import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Newsreader } from "next/font/google";
import "./globals.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-editorial-serif",
  display: "swap",
  style: ["normal", "italic"],
});

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-editorial-sans",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-editorial-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Stay Mad — Event Intelligence & Synthesis Platform",
  description:
    "Ruang redaksi intelijen peristiwa perkotaan berbasis sintesis bukti terverifikasi, transparansi pemrosesan AI, dan linimasa kronologis tanpa halusinasi.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="id"
      className={`${newsreader.variable} ${ibmPlexSans.variable} ${ibmPlexMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-[var(--bg)] text-[var(--ink)] antialiased transition-colors duration-200">
        <div className="min-h-screen flex flex-col">
          <main className="flex-1">{children}</main>

          <footer className="border-t-[1.5px] border-[var(--line)] bg-[var(--surface)] py-6 text-xs text-[var(--ink2)]">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="font-serif italic font-semibold text-[var(--ink)] tracking-wide">
                  Stay Mad
                </span>
                <span>·</span>
                <span>Platform Intelijen & Sintesis Berita Perkotaan</span>
              </div>
              <div className="flex items-center gap-3 text-[11px] text-[var(--ink2)]">
                <span>Waktu Resmi Asia/Jakarta (WIB)</span>
                <span>·</span>
                <span title="Kepatuhan Prinsip: DEC-0001 (Bahasa & Waktu WIB), DEC-0006 (Zero Fake Numbers), Master Spec §23-§29">
                  Kepatuhan Standar Otoritas (DEC-0001 / DEC-0006)
                </span>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
