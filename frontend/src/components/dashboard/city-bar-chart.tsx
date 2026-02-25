/**
 * CityBarChart component.
 *
 * Row 2 of the dashboard: vertical bar chart showing the top 10 active
 * cities by tender count, with annotation text above each bar displaying
 * the total housing units for that city.
 *
 * Uses MegidoBarChart (Recharts wrapper) with a custom LabelList for
 * the unit annotations. Data is aggregated from active tenders.
 */
"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
} from "recharts";

import { ChartWrapper } from "@/components/charts/chart-wrapper";
import { useActiveTenders } from "@/hooks";
import { RELEVANT_TENDER_TYPES } from "@/lib/constants";

// ---------------------------------------------------------------------------
// Relevant purpose filter (mirrors Python RELEVANT_PURPOSES)
// ---------------------------------------------------------------------------

const RELEVANT_PURPOSES = new Set([
  "\u05D1\u05E0\u05D9\u05D9\u05D4 \u05E8\u05D5\u05D5\u05D9\u05D4",
  "\u05D1\u05E0\u05D9\u05D9\u05D4 \u05E0\u05DE\u05D5\u05DB\u05D4/\u05E6\u05DE\u05D5\u05D3\u05EA \u05E7\u05E8\u05E7\u05E2",
  "\u05DE\u05D2\u05D5\u05E8\u05D9\u05DD/\u05DE\u05E1\u05D7\u05E8/\u05DE\u05DC\u05D5\u05E0\u05D0\u05D5\u05EA/\u05E0\u05D5\u05E4\u05E9",
  "\u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF (\u05D1\u05D9\u05EA \u05D0\u05D1\u05D5\u05EA)",
  "\u05D0\u05D7\u05E8",
]);

// ---------------------------------------------------------------------------
// Chart data row type
// ---------------------------------------------------------------------------

interface CityChartItem {
  city: string;
  tender_count: number;
  total_units: number;
  /** Formatted annotation string: 'סה"כ X יח"ד'. */
  annotation: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CityBarChart() {
  const { data: activeTenders, isLoading } = useActiveTenders();

  const chartData = useMemo<CityChartItem[]>(() => {
    if (!activeTenders || activeTenders.length === 0) return [];

    // Filter to relevant types and purposes (mirroring the Streamlit dashboard)
    const filtered = activeTenders.filter(
      (t) =>
        RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? 0) &&
        RELEVANT_PURPOSES.has(t.purpose ?? ""),
    );

    // Aggregate by city
    const cityMap = new Map<string, { count: number; units: number }>();

    for (const t of filtered) {
      const city = t.city ?? "\u05DC\u05D0 \u05D9\u05D3\u05D5\u05E2";
      const existing = cityMap.get(city) ?? { count: 0, units: 0 };
      existing.count += 1;
      existing.units += t.units ?? 0;
      cityMap.set(city, existing);
    }

    // Sort by count desc, take top 10
    return [...cityMap.entries()]
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 10)
      .map(([city, { count, units }]) => ({
        city,
        tender_count: count,
        total_units: units,
        annotation: `\u05E1\u05D4"\u05DB ${units.toLocaleString("he-IL")} \u05D9\u05D7"\u05D3`,
      }));
  }, [activeTenders]);

  if (isLoading) {
    return (
      <section dir="rtl">
        <p className="mb-2 text-[13px] font-medium text-slate-500">
          {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD \u05DC\u05E4\u05D9 \u05E2\u05D9\u05E8 (\u05D8\u05D5\u05E4 10)"}
        </p>
        <div className="h-[320px] animate-pulse rounded-md bg-slate-100" />
      </section>
    );
  }

  if (chartData.length === 0) {
    return (
      <section dir="rtl">
        <p className="text-sm text-slate-500">
          {"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9 \u05E2\u05E8\u05D9\u05DD"}
        </p>
      </section>
    );
  }

  return (
    <section dir="rtl">
      <ChartWrapper
        title={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD \u05DC\u05E4\u05D9 \u05E2\u05D9\u05E8 (\u05D8\u05D5\u05E4 10)"}
        height={320}
      >
        <BarChart
          data={chartData}
          margin={{ top: 40, right: 10, bottom: 10, left: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
          <XAxis dataKey="city" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="tender_count" fill="#2563EB" radius={[4, 4, 0, 0]}>
            {/* Value label inside bar */}
            <LabelList
              dataKey="tender_count"
              position="inside"
              fontSize={13}
              fill="#FFFFFF"
              fontWeight={600}
            />
            {/* Annotation above bar: total units */}
            <LabelList
              dataKey="annotation"
              position="top"
              fontSize={10}
              fill="#1E293B"
              offset={4}
            />
          </Bar>
        </BarChart>
      </ChartWrapper>
    </section>
  );
}
