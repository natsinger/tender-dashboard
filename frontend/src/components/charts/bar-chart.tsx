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
import { corePalette } from "@/design-system/tokens/colors";
import { ChartWrapper } from "./chart-wrapper";
import { HebrewTooltip } from "./hebrew-tooltip";

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
  /** Key for annotation text above bars (e.g. total units). */
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
  annotationKey,
  className,
}: MegidoBarChartProps) {
  const isHorizontal = orientation === "horizontal";

  return (
    <ChartWrapper title={title} height={height} className={className}>
      <BarChart
        data={data}
        layout={isHorizontal ? "vertical" : "horizontal"}
        margin={isHorizontal
          ? { top: 30, right: 10, bottom: 10, left: 10 }
          : { top: 30, right: 30, bottom: 60, left: 10 }
        }
      >
        <CartesianGrid strokeDasharray="3 3" stroke={corePalette.border} />

        {isHorizontal ? (
          <>
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey={xKey}
              tick={{ fontSize: 12 }}
              width={80}
              orientation="right"
            />
          </>
        ) : (
          <>
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 11 }}
              interval={0}
              angle={-45}
              textAnchor="end"
              dy={10}
            />
            <YAxis tick={{ fontSize: 12 }} orientation="right" allowDecimals={false} />
          </>
        )}

        <Tooltip content={<HebrewTooltip />} />

        <Bar dataKey={yKey} fill={barColor} radius={isHorizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]}>
          {showLabels && (
            <LabelList
              dataKey={yKey}
              position={isHorizontal ? "right" : "inside"}
              fontSize={14}
              fill={isHorizontal ? corePalette.textHeading : "#FFFFFF"}
              fontWeight={600}
            />
          )}
          {annotationKey && (
            <LabelList
              dataKey={annotationKey}
              position="top"
              fontSize={10}
              fill={corePalette.textHeading}
              offset={4}
            />
          )}
        </Bar>
      </BarChart>
    </ChartWrapper>
  );
}
