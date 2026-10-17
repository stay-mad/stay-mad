import {
  ActionabilityLevel,
  ConfidenceBucket,
  EventCategory,
  EvidenceStatus,
  VerificationLevel,
} from "./types";
import { Language } from "./i18n";

/**
 * Format timestamp into WIB (Asia/Jakarta / UTC+7) display string.
 * Example output: "16 Okt 2026, 14:30 WIB"
 */
export function formatWibDateTime(
  dateInput: string | Date | null | undefined,
  lang: Language = "id"
): string {
  if (!dateInput) return lang === "en" ? "Time unavailable" : "Waktu belum tersedia";
  try {
    const d = typeof dateInput === "string" ? new Date(dateInput) : dateInput;
    if (isNaN(d.getTime())) return String(dateInput);

    const locale = lang === "en" ? "en-US" : "id-ID";
    const formatter = new Intl.DateTimeFormat(locale, {
      timeZone: "Asia/Jakarta",
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });

    return `${formatter.format(d)} WIB`;
  } catch {
    return String(dateInput);
  }
}

/**
 * Friendly label for EventCategory in Indonesian or English.
 */
export function getCategoryLabel(
  category: EventCategory | string,
  lang: Language = "id"
): string {
  switch (category) {
    case "disaster_and_weather":
      return lang === "en" ? "Disaster & Weather" : "Bencana & Cuaca";
    case "transportation_and_infrastructure":
      return lang === "en" ? "Transportation & Infrastructure" : "Transportasi & Infrastruktur";
    case "government_and_public_policy":
      return lang === "en" ? "Public Policy" : "Kebijakan Publik";
    default:
      return category;
  }
}

/**
 * Editorial styling for EventCategory.
 */
export function getCategoryStyle(category: EventCategory | string) {
  switch (category) {
    case "disaster_and_weather":
      return {
        bg: "bg-amber-50 dark:bg-amber-950/40",
        text: "text-amber-800 dark:text-amber-300",
        border: "border-amber-200 dark:border-amber-900/60",
        dot: "bg-amber-600 dark:bg-amber-400",
      };
    case "transportation_and_infrastructure":
      return {
        bg: "bg-sky-50 dark:bg-sky-950/40",
        text: "text-sky-800 dark:text-sky-300",
        border: "border-sky-200 dark:border-sky-900/60",
        dot: "bg-sky-600 dark:bg-sky-400",
      };
    case "government_and_public_policy":
      return {
        bg: "bg-emerald-50 dark:bg-emerald-950/40",
        text: "text-emerald-800 dark:text-emerald-300",
        border: "border-emerald-200 dark:border-emerald-900/60",
        dot: "bg-emerald-600 dark:bg-emerald-400",
      };
    default:
      return {
        bg: "bg-stone-100 dark:bg-stone-800",
        text: "text-stone-700 dark:text-stone-300",
        border: "border-stone-200 dark:border-stone-700",
        dot: "bg-stone-500",
      };
  }
}

/**
 * Editorial Urgency & Impact badge mapper.
 */
export function getUrgencyBadge(
  urgencyScore: number,
  importanceScore?: number,
  lang: Language = "id"
) {
  const imp = importanceScore ?? 0;
  if (urgencyScore >= 0.8 || imp >= 0.8) {
    return {
      label: lang === "en" ? "NEED TO KNOW" : "PERLU DIKETAHUI",
      bg: "bg-red-50 dark:bg-red-950/50",
      text: "text-red-700 dark:text-red-300 font-semibold",
      border: "border-red-200 dark:border-red-900",
      pulse: true,
    };
  }
  if (urgencyScore >= 0.6 || imp >= 0.6) {
    return {
      label: lang === "en" ? "HIGH IMPACT" : "DAMPAK TINGGI",
      bg: "bg-amber-50 dark:bg-amber-950/50",
      text: "text-amber-800 dark:text-amber-300 font-medium",
      border: "border-amber-200 dark:border-amber-900",
      pulse: false,
    };
  }
  if (urgencyScore >= 0.4) {
    return {
      label: lang === "en" ? "DEVELOPING" : "BERKEMBANG",
      bg: "bg-stone-100 dark:bg-stone-800",
      text: "text-stone-700 dark:text-stone-300 font-medium",
      border: "border-stone-200 dark:border-stone-700",
      pulse: false,
    };
  }
  return {
    label: lang === "en" ? "INFORMATIONAL" : "INFORMASIONAL",
    bg: "bg-stone-100/70 dark:bg-stone-850",
    text: "text-stone-600 dark:text-stone-400 font-normal",
    border: "border-stone-200 dark:border-stone-800",
    pulse: false,
  };
}

/**
 * Editorial Verification level badge mapper.
 */
export function getVerificationBadge(
  level: VerificationLevel | string,
  lang: Language = "id"
) {
  switch (level) {
    case "OFFICIAL_PRIMARY":
      return {
        label: lang === "en" ? "Official Primary" : "Otoritas Resmi (Primer)",
        bg: "bg-emerald-50 dark:bg-emerald-950/40",
        text: "text-emerald-800 dark:text-emerald-300",
        border: "border-emerald-200 dark:border-emerald-900/60",
      };
    case "INDEPENDENTLY_CORROBORATED":
      return {
        label: lang === "en" ? "Independently Corroborated" : "Terkonfirmasi Independen",
        bg: "bg-stone-100 dark:bg-stone-800",
        text: "text-stone-800 dark:text-stone-200",
        border: "border-stone-300 dark:border-stone-700",
      };
    case "SINGLE_SOURCE":
    default:
      return {
        label: lang === "en" ? "Single Source Report" : "Laporan Sumber Tunggal",
        bg: "bg-stone-50 dark:bg-stone-900",
        text: "text-stone-600 dark:text-stone-400",
        border: "border-stone-200 dark:border-stone-800",
      };
  }
}

/**
 * Editorial Confidence bucket badge mapper.
 */
export function getConfidenceBadge(
  bucket: ConfidenceBucket | string,
  score?: number,
  lang: Language = "id"
) {
  const scoreSuffix = score !== undefined ? ` ${Math.round(score * 100)}%` : "";
  switch (bucket) {
    case "HIGH":
      return {
        label: lang === "en" ? `High Confidence${scoreSuffix}` : `Keyakinan Tinggi${scoreSuffix}`,
        bg: "bg-emerald-50 dark:bg-emerald-950/40",
        text: "text-emerald-800 dark:text-emerald-300",
        border: "border-emerald-200 dark:border-emerald-900/60",
      };
    case "MEDIUM":
      return {
        label: lang === "en" ? `Medium Confidence${scoreSuffix}` : `Keyakinan Sedang${scoreSuffix}`,
        bg: "bg-amber-50 dark:bg-amber-950/40",
        text: "text-amber-800 dark:text-amber-300",
        border: "border-amber-200 dark:border-amber-900/60",
      };
    case "LOW":
    default:
      return {
        label: lang === "en" ? `Low Confidence${scoreSuffix}` : `Keyakinan Rendah${scoreSuffix}`,
        bg: "bg-stone-100 dark:bg-stone-850",
        text: "text-stone-600 dark:text-stone-400",
        border: "border-stone-200 dark:border-stone-700",
      };
  }
}

/**
 * Editorial Evidence status badge mapper.
 */
export function getEvidenceStatusBadge(
  status: EvidenceStatus | string,
  lang: Language = "id"
) {
  switch (status) {
    case "SUPPORTED":
      return {
        label: lang === "en" ? "Supported by Evidence" : "Didukung Bukti Terverifikasi",
        bg: "bg-emerald-50 dark:bg-emerald-950/40",
        text: "text-emerald-800 dark:text-emerald-300",
        border: "border-emerald-200 dark:border-emerald-900/60",
      };
    case "CONFLICTING":
      return {
        label: lang === "en" ? "Claim Conflict Detected" : "Perbedaan Klaim / Angka Terdeteksi",
        bg: "bg-amber-50 dark:bg-amber-950/40",
        text: "text-amber-800 dark:text-amber-300",
        border: "border-amber-200 dark:border-amber-900/60",
      };
    case "RETRACTED":
      return {
        label: lang === "en" ? "Retracted by Publisher" : "Diralat / Dicabut Penerbit",
        bg: "bg-red-50 dark:bg-red-950/40",
        text: "text-red-800 dark:text-red-300",
        border: "border-red-200 dark:border-red-900/60",
      };
    case "INSUFFICIENT":
    default:
      return {
        label: lang === "en" ? "Insufficient Evidence" : "Bukti Belum Lengkap",
        bg: "bg-stone-100 dark:bg-stone-800",
        text: "text-stone-600 dark:text-stone-400",
        border: "border-stone-200 dark:border-stone-700",
      };
  }
}

/**
 * Actionability level badge mapper.
 */
export function getActionabilityBadge(
  level: ActionabilityLevel | string,
  lang: Language = "id"
) {
  switch (level) {
    case "ACTION_REQUIRED":
      return {
        isUrgent: true,
        label: lang === "en" ? "Immediate Action Required" : "Tindakan Darurat Wajib",
        bg: "bg-red-50 dark:bg-red-950/60",
        text: "text-red-800 dark:text-red-200 font-bold",
        border: "border-red-300 dark:border-red-800",
      };
    case "ACTION_RECOMMENDED":
      return {
        isUrgent: true,
        label: lang === "en" ? "Action Recommended" : "Tindakan Disarankan",
        bg: "bg-amber-50 dark:bg-amber-950/50",
        text: "text-amber-800 dark:text-amber-200 font-semibold",
        border: "border-amber-300 dark:border-amber-800",
      };
    case "OPTIONAL":
      return {
        isUrgent: false,
        label: lang === "en" ? "Optional Action" : "Tindakan Opsional",
        bg: "bg-stone-100 dark:bg-stone-800",
        text: "text-stone-700 dark:text-stone-300",
        border: "border-stone-200 dark:border-stone-700",
      };
    case "INFORMATIONAL":
      return {
        isUrgent: false,
        label: lang === "en" ? "Informational Only" : "Hanya Informasi",
        bg: "bg-stone-100 dark:bg-stone-800",
        text: "text-stone-700 dark:text-stone-300",
        border: "border-stone-200 dark:border-stone-700",
      };
    case "NO_IMMEDIATE_ACTION":
    default:
      return {
        isUrgent: false,
        label: lang === "en" ? "No Action Required" : "Tidak Perlu Tindakan",
        bg: "bg-stone-50 dark:bg-stone-900",
        text: "text-stone-600 dark:text-stone-400",
        border: "border-stone-200 dark:border-stone-800",
      };
  }
}
