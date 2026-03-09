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
  /** Optional subtitle shown below the value (e.g. scope context). */
  subtitle?: string;
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
  neutral: { text: "text-megido-text-muted", Icon: Minus },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MetricCard({
  label,
  value,
  subtitle,
  delta,
  deltaDirection,
  className,
}: MetricCardProps) {
  const direction = detectDirection(delta, deltaDirection);
  const { text: deltaColor, Icon: DeltaIcon } = DELTA_STYLES[direction];

  return (
    <div
      className={cn(
        "relative rounded-xl border border-megido-border bg-megido-bg-card p-4",
        "transition-shadow duration-200 hover:shadow-md",
        "focus-visible:ring-2 focus-visible:ring-megido-primary focus-visible:ring-offset-2",
        className,
      )}
    >
      {/* Blue right border accent (3px) */}
      <div className="absolute bottom-3 end-0 top-3 w-[3px] rounded-full bg-megido-primary" />

      <p className="mb-1 text-xs font-medium text-megido-text-muted">{label}</p>

      <div className="flex items-baseline gap-2">
        <span className="ltr-nums text-2xl font-bold text-megido-text-heading">{value}</span>

        {delta != null && (
          <span className={cn("flex items-center gap-0.5 text-sm font-medium", deltaColor)}>
            <DeltaIcon className="h-3.5 w-3.5" />
            {delta}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="mt-1 text-[0.64rem] text-megido-text-muted">{subtitle}</p>
      )}
    </div>
  );
}
