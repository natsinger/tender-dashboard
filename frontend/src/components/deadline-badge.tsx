/**
 * DeadlineBadge component.
 *
 * Displays a color-coded badge indicating how many days remain until
 * a tender's deadline closes. Color logic matches the Python _urgency()
 * helper from management.py.
 */
"use client";

import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DeadlineBadgeProps {
  /** Number of calendar days remaining until the deadline. */
  daysRemaining: number | null | undefined;
  /** Show only the colored dot (no text). Useful for tight table columns. */
  compact?: boolean;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Color mapping
// ---------------------------------------------------------------------------

interface BadgeStyle {
  bg: string;
  text: string;
  border: string;
  emoji: string;
}

function getBadgeStyle(days: number | null | undefined): BadgeStyle {
  if (days == null || Number.isNaN(days)) {
    return {
      bg: "bg-slate-100",
      text: "text-slate-500",
      border: "border-slate-200",
      emoji: "\u26AA",
    };
  }
  if (days <= 7) {
    return {
      bg: "bg-red-50",
      text: "text-red-700",
      border: "border-red-200",
      emoji: "\uD83D\uDD34",
    };
  }
  if (days <= 14) {
    return {
      bg: "bg-amber-50",
      text: "text-amber-700",
      border: "border-amber-200",
      emoji: "\uD83D\uDFE1",
    };
  }
  return {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    emoji: "\uD83D\uDFE2",
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DeadlineBadge({
  daysRemaining,
  compact = false,
  className,
}: DeadlineBadgeProps) {
  const style = getBadgeStyle(daysRemaining);

  if (compact) {
    const title =
      daysRemaining != null && !Number.isNaN(daysRemaining)
        ? `${daysRemaining} \u05D9\u05DE\u05D9\u05DD`
        : "";
    return (
      <span
        className={cn("inline-block h-2.5 w-2.5 shrink-0 rounded-full", style.bg, style.border, "border", className)}
        title={title}
      />
    );
  }

  const label =
    daysRemaining != null && !Number.isNaN(daysRemaining)
      ? `${style.emoji} ${daysRemaining} \u05D9\u05DE\u05D9\u05DD`
      : "\u2014";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        style.bg,
        style.text,
        style.border,
        className,
      )}
    >
      {label}
    </span>
  );
}
