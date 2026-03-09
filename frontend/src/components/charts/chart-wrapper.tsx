/**
 * ChartWrapper component.
 *
 * Wraps Recharts charts in a ResponsiveContainer with MEGIDO palette
 * defaults, RTL text direction for labels, and consistent padding.
 * All chart components should use this as their outer container.
 */
"use client";

import { cn } from "@/lib/utils";
import { ResponsiveContainer } from "recharts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChartWrapperProps {
  /** Chart title displayed above the chart area. */
  title?: string;
  /** Chart height in pixels. Defaults to 300. */
  height?: number;
  /** Chart width. Defaults to "100%". */
  width?: number | `${number}%`;
  /** Accessible label describing the chart content. */
  ariaLabel?: string;
  /** Additional CSS classes on the outer wrapper div. */
  className?: string;
  /** The Recharts chart element to render inside the container. */
  children: React.ReactNode;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ChartWrapper({
  title,
  height = 300,
  width = "100%" as const,
  ariaLabel,
  className,
  children,
}: ChartWrapperProps) {
  return (
    <div
      dir="rtl"
      role="img"
      aria-label={ariaLabel ?? title ?? "תרשים"}
      className={cn("w-full", className)}
    >
      {title && (
        <p className="mb-2 text-sm font-medium text-megido-text-muted">{title}</p>
      )}
      {/* Force LTR on the chart container — Recharts ResponsiveContainer
          calculates width incorrectly inside dir="rtl" parents. */}
      <div dir="ltr">
        <ResponsiveContainer width={width} height={height}>
          {children}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
