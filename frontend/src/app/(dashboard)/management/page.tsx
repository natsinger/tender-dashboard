/**
 * Management page -- executive overview dashboard (luch hanhala).
 *
 * Composes four sections:
 *   1. Team Watchlist Table (shared team favorites with review status)
 *   2. Closing Soon (collapsible, tenders closing within 14 days)
 *   3. Market KPIs and Charts (pie/bar charts + metric cards)
 *   4. Category Tabs (rental housing, sheltered housing, initiative tenders)
 *
 * Data is loaded via React Query hooks. Filtering for relevant tender types
 * and purposes mirrors the Python management.py logic.
 */
"use client";

import { useMemo } from "react";

import { PageHeader } from "@/components/page-header";
import { Separator } from "@/components/ui/separator";
import { TeamWatchlistSection } from "@/components/management/team-watchlist-section";
import { ClosingSoonSection } from "@/components/management/closing-soon-section";
import { MarketKPISection } from "@/components/management/market-kpi-section";
import { CategoryTabsSection } from "@/components/management/category-tabs-section";
import { useActiveTenders } from "@/hooks/use-tenders";
import { useBulkLots } from "@/hooks/use-bulk-lots";
import { RELEVANT_TENDER_TYPES } from "@/lib/constants";
import { getClosingSoonTenders } from "@/lib/utils/tenders";
import type { TenderWithComputed } from "@/types/database";

// ---------------------------------------------------------------------------
// Constants (mirroring management.py)
// ---------------------------------------------------------------------------

/** Purpose filter: codes 1, 2, 12, 13 only. */
const RELEVANT_PURPOSES = new Set([
  "\u05D1\u05E0\u05D9\u05D9\u05D4 \u05E0\u05DE\u05D5\u05DB\u05D4/\u05E6\u05DE\u05D5\u05D3\u05EA \u05E7\u05E8\u05E7\u05E2",
  "\u05D1\u05E0\u05D9\u05D9\u05D4 \u05E8\u05D5\u05D5\u05D9\u05D4",
  "\u05DE\u05D2\u05D5\u05E8\u05D9\u05DD/\u05DE\u05E1\u05D7\u05E8/\u05DE\u05DC\u05D5\u05E0\u05D0\u05D5\u05EA/\u05E0\u05D5\u05E4\u05E9",
  "\u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF (\u05D1\u05D9\u05EA \u05D0\u05D1\u05D5\u05EA)",
]);

/** The 3 tender types for KPI cards (codes 1, 5, 8). */
const CARD_TENDER_TYPES = new Set([1, 5, 8]);

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function ManagementPage() {
  const { data: allTenders, isLoading } = useActiveTenders();

  // Step 1: Filter to relevant tender types + purposes (main dataset)
  const filteredTenders: TenderWithComputed[] = useMemo(() => {
    if (!allTenders) return [];

    return allTenders.filter((t) => {
      if (!RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? -1)) return false;
      if (t.purpose && !RELEVANT_PURPOSES.has(t.purpose)) return false;
      return true;
    });
  }, [allTenders]);

  // Step 2: "All typed" tenders (type filter only, no purpose filter)
  // Used for closing-soon and category tabs -- matches Python _all_typed
  const allTypedActive: TenderWithComputed[] = useMemo(() => {
    if (!allTenders) return [];

    return allTenders.filter((t) =>
      RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? -1),
    );
  }, [allTenders]);

  // Step 3: Closing soon (from allTypedActive with purpose filter)
  const closingSoonTenders: TenderWithComputed[] = useMemo(() => {
    const purposeFiltered = allTypedActive.filter(
      (t) => !t.purpose || RELEVANT_PURPOSES.has(t.purpose),
    );
    return getClosingSoonTenders(purposeFiltered).sort((a, b) => {
      const da = a.days_to_deadline ?? Infinity;
      const db = b.days_to_deadline ?? Infinity;
      return da - db;
    });
  }, [allTypedActive]);

  // Step 4: Card-active tenders (types 1, 5, 8) for KPI section
  const cardActiveTenders: TenderWithComputed[] = useMemo(
    () =>
      filteredTenders.filter((t) =>
        CARD_TENDER_TYPES.has(t.tender_type_code ?? -1),
      ),
    [filteredTenders],
  );

  // Step 5: Bulk lot aggregation for card-active tenders
  const cardTenderIds = useMemo(
    () => cardActiveTenders.map((t) => t.tender_id),
    [cardActiveTenders],
  );
  const { data: lotMap } = useBulkLots(cardTenderIds);

  return (
    <div dir="rtl" className="space-y-6">
      <PageHeader
        title={"\u05DC\u05D5\u05D7 \u05D4\u05E0\u05D4\u05DC\u05D4"}
        subtitle={"\u05E1\u05E7\u05D9\u05E8\u05D4 \u05DB\u05DC\u05DC\u05D9\u05EA \u05DC\u05DE\u05E0\u05D4\u05DC\u05D9\u05DD \u2014 \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD, \u05E1\u05D8\u05D8\u05D5\u05E1 \u05E6\u05D5\u05D5\u05EA, \u05D5\u05DC\u05D5\u05D7\u05D5\u05EA \u05D6\u05DE\u05E0\u05D9\u05DD."}
      />

      {/* Section 1: Team Watchlist */}
      <TeamWatchlistSection />

      <Separator />

      {/* Section 2: Closing Soon (collapsible) */}
      <ClosingSoonSection
        tenders={closingSoonTenders}
        isLoading={isLoading}
      />

      <Separator />

      {/* Section 3: Market KPIs & Charts */}
      <MarketKPISection
        cardActiveTenders={cardActiveTenders}
        closingSoonCount={closingSoonTenders.length}
        lotMap={lotMap ?? {}}
      />

      <Separator />

      {/* Section 4: Category Tabs */}
      <CategoryTabsSection allActiveTenders={allTypedActive} />
    </div>
  );
}
