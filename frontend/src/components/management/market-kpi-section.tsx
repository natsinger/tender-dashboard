/**
 * MarketKPISection component for the Management page.
 *
 * Displays a 2x2 chart grid (brochure donut, region donut, top-10 cities
 * bar chart, tender type pie) plus 5 KPI metric cards. Default view shows
 * brochure tenders only (more reliable data); toggle to see all.
 */
"use client";

import { useMemo, useState } from "react";

import { MegidoPieChart } from "@/components/charts/pie-chart";
import { corePalette } from "@/design-system/tokens/colors";
import { MegidoBarChart } from "@/components/charts/bar-chart";
import { MetricCard } from "@/components/metric-card";
import {
  UnitCompositionCard,
  type CompositionSegment,
} from "@/components/management/unit-composition-card";
import { BrochureToggle, type BrochureFilter } from "@/components/brochure-toggle";
import type { LotAggregation } from "@/hooks/use-bulk-lots";
import type { TenderWithComputed } from "@/types/database";

// ---------------------------------------------------------------------------
// Segment color map for tender types
// ---------------------------------------------------------------------------

const TYPE_COLORS: Record<string, string> = {
  "\u05DE\u05DB\u05E8\u05D6 \u05E4\u05D5\u05DE\u05D1\u05D9 \u05E8\u05D2\u05D9\u05DC": "bg-megido-primary",
  "\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4": "bg-emerald-500",
  "\u05D3\u05D9\u05D5\u05E8 \u05D1\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D5\u05E4\u05D7\u05EA": "bg-amber-500",
};
const TYPE_FALLBACK_COLOR = "bg-neutral-400";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MarketKPISectionProps {
  /** Active tenders filtered to CARD_TENDER_TYPES (1, 5, 8). */
  cardActiveTenders: TenderWithComputed[];
  /** Count of tenders closing within 14 days. */
  closingSoonCount: number;
  /** Lot aggregation map for all card-active tenders. */
  lotMap: Record<number, LotAggregation>;
}

// ---------------------------------------------------------------------------
// Data transformers
// ---------------------------------------------------------------------------

function buildBrochureData(
  tenders: TenderWithComputed[],
): { name: string; value: number }[] {
  let withBrochure = 0;
  let withoutBrochure = 0;

  for (const t of tenders) {
    if (t.published_booklet) {
      withBrochure++;
    } else {
      withoutBrochure++;
    }
  }

  return [
    { name: "\u05D9\u05E9 \u05D7\u05D5\u05D1\u05E8\u05EA", value: withBrochure },
    { name: "\u05D1\u05DC\u05D9 \u05D7\u05D5\u05D1\u05E8\u05EA", value: withoutBrochure },
  ];
}

function buildRegionData(
  tenders: TenderWithComputed[],
): { name: string; value: number }[] {
  const counts: Record<string, number> = {};
  for (const t of tenders) {
    const region = t.region ?? "\u05DC\u05D0 \u05D9\u05D3\u05D5\u05E2";
    counts[region] = (counts[region] ?? 0) + 1;
  }

  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

function buildTenderTypeData(
  tenders: TenderWithComputed[],
): { name: string; value: number }[] {
  const counts: Record<string, number> = {};
  for (const t of tenders) {
    const type = t.tender_type ?? "\u05DC\u05D0 \u05D9\u05D3\u05D5\u05E2";
    counts[type] = (counts[type] ?? 0) + 1;
  }

  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

type CityBarItem = Record<string, string | number>;

function buildCityBarData(tenders: TenderWithComputed[]): CityBarItem[] {
  const cityMap: Record<string, { count: number; units: number }> = {};
  for (const t of tenders) {
    const city = t.city ?? "\u05DC\u05D0 \u05D9\u05D3\u05D5\u05E2";
    if (!cityMap[city]) {
      cityMap[city] = { count: 0, units: 0 };
    }
    cityMap[city].count++;
    cityMap[city].units += t.units ?? 0;
  }

  return Object.entries(cityMap)
    .map(([city, data]) => ({
      city,
      count: data.count,
      units: data.units,
      annotation: `\u05E1\u05D4"\u05DB ${data.units.toLocaleString("he-IL")} \u05D9\u05D7"\u05D3`,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MarketKPISection({
  cardActiveTenders,
  closingSoonCount,
  lotMap,
}: MarketKPISectionProps) {
  const [brochureFilter, setBrochureFilter] =
    useState<BrochureFilter>("with_brochure");

  // Filter tenders based on brochure toggle
  const filteredTenders = useMemo(() => {
    if (brochureFilter === "with_brochure") {
      return cardActiveTenders.filter((t) => Boolean(t.published_booklet));
    }
    return cardActiveTenders;
  }, [cardActiveTenders, brochureFilter]);

  const brochureData = useMemo(
    () => buildBrochureData(cardActiveTenders),
    [cardActiveTenders],
  );
  const regionData = useMemo(
    () => buildRegionData(filteredTenders),
    [filteredTenders],
  );
  const tenderTypeData = useMemo(
    () => buildTenderTypeData(filteredTenders),
    [filteredTenders],
  );
  const cityBarData = useMemo(
    () => buildCityBarData(filteredTenders),
    [filteredTenders],
  );

  // KPI aggregations — lot-based when brochure filter is active,
  // tender-level when showing all tenders.
  const isBrochureMode = brochureFilter === "with_brochure";

  // Brochure mode: lot-level FM/TP breakdown
  const { totalUnits: brochureTotal, segments: brochureSegments, footnote: brochureFootnote } =
    useMemo(() => {
      let total = 0;
      let fm = 0;
      let tp = 0;
      let withData = 0;
      const tenderIds = new Set(filteredTenders.map((t) => t.tender_id));

      for (const [tidStr, agg] of Object.entries(lotMap)) {
        const tid = Number(tidStr);
        if (!tenderIds.has(tid)) continue;
        fm += agg.free_market;
        tp += agg.target_price;
        total += agg.total;
        if (agg.total > 0) withData++;
      }

      const unclassified = total - fm - tp;
      const segments: CompositionSegment[] = [];
      if (fm > 0) segments.push({ label: "\u05E9\u05D5\u05E7 \u05D7\u05D5\u05E4\u05E9\u05D9", value: fm, color: "bg-megido-primary" });
      if (tp > 0) segments.push({ label: "\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4", value: tp, color: "bg-emerald-500" });
      if (unclassified > 0) segments.push({ label: "\u05DC\u05DC\u05D0 \u05E4\u05D9\u05E8\u05D5\u05D8", value: unclassified, color: "bg-neutral-300" });

      const footnote = filteredTenders.length > 0
        ? `\u05DE\u05D1\u05D5\u05E1\u05E1 \u05E2\u05DC ${withData} \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E2\u05DD \u05E0\u05EA\u05D5\u05E0\u05D9 \u05DE\u05D2\u05E8\u05E9\u05D9\u05DD \u05DE\u05EA\u05D5\u05DA ${filteredTenders.length}`
        : undefined;

      return { totalUnits: total, segments, footnote };
    }, [filteredTenders, lotMap]);

  // All-tenders mode: breakdown by tender type
  const { totalUnits: allTotal, segments: allSegments } = useMemo(() => {
    const typeUnits: Record<string, number> = {};
    let total = 0;

    for (const t of filteredTenders) {
      const units = t.units ?? 0;
      const type = t.tender_type ?? "\u05DC\u05D0 \u05D9\u05D3\u05D5\u05E2";
      typeUnits[type] = (typeUnits[type] ?? 0) + units;
      total += units;
    }

    const segments: CompositionSegment[] = Object.entries(typeUnits)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([label, value]) => ({
        label,
        value,
        color: TYPE_COLORS[label] ?? TYPE_FALLBACK_COLOR,
      }));

    return { totalUnits: total, segments };
  }, [filteredTenders]);

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h4 className="text-lg font-semibold text-megido-text-heading">
          {"\u05DE\u05DB\u05E8\u05D6\u05D9 \u05DE\u05E7\u05E8\u05E7\u05E2\u05D9\u05DF \u05DC\u05D3\u05D9\u05D5\u05E8 \u05DC\u05DE\u05DB\u05D9\u05E8\u05D4"}
        </h4>
        <BrochureToggle
          value={brochureFilter}
          onChange={setBrochureFilter}
        />
      </div>

      {/* 2x2 chart grid + KPI cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Charts column (3/5 width) */}
        <div className="space-y-6 lg:col-span-3">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <MegidoPieChart
              data={brochureData}
              nameKey="name"
              valueKey="value"
              title={"\u05D7\u05D5\u05D1\u05E8\u05EA \u05DE\u05DB\u05E8\u05D6"}
              height={264}
              colors={[corePalette.primary, corePalette.border]}
            />
            <MegidoPieChart
              data={regionData}
              nameKey="name"
              valueKey="value"
              title={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DC\u05E4\u05D9 \u05DE\u05D7\u05D5\u05D6"}
              height={264}
            />
          </div>

          {/* Top 10 cities bar chart */}
          <MegidoBarChart
            data={cityBarData}
            xKey="city"
            yKey="count"
            annotationKey="annotation"
            title={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD \u05DC\u05E4\u05D9 \u05E2\u05D9\u05E8 (\u05D8\u05D5\u05E4 10)"}
            height={420}
          />

          {/* Tender type pie chart */}
          <MegidoPieChart
            data={tenderTypeData}
            nameKey="name"
            valueKey="value"
            title={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DC\u05E4\u05D9 \u05E1\u05D5\u05D2"}
            height={264}
          />
        </div>

        {/* KPI column (2/5 width) */}
        <div className="space-y-4 lg:col-span-2">
          {/* Row 1: Active + closing */}
          <div className="grid grid-cols-2 gap-3">
            <MetricCard
              label={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD"}
              value={filteredTenders.length.toLocaleString("he-IL")}
            />
            <MetricCard
              label={"\u05E0\u05E1\u05D2\u05E8\u05D9\u05DD \u05D1-14 \u05D9\u05D5\u05DD"}
              value={closingSoonCount}
            />
          </div>

          {/* Row 2: Unit composition */}
          {isBrochureMode ? (
            <UnitCompositionCard
              total={brochureTotal}
              segments={brochureSegments}
              footnote={brochureFootnote}
            />
          ) : (
            <UnitCompositionCard
              total={allTotal}
              segments={allSegments}
            />
          )}
        </div>
      </div>
    </section>
  );
}
