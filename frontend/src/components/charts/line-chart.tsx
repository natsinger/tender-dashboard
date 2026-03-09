/**
 * MegidoLineChart component.
 *
 * Line chart with dot markers, MEGIDO color palette, and consistent
 * styling. Used for time-series data (e.g. tenders over time).
 * Wraps Recharts LineChart inside ChartWrapper.
 */
"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { corePalette } from "@/design-system/tokens/colors";
import { ChartWrapper } from "./chart-wrapper";
import { HebrewTooltip } from "./hebrew-tooltip";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LineDataItem {
  [key: string]: string | number;
}

interface MegidoLineChartProps {
  /** Chart data array. */
  data: LineDataItem[];
  /** Key for the X-axis (category/time). */
  xKey: string;
  /** Key for the Y-axis (numeric value). */
  yKey: string;
  /** Optional chart title. */
  title?: string;
  /** Chart height in pixels. Defaults to 260. */
  height?: number;
  /** Line stroke color. Defaults to MEGIDO secondary navy. */
  lineColor?: string;
  /** Show dots on data points. Defaults to true. */
  showDots?: boolean;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MegidoLineChart({
  data,
  xKey,
  yKey,
  title,
  height = 260,
  lineColor = corePalette.secondary,
  showDots = true,
  className,
}: MegidoLineChartProps) {
  return (
    <ChartWrapper title={title} height={height} className={className}>
      <LineChart
        data={data}
        margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={corePalette.border} />
        <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} orientation="right" />
        <Tooltip content={<HebrewTooltip />} />
        <Line
          type="monotone"
          dataKey={yKey}
          stroke={lineColor}
          strokeWidth={2}
          dot={
            showDots
              ? { fill: lineColor, stroke: lineColor, r: 4 }
              : false
          }
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ChartWrapper>
  );
}
