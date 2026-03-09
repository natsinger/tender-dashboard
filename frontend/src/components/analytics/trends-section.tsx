/**
 * Trends section for the Analytics page.
 *
 * Tabbed layout with:
 *   1. Regional tender volume line chart
 *   2. Regional momentum table (direction arrows)
 *   3. Monthly publication distribution bar chart
 *   4. Volume moving averages line chart (30/60/90 day)
 */
"use client";

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
import { MEGIDO_CHART_COLORS } from "@/design-system/tokens/chart-colors";
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

/** Build line chart data from regional volume. Pivot to one series per region. */
function pivotRegionalVolume(
  data: RegionalVolumeRow[],
): { chartData: Record<string, string | number>[]; regions: string[] } {
  const dateMap = new Map<string, Record<string, number>>();
  const regionSet = new Set<string>();

  for (const row of data) {
    regionSet.add(row.region);
    if (!dateMap.has(row.date)) dateMap.set(row.date, {});
    dateMap.get(row.date)![row.region] = row.count;
  }

  const regions = [...regionSet].sort();
  const chartData: Record<string, string | number>[] = [];
  for (const [date, regionCounts] of dateMap) {
    const point: Record<string, string | number> = { date };
    for (const r of regions) {
      point[r] = regionCounts[r] ?? 0;
    }
    chartData.push(point);
  }
  chartData.sort((a, b) => String(a.date).localeCompare(String(b.date)));
  return { chartData, regions };
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
  const { chartData: volChartData, regions } =
    pivotRegionalVolume(regionalVolumeData);

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-megido-text-heading">מגמות</h2>

      <Tabs defaultValue="volume" dir="rtl">
        <TabsList>
          <TabsTrigger value="volume">נפח אזורי</TabsTrigger>
          <TabsTrigger value="momentum">מומנטום אזורי</TabsTrigger>
          <TabsTrigger value="monthly">התפלגות חודשית</TabsTrigger>
          <TabsTrigger value="ma">ממוצעים נעים</TabsTrigger>
        </TabsList>

        {/* Tab 1: Regional tender volume */}
        <TabsContent value="volume">
          {volChartData.length > 0 ? (
            <ChartWrapper
              title="נפח מכרזים לפי מחוז לאורך זמן"
              height={350}
            >
              <LineChart
                data={volChartData}
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
                {regions.map((region, i) => (
                  <Line
                    key={region}
                    type="monotone"
                    dataKey={region}
                    name={region}
                    stroke={
                      MEGIDO_CHART_COLORS[i % MEGIDO_CHART_COLORS.length]
                    }
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                ))}
              </LineChart>
            </ChartWrapper>
          ) : (
            <p className="py-6 text-center text-sm text-megido-text-muted">
              אין נתונים זמינים לנפח אזורי
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
