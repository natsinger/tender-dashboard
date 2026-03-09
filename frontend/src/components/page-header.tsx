/**
 * PageHeader component.
 *
 * RTL flexbox header with the title on the right and the current date
 * (formatted in Hebrew locale) on the left. Matches the Streamlit
 * compact header style from the MEGIDO dashboard.
 */
"use client";

import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PageHeaderProps {
  /** Main page title (displayed large & bold). */
  title: string;
  /** Optional subtitle below the title. */
  subtitle?: string;
  /** Override the displayed date. Defaults to today. */
  date?: Date;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format a Date as "dd/MM/yyyy" using the Hebrew locale.
 * Falls back to basic formatting if Intl is unavailable.
 */
function formatHebrewDate(date: Date): string {
  try {
    return new Intl.DateTimeFormat("he-IL", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(date);
  } catch {
    const d = String(date.getDate()).padStart(2, "0");
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const y = date.getFullYear();
    return `${d}/${m}/${y}`;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PageHeader({
  title,
  subtitle,
  date,
  className,
}: PageHeaderProps) {
  const displayDate = date ?? new Date();

  return (
    <div
      dir="rtl"
      className={cn(
        "flex items-center justify-between gap-3 py-2",
        className,
      )}
    >
      {/* Title side (right in RTL) */}
      <div>
        <h1 className="text-xl font-bold text-megido-text-heading">{title}</h1>
        {subtitle && (
          <p className="mt-0.5 text-sm text-megido-text-muted">{subtitle}</p>
        )}
      </div>

      {/* Date side (left in RTL) */}
      <span className="shrink-0 text-sm text-megido-text-muted">
        {formatHebrewDate(displayDate)}
      </span>
    </div>
  );
}
