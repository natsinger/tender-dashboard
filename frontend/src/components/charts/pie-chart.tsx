/**
 * MegidoPieChart component.
 *
 * Donut chart (innerRadius 60%) with MEGIDO color palette, value labels
 * inside slices, and a horizontal bottom legend. Wraps Recharts PieChart
 * inside ChartWrapper for consistent sizing and RTL direction.
 */
"use client";

import {
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip,
} from "recharts";
import { categoricalColors } from "@/design-system/tokens/chart-colors";
import { ChartWrapper } from "./chart-wrapper";
import { HebrewTooltip } from "./hebrew-tooltip";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PieDataItem {
  [key: string]: string | number;
}

interface MegidoPieChartProps {
  /** Chart data array. */
  data: PieDataItem[];
  /** Key in each data item to use as the slice name/label. */
  nameKey: string;
  /** Key in each data item to use as the numeric value. */
  valueKey: string;
  /** Optional chart title. */
  title?: string;
  /** Chart height in pixels. Defaults to 264. */
  height?: number;
  /** Custom color palette. Defaults to categoricalColors. */
  colors?: readonly string[];
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Custom label renderer (inside slices)
// ---------------------------------------------------------------------------

import type { PieLabelRenderProps } from "recharts";

function renderInsideLabel(props: PieLabelRenderProps) {
  const {
    cx = 0,
    cy = 0,
    midAngle = 0,
    innerRadius = 0,
    outerRadius = 0,
    value = 0,
  } = props;

  const cxNum = Number(cx);
  const cyNum = Number(cy);
  const innerR = Number(innerRadius);
  const outerR = Number(outerRadius);

  const RADIAN = Math.PI / 180;
  const radius = innerR + (outerR - innerR) * 0.5;
  const x = cxNum + radius * Math.cos(-midAngle * RADIAN);
  const y = cyNum + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={14}
      fontWeight={600}
    >
      {value}
    </text>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MegidoPieChart({
  data,
  nameKey,
  valueKey,
  title,
  height = 264,
  colors = categoricalColors,
  className,
}: MegidoPieChartProps) {
  return (
    <ChartWrapper title={title} height={height} className={className}>
      <PieChart margin={{ top: 5, right: 5, bottom: 36, left: 5 }}>
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={nameKey}
          cx="50%"
          cy="50%"
          innerRadius="55%"
          outerRadius="85%"
          label={renderInsideLabel}
          labelLine={false}
        >
          {data.map((_, index) => (
            <Cell
              key={`cell-${index}`}
              fill={colors[index % colors.length]}
            />
          ))}
        </Pie>
        <Tooltip content={<HebrewTooltip />} />
        <Legend
          layout="horizontal"
          verticalAlign="bottom"
          align="center"
          wrapperStyle={{ fontSize: 11 }}
        />
      </PieChart>
    </ChartWrapper>
  );
}
