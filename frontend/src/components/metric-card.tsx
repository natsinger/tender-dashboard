/**
 * MetricCard component.
 *
 * Displays a single KPI metric with a blue right border accent,
 * a muted label, a large bold value, and an optional delta indicator.
 * Matches the Streamlit st.metric visual style from the MEGIDO dashboard.
 */
"use client";

import { cn } from "@/lib/utils";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MetricCardProps {
  /** Small muted label above the value (Hebrew). */
  label: string;
  /** Large bold value text. */
  value: string | number;
  /** Optional delta string (e.g. "+12" or "-5"). Determines icon & color. */
  delta?: string | number | null;
  /** Override delta direction. Auto-detected from delta sign by default. */
  deltaDirection?: "up" | "down" | "neutral";
  /** Additional CSS classes on the outer container. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function detectDirection(
  delta: string | number | null | undefined,
  override?: "up" | "down" | "neutral",
): "up" | "down" | "neutral" {
  if (override) return override;
  if (delta == null) return "neutral";

  const num = typeof delta === "number" ? delta : parseFloat(String(delta));
  if (Number.isNaN(num) || num === 0) return "neutral";
  return num > 0 ? "up" : "down";
}

const DELTA_STYLES: Record<
  "up" | "down" | "neutral",
  { text: string; Icon: React.ElementType }
> = {
  up: { text: "text-emerald-600", Icon: TrendingUp },
  down: { text: "text-red-500", Icon: TrendingDown },
  neutral: { text: "text-slate-400", Icon: Minus },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MetricCard({
  label,
  value,
  delta,
  deltaDirection,
  className,
}: MetricCardProps) {
  const direction = detectDirection(delta, deltaDirection);
  const { text: deltaColor, Icon: DeltaIcon } = DELTA_STYLES[direction];

  return (
    <div
      className={cn(
        "relative rounded-xl border border-slate-200 bg-white p-4",
        "transition-shadow duration-200 hover:shadow-md",
        className,
      )}
    >
      {/* Blue right border accent (3px) */}
      <div className="absolute bottom-3 right-0 top-3 w-[3px] rounded-full bg-[#2563EB]" />

      <p className="mb-1 text-xs font-medium text-slate-500">{label}</p>

      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-slate-900">{value}</span>

        {delta != null && (
          <span className={cn("flex items-center gap-0.5 text-sm font-medium", deltaColor)}>
            <DeltaIcon className="h-3.5 w-3.5" />
            {delta}
          </span>
        )}
      </div>
    </div>
  );
}
