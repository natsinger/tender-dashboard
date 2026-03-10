/**
 * UnitCompositionCard component.
 *
 * Displays total housing units with a stacked bar and legend showing
 * the breakdown into named segments. Used for both lot-level splits
 * (FM / TP / unclassified) and tender-type splits.
 */
"use client";

import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CompositionSegment {
  label: string;
  value: number;
  /** Tailwind bg class for the bar segment and legend dot. */
  color: string;
}

interface UnitCompositionCardProps {
  /** Total value displayed as the headline number. */
  total: number;
  /** Ordered segments that compose the total. */
  segments: CompositionSegment[];
  /** Optional footnote below the legend. */
  footnote?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function UnitCompositionCard({
  total,
  segments,
  footnote,
}: UnitCompositionCardProps) {
  // Compute percentages — use remainder trick on last segment to avoid drift
  const withPct = segments
    .filter((s) => s.value > 0)
    .map((s, _i, arr) => {
      const pct = total > 0 ? Math.round((s.value / total) * 100) : 0;
      return { ...s, pct };
    });

  // Adjust last segment so percentages sum to exactly 100
  if (withPct.length > 0 && total > 0) {
    const sum = withPct.reduce((acc, s) => acc + s.pct, 0);
    withPct[withPct.length - 1].pct += 100 - sum;
  }

  const colsClass =
    withPct.length <= 2
      ? "grid-cols-2"
      : withPct.length === 3
        ? "grid-cols-3"
        : "grid-cols-2 sm:grid-cols-4";

  return (
    <div
      className={cn(
        "relative rounded-xl border border-megido-border bg-megido-bg-card p-5",
        "transition-shadow duration-200 hover:shadow-md",
      )}
    >
      {/* Blue right border accent */}
      <div className="absolute bottom-3 end-0 top-3 w-[3px] rounded-full bg-megido-primary" />

      {/* Header */}
      <p className="mb-1 text-xs font-medium text-megido-text-muted">
        {'\u05E1\u05D4"\u05DB \u05D9\u05D7"\u05D3'}
      </p>
      <span className="ltr-nums text-2xl font-bold text-megido-text-heading">
        {total.toLocaleString("he-IL")}
      </span>

      {/* Stacked bar */}
      {withPct.length > 0 && (
        <div className="mt-4 flex h-2 overflow-hidden rounded-full bg-neutral-100">
          {withPct.map((seg) => (
            <div
              key={seg.label}
              className={cn(seg.color, "transition-all duration-300")}
              style={{
                width: `${seg.pct}%`,
                minWidth: seg.pct > 0 ? "4px" : undefined,
              }}
            />
          ))}
        </div>
      )}

      {/* Legend */}
      {withPct.length > 0 && (
        <div className={cn("mt-3 grid gap-x-3 gap-y-2", colsClass)}>
          {withPct.map((seg) => (
            <div key={seg.label} className="flex items-start gap-1.5">
              <div
                className={cn(
                  "mt-1 h-2 w-2 shrink-0 rounded-full",
                  seg.color,
                )}
              />
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-megido-text-heading">
                  {seg.label}
                </p>
                <p className="ltr-nums text-xs text-megido-text-muted">
                  {seg.value.toLocaleString("he-IL")}{" "}
                  <span className="text-[0.64rem]">({seg.pct}%)</span>
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {total === 0 && (
        <p className="mt-3 text-xs text-megido-text-muted">
          {"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9\u05DD \u05D6\u05DE\u05D9\u05E0\u05D9\u05DD"}
        </p>
      )}

      {/* Footnote */}
      {footnote && (
        <p className="mt-3 text-[0.64rem] leading-relaxed text-megido-text-muted">
          {footnote}
        </p>
      )}
    </div>
  );
}
