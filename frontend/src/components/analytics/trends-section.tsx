/**
 * Trends section for the Analytics page.
 *
 * Tabbed layout with:
 *   1. Monthly tender volume by year (overlay) — months on X-axis, one line per year
 *   2. Regional momentum table (direction arrows)
 *   3. Monthly publication distribution bar chart
 *   4. Volume moving averages line chart (30/60/90 day)
 */
"use client";

import { useState, useMemo } from "react";

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LabelList,
} from "recharts";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ChartWrapper } from "@/components/charts/chart-wrapper";
import { Badge } from "@/components/ui/badge";
import { MEGIDO_CHART_COLORS, MEGIDO_CHART_COLORS_EXTENDED } from "@/design-system/tokens/chart-colors";
import { corePalette } from "@/design-system/tokens/colors";
import type {
  RegionalVolumeRow,
  MomentumRow,
  MonthlyDistributionRow,
  VolumeMovingAverageRow,
} from "@/lib/utils/analytics-engine";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TrendsSectionProps {
  regionalVolumeData: RegionalVolumeRow[];
  momentumData: MomentumRow[];
  monthlyData: MonthlyDistributionRow[];
  movingAvgData: VolumeMovingAverageRow[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MONTH_NAMES_HE = [
  "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
  "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
] as const;

/**
 * Aggregate regional volume data into per-year monthly totals.
 * Returns chart data with months (1-12) on the X-axis and one key per year.
 * Excludes data beyond the current month to avoid showing future dates
 * that the API sometimes returns.
 */
function pivotByYear(
  data: RegionalVolumeRow[],
  selectedYears: Set<string>,
): { chartData: Record<string, string | number>[]; allYears: string[]; years: string[] } {
  const now = new Date();
  const currentYear = String(now.getFullYear());
  const currentMonth = now.getMonth() + 1; // 1-based
  const cutoff = `${currentYear}-${String(currentMonth).padStart(2, "0")}`;

  // Sum all regions per YYYY-MM bucket, ignoring anything after current month
  const monthlyTotals = new Map<string, number>();
  for (const row of data) {
    if (row.date > cutoff) continue;
    monthlyTotals.set(row.date, (monthlyTotals.get(row.date) ?? 0) + row.count);
  }

  // All available years in the data
  const allYears = [...new Set([...monthlyTotals.keys()].map((d) => d.slice(0, 4)))].sort();
  const years = allYears.filter((y) => selectedYears.has(y));

  // Pivot: one row per month (1-12), one column per year.
  // For the current year, only show up to the current month.
  const chartData: Record<string, string | number>[] = [];
  for (let m = 1; m <= 12; m++) {
    const mm = String(m).padStart(2, "0");
    const point: Record<string, string | number> = { month: MONTH_NAMES_HE[m - 1] };
    for (const y of years) {
      if (y === currentYear && m > currentMonth) continue;
      point[y] = monthlyTotals.get(`${y}-${mm}`) ?? 0;
    }
    chartData.push(point);
  }

  return { chartData, allYears, years };
}

const DIRECTION_LABELS: Record<string, string> = {
  up: "עולה",
  down: "יורד",
  stable: "יציב",
};

const DIRECTION_COLORS: Record<string, string> = {
  up: "bg-emerald-100 text-emerald-700",
  down: "bg-red-100 text-red-700",
  stable: "bg-megido-neutral-100 text-megido-neutral-600",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TrendsSection({
  regionalVolumeData,
  momentumData,
  monthlyData,
  movingAvgData,
}: TrendsSectionProps) {
  // Derive all available years from data (stable across renders)
  const allAvailableYears = useMemo(() => {
    const now = new Date();
    const cutoff = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const yearSet = new Set<string>();
    for (const row of regionalVolumeData) {
      if (row.date <= cutoff) yearSet.add(row.date.slice(0, 4));
    }
    return [...yearSet].sort();
  }, [regionalVolumeData]);

  // Default to the 3 most recent years
  const [selectedYears, setSelectedYears] = useState<Set<string>>(() => {
    const now = new Date();
    const cur = now.getFullYear();
    return new Set([String(cur), String(cur - 1), String(cur - 2)]);
  });

  const toggleYear = (year: string) => {
    setSelectedYears((prev) => {
      const next = new Set(prev);
      if (next.has(year)) {
        next.delete(year);
      } else {
        next.add(year);
      }
      return next;
    });
  };

  const { chartData: volChartData, years } = useMemo(
    () => pivotByYear(regionalVolumeData, selectedYears),
    [regionalVolumeData, selectedYears],
  );

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-megido-text-heading">מגמות</h2>

      <Tabs defaultValue="volume" dir="rtl">
        <TabsList>
          <TabsTrigger value="volume">מכרזים לפי חודש</TabsTrigger>
          <TabsTrigger value="momentum">מומנטום אזורי</TabsTrigger>
          <TabsTrigger value="monthly">התפלגות חודשית</TabsTrigger>
          <TabsTrigger value="ma">ממוצעים נעים</TabsTrigger>
        </TabsList>

        {/* Tab 1: Monthly tender volume by year */}
        <TabsContent value="volume">
          {volChartData.length > 0 ? (
            <div className="space-y-4">
              {/* Year selector */}
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="ml-1 text-xs text-megido-text-muted">שנים:</span>
                {allAvailableYears.map((year) => (
                  <button
                    key={year}
                    onClick={() => toggleYear(year)}
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                      selectedYears.has(year)
                        ? "bg-megido-primary text-white"
                        : "bg-megido-neutral-100 text-megido-text-muted hover:bg-megido-neutral-200"
                    }`}
                  >
                    {year}
                  </button>
                ))}
              </div>

              <ChartWrapper
                title="כמות מכרזים לפי חודש — השוואה שנתית"
                height={440}
              >
                <LineChart
                  data={volChartData}
                  margin={{ top: 24, right: 24, bottom: 24, left: 24 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={corePalette.border} />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11 }}
                    tickMargin={10}
                    padding={{ left: 20, right: 20 }}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    orientation="right"
                    tickMargin={8}
                  />
                  <Tooltip />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    wrapperStyle={{ fontSize: 11, paddingBottom: 16 }}
                  />
                  {years.map((year, i) => (
                    <Line
                      key={year}
                      type="monotone"
                      dataKey={year}
                      name={year}
                      stroke={
                        MEGIDO_CHART_COLORS_EXTENDED[i % MEGIDO_CHART_COLORS_EXTENDED.length]
                      }
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  ))}
                </LineChart>
              </ChartWrapper>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-megido-text-muted">
              אין נתונים זמינים
            </p>
          )}
        </TabsContent>

        {/* Tab 2: Regional momentum */}
        <TabsContent value="momentum">
          {momentumData.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-megido-border bg-megido-bg-card">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-megido-border bg-megido-neutral-50 text-end">
                    <th className="px-3 py-2 font-semibold">מחוז</th>
                    <th className="px-3 py-2 text-center font-semibold">
                      תקופה אחרונה
                    </th>
                    <th className="px-3 py-2 text-center font-semibold">
                      תקופה קודמת
                    </th>
                    <th className="px-3 py-2 text-center font-semibold">
                      שינוי %
                    </th>
                    <th className="px-3 py-2 text-center font-semibold">
                      כיוון
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {momentumData.map((row) => (
                    <tr
                      key={row.region}
                      className="border-b border-megido-neutral-100 hover:bg-megido-neutral-50/50"
                    >
                      <td className="px-3 py-2">{row.region}</td>
                      <td className="px-3 py-2 text-center">
                        {row.recentCount}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {row.previousCount}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {row.changePct.toFixed(1)}%
                      </td>
                      <td className="px-3 py-2 text-center">
                        <Badge
                          variant="secondary"
                          className={DIRECTION_COLORS[row.direction]}
                        >
                          {DIRECTION_LABELS[row.direction]}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-megido-text-muted">
              אין מספיק נתונים לניתוח מומנטום
            </p>
          )}
        </TabsContent>

        {/* Tab 3: Monthly publication distribution */}
        <TabsContent value="monthly">
          {monthlyData.length > 0 ? (
            <ChartWrapper
              title="התפלגות פרסום חודשית (ממוצע שנתי)"
              height={320}
            >
              <BarChart
                data={monthlyData}
                margin={{ top: 30, right: 10, bottom: 10, left: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={corePalette.border} />
                <XAxis dataKey="monthNameHe" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} orientation="right" />
                <Tooltip />
                <Bar
                  dataKey="avgCount"
                  name="ממוצע מכרזים"
                  fill={MEGIDO_CHART_COLORS[0]}
                  radius={[4, 4, 0, 0]}
                >
                  <LabelList
                    dataKey="avgCount"
                    position="top"
                    fontSize={12}
                    fill={corePalette.textHeading}
                    fontWeight={600}
                  />
                </Bar>
              </BarChart>
            </ChartWrapper>
          ) : (
            <p className="py-6 text-center text-sm text-megido-text-muted">
              אין נתונים להתפלגות חודשית
            </p>
          )}
        </TabsContent>

        {/* Tab 4: Volume moving averages */}
        <TabsContent value="ma">
          {movingAvgData.length > 0 ? (
            <ChartWrapper
              title="ממוצעים נעים -- נפח פרסום מכרזים"
              height={320}
            >
              <LineChart
                data={movingAvgData}
                margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={corePalette.border} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} orientation="right" />
                <Tooltip />
                <Legend
                  verticalAlign="top"
                  align="right"
                  wrapperStyle={{ fontSize: 11 }}
                />
                <Line
                  type="monotone"
                  dataKey="ma30"
                  name="30 יום"
                  stroke={MEGIDO_CHART_COLORS[0]}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="ma60"
                  name="60 יום"
                  stroke={MEGIDO_CHART_COLORS[2]}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="ma90"
                  name="90 יום"
                  stroke={MEGIDO_CHART_COLORS[1]}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ChartWrapper>
          ) : (
            <p className="py-6 text-center text-sm text-megido-text-muted">
              אין נתונים לממוצעים נעים
            </p>
          )}
        </TabsContent>
      </Tabs>
    </section>
  );
}
