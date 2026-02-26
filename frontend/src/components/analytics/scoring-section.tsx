/**
 * Scoring section for the Analytics page.
 *
 * Tabbed layout with:
 *   1. Top 20 scored tenders ranked table
 *   2. Score distribution histogram
 *   3. Radar chart deep-dive per tender
 */
"use client";

import { useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ChartWrapper } from "@/components/charts/chart-wrapper";
import { MetricCard } from "@/components/metric-card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { MEGIDO_CHART_COLORS } from "@/design-system/tokens/chart-colors";
import { getRadarData } from "@/lib/utils/analytics-engine";
import type { ScoreDistribution } from "@/lib/utils/analytics-engine";
import type { ScoredTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ScoringSectionProps {
  topTenders: ScoredTender[];
  scoreDist: ScoreDistribution;
  scoredTenders: ScoredTender[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreBadgeClass(score: number): string {
  if (score >= 70) return "bg-emerald-500 text-white";
  if (score >= 40) return "bg-amber-500 text-white";
  return "bg-red-500 text-white";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ScoringSection({
  topTenders,
  scoreDist,
  scoredTenders,
}: ScoringSectionProps) {
  const [selectedTenderId, setSelectedTenderId] = useState<string>("");

  // Build histogram chart data
  const histogramData = useMemo(() => {
    if (scoreDist.bins.length === 0) return [];
    return scoreDist.counts.map((count, i) => ({
      range: `${scoreDist.bins[i].toFixed(0)}-${scoreDist.bins[i + 1].toFixed(0)}`,
      count,
    }));
  }, [scoreDist]);

  // Get selected tender for radar
  const selectedTender = useMemo(() => {
    if (!selectedTenderId) return scoredTenders[0] ?? null;
    return (
      scoredTenders.find(
        (t) => String(t.tender_id) === selectedTenderId,
      ) ?? null
    );
  }, [selectedTenderId, scoredTenders]);

  const radarData = useMemo(
    () => (selectedTender ? getRadarData(selectedTender) : []),
    [selectedTender],
  );

  // Sorted tenders for the select dropdown
  const sortedForSelect = useMemo(
    () => [...scoredTenders].sort((a, b) => b.total_score - a.total_score),
    [scoredTenders],
  );

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">ניקוד מכרזים</h2>

      <Tabs defaultValue="top20" dir="rtl">
        <TabsList>
          <TabsTrigger value="top20">טופ 20</TabsTrigger>
          <TabsTrigger value="distribution">התפלגות ציונים</TabsTrigger>
          <TabsTrigger value="deepdive">ניתוח מכרז</TabsTrigger>
        </TabsList>

        {/* Tab 1: Top 20 scored tenders */}
        <TabsContent value="top20">
          {topTenders.length > 0 ? (
            <div className="space-y-2">
              <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                <table className="w-full table-fixed text-sm">
                  <thead>
                    <tr className="border-b-2 border-slate-200 bg-slate-50 text-right">
                      <th className="px-3 py-2 font-semibold">שם מכרז</th>
                      <th className="px-3 py-2 font-semibold">עיר</th>
                      <th className="px-3 py-2 font-semibold">מחוז</th>
                      <th className="px-3 py-2 text-center font-semibold">
                        {`יח"ד`}
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        ציון
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {topTenders.map((t) => (
                      <tr
                        key={t.tender_id}
                        className="border-b border-slate-100 hover:bg-slate-50/50"
                      >
                        <td className="truncate px-3 py-2">
                          {t.tender_name ?? "\u2014"}
                        </td>
                        <td className="truncate px-3 py-2">{t.city ?? "\u2014"}</td>
                        <td className="truncate px-3 py-2">{t.region ?? "\u2014"}</td>
                        <td className="px-3 py-2 text-center">
                          {t.units ?? 0}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span
                            className={cn(
                              "inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold",
                              scoreBadgeClass(t.total_score),
                            )}
                          >
                            {t.total_score.toFixed(0)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-slate-400">
                20 המכרזים עם הציון הגבוה ביותר (דחיפות 20%, גודל 20%, מוכנות
                25%, מיקום 20%, טריות 15%)
              </p>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-slate-400">
              אין מכרזים לניקוד
            </p>
          )}
        </TabsContent>

        {/* Tab 2: Score distribution histogram */}
        <TabsContent value="distribution">
          {histogramData.length > 0 ? (
            <div className="space-y-4">
              <ChartWrapper title="התפלגות ציוני מכרזים" height={320}>
                <BarChart
                  data={histogramData}
                  margin={{ top: 20, right: 10, bottom: 10, left: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="range" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar
                    dataKey="count"
                    name="מספר מכרזים"
                    fill={MEGIDO_CHART_COLORS[0]}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ChartWrapper>

              <div className="grid grid-cols-3 gap-3">
                <MetricCard label="ממוצע" value={scoreDist.mean.toFixed(1)} />
                <MetricCard label="חציון" value={scoreDist.median.toFixed(1)} />
                <MetricCard
                  label="סטיית תקן"
                  value={scoreDist.std.toFixed(1)}
                />
              </div>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-slate-400">
              אין ציונים זמינים להתפלגות
            </p>
          )}
        </TabsContent>

        {/* Tab 3: Tender deep-dive with radar chart */}
        <TabsContent value="deepdive">
          {scoredTenders.length > 0 ? (
            <div className="space-y-4">
              <Select
                value={selectedTenderId || String(sortedForSelect[0]?.tender_id ?? "")}
                onValueChange={setSelectedTenderId}
                dir="rtl"
              >
                <SelectTrigger className="w-full max-w-md">
                  <SelectValue placeholder="בחר מכרז לניתוח מעמיק" />
                </SelectTrigger>
                <SelectContent>
                  {sortedForSelect.slice(0, 50).map((t) => {
                    const name = t.tender_name
                      ? t.tender_name.slice(0, 35)
                      : String(t.tender_id);
                    const city = t.city ? t.city.slice(0, 15) : "";
                    return (
                      <SelectItem
                        key={t.tender_id}
                        value={String(t.tender_id)}
                      >
                        {`${name} -- ${city} (ציון: ${t.total_score.toFixed(0)})`}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>

              {selectedTender && (
                <>
                  <ChartWrapper height={380}>
                    <RadarChart
                      data={radarData}
                      margin={{ top: 20, right: 30, bottom: 20, left: 30 }}
                    >
                      <PolarGrid stroke="#E2E8F0" />
                      <PolarAngleAxis
                        dataKey="dimension"
                        tick={{ fontSize: 12, fill: "#1E293B" }}
                      />
                      <PolarRadiusAxis
                        angle={90}
                        domain={[0, 100]}
                        tick={{ fontSize: 9, fill: "#64748B" }}
                      />
                      <Radar
                        name="ציון"
                        dataKey="value"
                        stroke={MEGIDO_CHART_COLORS[0]}
                        fill={MEGIDO_CHART_COLORS[0]}
                        fillOpacity={0.2}
                        strokeWidth={2}
                      />
                    </RadarChart>
                  </ChartWrapper>

                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                    <MetricCard
                      label="דחיפות"
                      value={selectedTender.urgency_score.toFixed(0)}
                    />
                    <MetricCard
                      label="גודל"
                      value={selectedTender.size_score.toFixed(0)}
                    />
                    <MetricCard
                      label="מוכנות"
                      value={selectedTender.readiness_score.toFixed(0)}
                    />
                    <MetricCard
                      label="מיקום"
                      value={selectedTender.location_score.toFixed(0)}
                    />
                    <MetricCard
                      label="טריות"
                      value={selectedTender.freshness_score.toFixed(0)}
                    />
                  </div>

                  <p className="text-center text-sm font-semibold text-slate-700">
                    ציון כולל: {selectedTender.total_score.toFixed(1)} / 100
                  </p>
                </>
              )}
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-slate-400">
              אין מכרזים לניתוח מעמיק
            </p>
          )}
        </TabsContent>
      </Tabs>
    </section>
  );
}
