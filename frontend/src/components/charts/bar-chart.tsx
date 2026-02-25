/**
 * MegidoBarChart component.
 *
 * Vertical or horizontal bar chart with MEGIDO color palette,
 * value annotations above/beside bars, and consistent styling.
 * Wraps Recharts BarChart inside ChartWrapper.
 */
"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
} from "recharts";
import { MEGIDO_CHART_COLORS } from "@/design-system/tokens/chart-colors";
import { ChartWrapper } from "./chart-wrapper";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BarDataItem {
  [key: string]: string | number;
}

interface MegidoBarChartProps {
  /** Chart data array. */
  data: BarDataItem[];
  /** Key for the category axis (X for vertical, Y for horizontal). */
  xKey: string;
  /** Key for the value axis. */
  yKey: string;
  /** Optional chart title. */
  title?: string;
  /** Bar orientation. Defaults to "vertical". */
  orientation?: "vertical" | "horizontal";
  /** Chart height in pixels. Defaults to 320. */
  height?: number;
  /** Bar fill color. Defaults to MEGIDO primary blue. */
  barColor?: string;
  /** Show value labels on bars. Defaults to true. */
  showLabels?: boolean;
  /** Optional second data key for annotation text above bars. */
  annotationKey?: string;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MegidoBarChart({
  data,
  xKey,
  yKey,
  title,
  orientation = "vertical",
  height = 320,
  barColor = MEGIDO_CHART_COLORS[0],
  showLabels = true,
  className,
}: MegidoBarChartProps) {
  const isHorizontal = orientation === "horizontal";

  return (
    <ChartWrapper title={title} height={height} className={className}>
      <BarChart
        data={data}
        layout={isHorizontal ? "vertical" : "horizontal"}
        margin={{ top: 30, right: 10, bottom: 10, left: 10 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />

        {isHorizontal ? (
          <>
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey={xKey}
              tick={{ fontSize: 12 }}
              width={80}
            />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
          </>
        )}

        <Tooltip />

        <Bar dataKey={yKey} fill={barColor} radius={[4, 4, 0, 0]}>
          {showLabels && (
            <LabelList
              dataKey={yKey}
              position={isHorizontal ? "right" : "top"}
              fontSize={13}
              fill="#1E293B"
              fontWeight={600}
            />
          )}
        </Bar>
      </BarChart>
    </ChartWrapper>
  );
}
