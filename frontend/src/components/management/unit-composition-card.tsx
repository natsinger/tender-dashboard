/**
 * UnitCompositionCard component.
 *
 * Displays total housing units with a stacked bar showing the breakdown
 * into free market, target price, and unclassified (no lot-level data).
 * Makes the part-whole relationship explicit so viewers understand why
 * FM + TP may not equal the total.
 */
"use client";

import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface UnitCompositionCardProps {
  totalUnits: number;
  freeMarket: number;
  targetPrice: number;
  /** Number of tenders that have lot-level breakdown data. */
  tendersWithData: number;
  /** Total number of tenders in the filtered set. */
  tendersTotal: number;
}

// ---------------------------------------------------------------------------
// Segment config
// ---------------------------------------------------------------------------

interface Segment {
  label: string;
  value: number;
  pct: number;
  color: string;
  dotClass: string;
}

function buildSegments(
  total: number,
  fm: number,
  tp: number,
): Segment[] {
  if (total <= 0) return [];

  const unclassified = total - fm - tp;
  const fmPct = Math.round((fm / total) * 100);
  const tpPct = Math.round((tp / total) * 100);
  const unclPct = 100 - fmPct - tpPct;

  const segments: Segment[] = [];

  if (fm > 0) {
    segments.push({
      label: "\u05E9\u05D5\u05E7 \u05D7\u05D5\u05E4\u05E9\u05D9",
      value: fm,
      pct: fmPct,
      color: "bg-megido-primary",
      dotClass: "bg-megido-primary",
    });
  }

  if (tp > 0) {
    segments.push({
      label: "\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4",
      value: tp,
      pct: tpPct,
      color: "bg-emerald-500",
      dotClass: "bg-emerald-500",
    });
  }

  if (unclassified > 0) {
    segments.push({
      label: "\u05DC\u05DC\u05D0 \u05E4\u05D9\u05E8\u05D5\u05D8",
      value: unclassified,
      pct: unclPct,
      color: "bg-neutral-300",
      dotClass: "bg-neutral-300",
    });
  }

  return segments;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function UnitCompositionCard({
  totalUnits,
  freeMarket,
  targetPrice,
  tendersWithData,
  tendersTotal,
}: UnitCompositionCardProps) {
  const segments = buildSegments(totalUnits, freeMarket, targetPrice);

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
        {totalUnits.toLocaleString("he-IL")}
      </span>

      {/* Stacked bar */}
      {segments.length > 0 && (
        <div className="mt-4 flex h-2 overflow-hidden rounded-full bg-neutral-100">
          {segments.map((seg) => (
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
      {segments.length > 0 && (
        <div className="mt-3 grid grid-cols-3 gap-2">
          {segments.map((seg) => (
            <div key={seg.label} className="flex items-start gap-1.5">
              <div
                className={cn(
                  "mt-1 h-2 w-2 shrink-0 rounded-full",
                  seg.dotClass,
                )}
              />
              <div>
                <p className="text-xs font-medium text-megido-text-heading">
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
      {totalUnits === 0 && (
        <p className="mt-3 text-xs text-megido-text-muted">
          {"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9 \u05DE\u05D2\u05E8\u05E9\u05D9\u05DD \u05D6\u05DE\u05D9\u05E0\u05D9\u05DD"}
        </p>
      )}

      {/* Footnote */}
      {tendersTotal > 0 && (
        <p className="mt-3 text-[0.64rem] text-megido-text-muted">
          {"\u05DE\u05D1\u05D5\u05E1\u05E1 \u05E2\u05DC "}
          <span className="ltr-nums font-medium">{tendersWithData}</span>
          {" \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E2\u05DD \u05E0\u05EA\u05D5\u05E0\u05D9 \u05DE\u05D2\u05E8\u05E9\u05D9\u05DD \u05DE\u05EA\u05D5\u05DA "}
          <span className="ltr-nums font-medium">{tendersTotal}</span>
        </p>
      )}
    </div>
  );
}
