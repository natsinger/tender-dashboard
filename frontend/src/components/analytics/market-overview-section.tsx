/**
 * Market Overview section for the Analytics page.
 *
 * Displays 4 KPI cards (total tenders, avg score, active regions, total units)
 * and a supply pipeline area chart showing new published, closing, and net change.
 */
"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Line,
  ComposedChart,
} from "recharts";

import { MetricCard } from "@/components/metric-card";
import { ChartWrapper } from "@/components/charts/chart-wrapper";
import { MEGIDO_CHART_COLORS } from "@/design-system/tokens/chart-colors";
import type { SupplyPipelineRow } from "@/lib/utils/analytics-engine";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MarketOverviewSectionProps {
  totalTenders: number;
  avgScore: number;
  activeRegions: number;
  totalUnits: number;
  pipelineData: SupplyPipelineRow[];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MarketOverviewSection({
  totalTenders,
  avgScore,
  activeRegions,
  totalUnits,
  pipelineData,
}: MarketOverviewSectionProps) {
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">
        סקירת שוק
      </h2>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard
          label={'סה"כ מכרזים'}
          value={totalTenders.toLocaleString("he-IL")}
        />
        <MetricCard
          label="ציון ממוצע"
          value={avgScore.toFixed(1)}
        />
        <MetricCard
          label="מחוזות פעילים"
          value={activeRegions}
        />
        <MetricCard
          label={'סה"כ יח"ד'}
          value={totalUnits.toLocaleString("he-IL")}
        />
      </div>

      {/* Supply pipeline chart */}
      {pipelineData.length > 0 ? (
        <ChartWrapper title="צינור היצע מכרזים" height={320}>
          <ComposedChart
            data={pipelineData}
            margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ fontSize: 11, paddingBottom: 8 }}
            />
            <Area
              type="monotone"
              dataKey="newPublished"
              name="מכרזים חדשים"
              stroke={MEGIDO_CHART_COLORS[0]}
              fill={MEGIDO_CHART_COLORS[0]}
              fillOpacity={0.3}
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="closing"
              name="נסגרים"
              stroke={MEGIDO_CHART_COLORS[2]}
              fill={MEGIDO_CHART_COLORS[2]}
              fillOpacity={0.2}
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="activeNet"
              name="שינוי נטו"
              stroke="#EF4444"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
            />
          </ComposedChart>
        </ChartWrapper>
      ) : (
        <p className="py-6 text-center text-sm text-slate-400">
          אין מספיק נתונים לתצוגת צינור היצע
        </p>
      )}
    </section>
  );
}
