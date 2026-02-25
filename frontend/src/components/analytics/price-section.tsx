/**
 * Price Analytics section for the Analytics page.
 *
 * Tabbed layout with:
 *   1. Price trends line chart by region
 *   2. Taba analysis summary table
 *   3. Price premium analysis table
 */
"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ChartWrapper } from "@/components/charts/chart-wrapper";
import { MEGIDO_CHART_COLORS } from "@/design-system/tokens/chart-colors";
import type {
  PriceTrendRow,
  TabaSummaryRow,
  PricePremiumRow,
} from "@/lib/utils/analytics-engine";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PriceSectionProps {
  priceTrends: PriceTrendRow[];
  tabaSummary: TabaSummaryRow[];
  premiumData: PricePremiumRow[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Pivot price trends to one series per region for LineChart. */
function pivotPriceTrends(
  data: PriceTrendRow[],
): { chartData: Record<string, string | number>[]; regions: string[] } {
  const dateMap = new Map<string, Record<string, number>>();
  const regionSet = new Set<string>();

  for (const row of data) {
    regionSet.add(row.region);
    if (!dateMap.has(row.date)) dateMap.set(row.date, {});
    dateMap.get(row.date)![row.region] = row.avgPricePerSqm;
  }

  const regions = [...regionSet].sort();
  const chartData: Record<string, string | number>[] = [];
  for (const [date, regionPrices] of dateMap) {
    const point: Record<string, string | number> = { date };
    for (const r of regions) {
      point[r] = regionPrices[r] ?? 0;
    }
    chartData.push(point);
  }
  chartData.sort((a, b) => String(a.date).localeCompare(String(b.date)));
  return { chartData, regions };
}

function formatCurrency(value: number | null): string {
  if (value == null || value === 0) return "\u2014";
  return `\u20AA${value.toLocaleString("he-IL", { maximumFractionDigits: 0 })}`;
}

function formatPct(value: number | null): string {
  if (value == null) return "\u2014";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PriceSection({
  priceTrends,
  tabaSummary,
  premiumData,
}: PriceSectionProps) {
  const { chartData: priceChartData, regions: priceRegions } =
    pivotPriceTrends(priceTrends);

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">ניתוח מחירים</h2>

      <Tabs defaultValue="trends" dir="rtl">
        <TabsList>
          <TabsTrigger value="trends">מגמות מחירים</TabsTrigger>
          <TabsTrigger value="taba">{`ניתוח תב"ע`}</TabsTrigger>
          <TabsTrigger value="premium">פרמיית מחיר</TabsTrigger>
        </TabsList>

        {/* Tab 1: Price trends by region */}
        <TabsContent value="trends">
          {priceChartData.length > 0 ? (
            <ChartWrapper
              title={`מגמות מחיר זכייה ממוצע למ"ר לפי מחוז`}
              height={350}
            >
              <LineChart
                data={priceChartData}
                margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend
                  verticalAlign="top"
                  align="right"
                  wrapperStyle={{ fontSize: 11 }}
                />
                {priceRegions.map((region, i) => (
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
            <p className="py-6 text-center text-sm text-slate-400">
              {`אין נתוני מחירים עם שטח קרקע תקין לחישוב מחיר למ"ר`}
            </p>
          )}
        </TabsContent>

        {/* Tab 2: Taba analysis summary */}
        <TabsContent value="taba">
          {tabaSummary.length > 0 ? (
            <div className="space-y-2">
              <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-slate-200 bg-slate-50 text-right">
                      <th className="px-3 py-2 font-semibold">{`מספר תב"ע`}</th>
                      <th className="px-3 py-2 text-center font-semibold">
                        מכרזים
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        {`יח"ד`}
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        שומה ממוצעת
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        זכייה ממוצעת
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        פרמיה מול שומה
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        קצב/שנה
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {tabaSummary.slice(0, 50).map((row) => (
                      <tr
                        key={row.planNumber}
                        className="border-b border-slate-100 hover:bg-slate-50/50"
                      >
                        <td className="px-3 py-2">{row.planNumber}</td>
                        <td className="px-3 py-2 text-center">
                          {row.tenderCount}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {row.totalUnits ?? "\u2014"}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {formatCurrency(row.avgAppraisalPrice)}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {formatCurrency(row.avgWinningBid)}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {formatPct(row.premiumVsAppraisalPct)}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {row.tenderRatePerYear?.toFixed(1) ?? "\u2014"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-slate-400">
                {`ניתוח מצטבר לפי תב"ע -- מחירים, פרמיות וקצב מכרזים`}
              </p>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-slate-400">
              {`אין נתוני תב"ע מעובדים`}
            </p>
          )}
        </TabsContent>

        {/* Tab 3: Price premium analysis */}
        <TabsContent value="premium">
          {premiumData.length > 0 ? (
            <div className="space-y-2">
              <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-slate-200 bg-slate-50 text-right">
                      <th className="px-3 py-2 font-semibold">מכרז</th>
                      <th className="px-3 py-2 text-center font-semibold">
                        שומה
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        מחיר סף
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        זכייה
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        פרמיה מול שומה
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        פרמיה מול סף
                      </th>
                      <th className="px-3 py-2 font-semibold">מחוז</th>
                    </tr>
                  </thead>
                  <tbody>
                    {premiumData.slice(0, 50).map((row, i) => (
                      <tr
                        key={`${row.tenderId}-${i}`}
                        className="border-b border-slate-100 hover:bg-slate-50/50"
                      >
                        <td className="px-3 py-2">{row.tenderId}</td>
                        <td className="px-3 py-2 text-center">
                          {formatCurrency(row.appraisalPrice)}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {formatCurrency(row.floorPrice)}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {formatCurrency(row.winningPrice)}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {formatPct(row.premiumVsAppraisalPct)}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {formatPct(row.premiumVsFloorPct)}
                        </td>
                        <td className="px-3 py-2">{row.region ?? "\u2014"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-slate-400">
                {`פרמיית/הנחת מחיר זכייה ביחס לשומת רמ"י ומחיר סף`}
              </p>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-slate-400">
              אין מכרזים עם נתוני הצעות זוכות
            </p>
          )}
        </TabsContent>
      </Tabs>
    </section>
  );
}
