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
  className,
  children,
}: ChartWrapperProps) {
  return (
    <div dir="rtl" className={cn("w-full", className)}>
      {title && (
        <p className="mb-2 text-[13px] font-medium text-slate-500">{title}</p>
      )}
      <ResponsiveContainer width={width} height={height}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}
