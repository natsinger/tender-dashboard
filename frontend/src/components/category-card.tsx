/**
 * CategoryCard component.
 *
 * White card with a blue right border stripe showing a category name,
 * a large bold units count, and a smaller tender count text. Matches
 * the _CARD_HTML template from the Streamlit dashboard (ROW 4).
 */
"use client";

import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CategoryCardProps {
  /** Category label displayed as small muted text (e.g. "דיור להשכרה"). */
  label: string;
  /** Number of housing units — displayed large and bold. */
  units: number;
  /** Number of tenders — displayed as secondary text. */
  count: number;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CategoryCard({
  label,
  units,
  count,
  className,
}: CategoryCardProps) {
  return (
    <div
      dir="rtl"
      className={cn(
        "relative rounded-xl border border-megido-border bg-megido-bg-card p-4 shadow-sm",
        "transition-shadow duration-200 hover:shadow-md",
        "focus-visible:ring-2 focus-visible:ring-megido-primary focus-visible:ring-offset-2",
        className,
      )}
    >
      {/* Blue right border accent (3px) */}
      <div className="absolute bottom-3 end-0 top-3 w-[3px] rounded-full bg-megido-primary" />

      <p className="mb-1 text-xs font-medium text-megido-text-muted">{label}</p>

      <div className="flex items-baseline gap-2">
        <span className="ltr-nums text-xl font-bold text-megido-text-heading">
          {units.toLocaleString("he-IL")} {'\u05D9\u05D7"\u05D3'}
        </span>
        <span className="text-xs text-megido-text-muted">
          {count} {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD"}
        </span>
      </div>
    </div>
  );
}
