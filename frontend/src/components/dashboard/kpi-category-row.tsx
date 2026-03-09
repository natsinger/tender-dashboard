/**
 * KpiCategoryRow component.
 *
 * Combines the two KPI MetricCards (active tenders, closing soon) and
 * three CategoryCards (rental, assisted living, initiative) into a single
 * compact horizontal row. Uses a responsive grid: 2 cols on mobile,
 * 3 on tablet, 5 on desktop.
 */
"use client";

import { useMemo } from "react";

import { MetricCard } from "@/components/metric-card";
import { CategoryCard } from "@/components/category-card";
import { useActiveTenders } from "@/hooks";
import {
  CLOSING_SOON_DAYS,
  RELEVANT_TENDER_TYPES,
} from "@/lib/constants";
import { getClosingSoonTenders } from "@/lib/utils/tenders";

// ---------------------------------------------------------------------------
// Tender type codes for the "active (excluding initiative)" KPI card
// ---------------------------------------------------------------------------

/** Tender type codes for the KPI card: public(1), target price(5), reduced(8). */
const CARD_TENDER_TYPES = new Set([1, 5, 8]);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function KpiCategoryRow() {
  const { data: activeTenders, isLoading } = useActiveTenders();

  // Filter to relevant types
  const allActive = useMemo(
    () =>
      (activeTenders ?? []).filter((t) =>
        RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? 0),
      ),
    [activeTenders],
  );

  // KPI: active count (excluding initiative)
  const cardActiveCount = useMemo(
    () =>
      allActive.filter((t) =>
        CARD_TENDER_TYPES.has(t.tender_type_code ?? 0),
      ).length,
    [allActive],
  );

  // KPI: closing soon count
  const closingSoonCount = useMemo(
    () => getClosingSoonTenders(allActive, CLOSING_SOON_DAYS).length,
    [allActive],
  );

  // Category 1: Rental housing
  const rentalHousing = useMemo(() => {
    const filtered = allActive.filter(
      (t) => t.tender_type === "\u05D3\u05D9\u05D5\u05E8 \u05DC\u05D4\u05E9\u05DB\u05E8\u05D4",
    );
    return {
      count: filtered.length,
      units: filtered.reduce((sum, t) => sum + (t.units ?? 0), 0),
    };
  }, [allActive]);

  // Category 2: Assisted living
  const assistedLiving = useMemo(() => {
    const filtered = allActive.filter((t) =>
      (t.purpose ?? "").includes("\u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF"),
    );
    return {
      count: filtered.length,
      units: filtered.reduce((sum, t) => sum + (t.units ?? 0), 0),
    };
  }, [allActive]);

  // Category 3: Initiative tenders
  const initiative = useMemo(() => {
    const filtered = allActive.filter(
      (t) => t.tender_type === "\u05DE\u05DB\u05E8\u05D6 \u05D9\u05D9\u05D6\u05D5\u05DD",
    );
    return {
      count: filtered.length,
      units: filtered.reduce((sum, t) => sum + (t.units ?? 0), 0),
    };
  }, [allActive]);

  if (isLoading) {
    return (
      <section dir="rtl">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-xl bg-megido-neutral-100"
            />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section dir="rtl">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {/* KPI 1: Active tenders */}
        <MetricCard
          label={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD (\u05DC\u05DC\u05D0 \u05D9\u05D9\u05D6\u05D5\u05DD)"}
          value={cardActiveCount.toLocaleString("he-IL")}
        />
        {/* KPI 2: Closing soon */}
        <MetricCard
          label={"\u05E0\u05E1\u05D2\u05E8\u05D9\u05DD \u05D1\u05E9\u05D1\u05D5\u05E2\u05D9\u05D9\u05DD \u05D4\u05E7\u05E8\u05D5\u05D1\u05D9\u05DD"}
          value={closingSoonCount.toLocaleString("he-IL")}
        />
        {/* Category 1: Rental */}
        <CategoryCard
          label={"\u05D3\u05D9\u05D5\u05E8 \u05DC\u05D4\u05E9\u05DB\u05E8\u05D4"}
          units={rentalHousing.units}
          count={rentalHousing.count}
        />
        {/* Category 2: Assisted living */}
        <CategoryCard
          label={"\u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF"}
          units={assistedLiving.units}
          count={assistedLiving.count}
        />
        {/* Category 3: Initiative */}
        <CategoryCard
          label={"\u05DE\u05DB\u05E8\u05D6 \u05D9\u05D9\u05D6\u05D5\u05DD"}
          units={initiative.units}
          count={initiative.count}
        />
      </div>
    </section>
  );
}
