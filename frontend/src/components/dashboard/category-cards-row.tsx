/**
 * CategoryCardsRow component.
 *
 * Row 4 of the dashboard: three CategoryCard components showing
 * aggregated data for special tender categories:
 *   1. Rental housing (type = "דיור להשכרה")
 *   2. Assisted living (purpose contains "דיור מוגן")
 *   3. Initiative tenders (type = "מכרז ייזום")
 *
 * Uses the unfiltered-by-purpose active tenders (same as Streamlit ROW 4).
 */
"use client";

import { useMemo } from "react";

import { CategoryCard } from "@/components/category-card";
import { useActiveTenders } from "@/hooks";
import { RELEVANT_TENDER_TYPES } from "@/lib/constants";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CategoryCardsRow() {
  const { data: activeTenders, isLoading } = useActiveTenders();

  // Filter to relevant types only (no purpose filter, matching Streamlit logic)
  const allActive = useMemo(
    () =>
      (activeTenders ?? []).filter((t) =>
        RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? 0),
      ),
    [activeTenders],
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

  // Category 2: Assisted living (purpose contains "דיור מוגן")
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
        <h3 className="mb-2 text-base font-semibold text-slate-800">
          {"\u05E1\u05D5\u05D2\u05D9\u05DD \u05E0\u05D5\u05E1\u05E4\u05D9\u05DD"}
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-xl bg-slate-100"
            />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section dir="rtl">
      <h3 className="mb-2 text-base font-semibold text-slate-800">
        {"\u05E1\u05D5\u05D2\u05D9\u05DD \u05E0\u05D5\u05E1\u05E4\u05D9\u05DD"}
      </h3>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <CategoryCard
          label={"\u05D3\u05D9\u05D5\u05E8 \u05DC\u05D4\u05E9\u05DB\u05E8\u05D4"}
          units={rentalHousing.units}
          count={rentalHousing.count}
        />
        <CategoryCard
          label={"\u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF"}
          units={assistedLiving.units}
          count={assistedLiving.count}
        />
        <CategoryCard
          label={"\u05DE\u05DB\u05E8\u05D6 \u05D9\u05D9\u05D6\u05D5\u05DD"}
          units={initiative.units}
          count={initiative.count}
        />
      </div>
    </section>
  );
}
