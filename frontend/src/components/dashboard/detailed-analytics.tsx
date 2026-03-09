/**
 * DetailedAnalytics component.
 *
 * Row 5 of the dashboard: collapsible section (collapsed by default)
 * with a 2x2 chart grid:
 *   1. Top 10 cities horizontal bar chart
 *   2. Tenders by type donut chart
 *   3. Tenders over time line chart (by publish month)
 *   4. Units by tender type vertical bar chart
 *
 * Mirrors the Streamlit ROW 5 expander from pages/dashboard.py.
 */
"use client";

import { useState, useMemo } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

import { MegidoBarChart } from "@/components/charts/bar-chart";
import { MegidoPieChart } from "@/components/charts/pie-chart";
import { MegidoLineChart } from "@/components/charts/line-chart";
import { useActiveTenders } from "@/hooks";
import { RELEVANT_TENDER_TYPES } from "@/lib/constants";

// ---------------------------------------------------------------------------
// Relevant purpose filter
// ---------------------------------------------------------------------------

const RELEVANT_PURPOSES = new Set([
  "\u05D1\u05E0\u05D9\u05D9\u05D4 \u05E8\u05D5\u05D5\u05D9\u05D4",
  "\u05D1\u05E0\u05D9\u05D9\u05D4 \u05E0\u05DE\u05D5\u05DB\u05D4/\u05E6\u05DE\u05D5\u05D3\u05EA \u05E7\u05E8\u05E7\u05E2",
  "\u05DE\u05D2\u05D5\u05E8\u05D9\u05DD/\u05DE\u05E1\u05D7\u05E8/\u05DE\u05DC\u05D5\u05E0\u05D0\u05D5\u05EA/\u05E0\u05D5\u05E4\u05E9",
  "\u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF (\u05D1\u05D9\u05EA \u05D0\u05D1\u05D5\u05EA)",
  "\u05D0\u05D7\u05E8",
]);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DetailedAnalytics() {
  const [expanded, setExpanded] = useState(false);
  const { data: activeTenders } = useActiveTenders();

  // Filter to relevant types + purposes
  const filtered = useMemo(
    () =>
      (activeTenders ?? []).filter(
        (t) =>
          RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? 0) &&
          RELEVANT_PURPOSES.has(t.purpose ?? ""),
      ),
    [activeTenders],
  );

  // Chart 1: Top 10 cities horizontal bar
  const cityBarData = useMemo(() => {
    const cityMap = new Map<string, number>();
    for (const t of filtered) {
      const city = t.city ?? "\u05DC\u05D0 \u05D9\u05D3\u05D5\u05E2";
      cityMap.set(city, (cityMap.get(city) ?? 0) + 1);
    }
    return [...cityMap.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([city, count]) => ({ city, count }));
  }, [filtered]);

  // Chart 2: Tenders by type (donut)
  const typeDonutData = useMemo(() => {
    const typeMap = new Map<string, number>();
    for (const t of filtered) {
      const type = t.tender_type ?? "\u05DC\u05D0 \u05D9\u05D3\u05D5\u05E2";
      typeMap.set(type, (typeMap.get(type) ?? 0) + 1);
    }
    return [...typeMap.entries()].map(([name, value]) => ({ name, value }));
  }, [filtered]);

  // Chart 3: Tenders over time by publish month
  const timelineData = useMemo(() => {
    const monthMap = new Map<string, number>();
    for (const t of filtered) {
      if (!t.publish_date) continue;
      const d = new Date(t.publish_date);
      if (Number.isNaN(d.getTime())) continue;
      const month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      monthMap.set(month, (monthMap.get(month) ?? 0) + 1);
    }
    return [...monthMap.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([month, count]) => ({ month, count }));
  }, [filtered]);

  // Chart 4: Units by tender type
  const unitsByTypeData = useMemo(() => {
    const typeMap = new Map<string, number>();
    for (const t of filtered) {
      const type = t.tender_type ?? "\u05DC\u05D0 \u05D9\u05D3\u05D5\u05E2";
      typeMap.set(type, (typeMap.get(type) ?? 0) + (t.units ?? 0));
    }
    return [...typeMap.entries()]
      .filter(([, units]) => units > 0)
      .map(([type, units]) => ({ type, units }));
  }, [filtered]);

  return (
    <section dir="rtl">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-end hover:bg-megido-neutral-50"
      >
        {expanded ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-megido-text-muted" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-megido-text-muted" />
        )}
        <span className="text-base font-semibold text-megido-text-heading">
          {"\u05E0\u05D9\u05EA\u05D5\u05D7 \u05DE\u05E4\u05D5\u05E8\u05D8"}
        </span>
      </button>

      {/* Collapsible content with smooth animation */}
      <div
        className="grid transition-[grid-template-rows] duration-300 ease-in-out"
        style={{
          gridTemplateRows: expanded ? "1fr" : "0fr",
        }}
      >
        <div className="overflow-hidden">
          <div className="mt-3 grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Chart 1: Top 10 cities horizontal bar */}
            {cityBarData.length > 0 ? (
              <MegidoBarChart
                data={cityBarData}
                xKey="city"
                yKey="count"
                title={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD \u05DC\u05E4\u05D9 \u05E2\u05D9\u05E8"}
                orientation="horizontal"
                height={260}
              />
            ) : (
              <EmptyChart label={"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9\u05DD"} />
            )}

            {/* Chart 2: Tenders by type donut */}
            {typeDonutData.length > 0 ? (
              <MegidoPieChart
                data={typeDonutData}
                nameKey="name"
                valueKey="value"
                title={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DC\u05E4\u05D9 \u05E1\u05D5\u05D2"}
                height={260}
              />
            ) : (
              <EmptyChart label={"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9\u05DD"} />
            )}

            {/* Chart 3: Tenders over time */}
            {timelineData.length > 0 ? (
              <MegidoLineChart
                data={timelineData}
                xKey="month"
                yKey="count"
                title={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DC\u05D0\u05D5\u05E8\u05DA \u05D6\u05DE\u05DF"}
                height={260}
              />
            ) : (
              <EmptyChart label={"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9 \u05EA\u05D0\u05E8\u05D9\u05DB\u05D9\u05DD"} />
            )}

            {/* Chart 4: Units by tender type */}
            {unitsByTypeData.length > 0 ? (
              <MegidoBarChart
                data={unitsByTypeData}
                xKey="type"
                yKey="units"
                title={'\u05D9\u05D7"\u05D3 \u05DC\u05E4\u05D9 \u05E1\u05D5\u05D2'}
                orientation="vertical"
                height={260}
              />
            ) : (
              <EmptyChart label={'\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9 \u05D9\u05D7"\u05D3'} />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Empty chart placeholder
// ---------------------------------------------------------------------------

function EmptyChart({ label }: { label: string }) {
  return (
    <div className="flex h-[260px] items-center justify-center rounded-md border border-dashed border-megido-border">
      <p className="text-sm text-megido-text-muted">{label}</p>
    </div>
  );
}
