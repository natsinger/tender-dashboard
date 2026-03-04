/**
 * Explorer page (סייר מכרזים).
 *
 * Full-featured tender data table with 4-column filters (city, region,
 * purpose, status), scoring, sortable columns, single-row selection
 * triggering a detail panel, and CSV export.
 *
 * Mirrors the Streamlit pages/explorer.py layout:
 *   1. PageHeader with title and date
 *   2. FilterBar (city, region, purpose, status multiselects)
 *   3. ExplorerTable with scored tenders
 *   4. DetailViewer (expandable)
 *   5. CSV export button
 */
"use client";

import { useMemo, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { FilterBar } from "@/components/filter-bar";
import { ExplorerTable } from "@/components/explorer/explorer-table";
import { DetailViewer } from "@/components/explorer/detail-viewer";
import { CsvExport } from "@/components/explorer/csv-export";
import { useActiveTenders } from "@/hooks/use-tenders";
import { useFilterStore } from "@/stores/filter-store";
import { RELEVANT_TENDER_TYPES } from "@/lib/constants";
import { scoreAllTenders } from "@/lib/utils/tenders";
import type { ScoredTender, TenderWithComputed } from "@/types/database";

// ---------------------------------------------------------------------------
// Constants (mirrors Python explorer.py RELEVANT_PURPOSES)
// ---------------------------------------------------------------------------

const RELEVANT_PURPOSES = new Set([
  "\u05D1\u05E0\u05D9\u05D9\u05D4 \u05E8\u05D5\u05D5\u05D9\u05D4",
  "\u05D1\u05E0\u05D9\u05D9\u05D4 \u05E0\u05DE\u05D5\u05DB\u05D4/\u05E6\u05DE\u05D5\u05D3\u05EA \u05E7\u05E8\u05E7\u05E2",
  "\u05DE\u05D2\u05D5\u05E8\u05D9\u05DD/\u05DE\u05E1\u05D7\u05E8/\u05DE\u05DC\u05D5\u05E0\u05D0\u05D5\u05EA/\u05E0\u05D5\u05E4\u05E9",
  "\u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF (\u05D1\u05D9\u05EA \u05D0\u05D1\u05D5\u05EA)",
  "\u05D0\u05D7\u05E8",
]);

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function ExplorerPage() {
  const { data: allTenders, isLoading } = useActiveTenders();
  const filters = useFilterStore();

  const [selectedTender, setSelectedTender] = useState<ScoredTender | null>(
    null,
  );

  // Step 1: Pre-filter by tender type and purpose (matches Python explorer.py)
  const baseTenders: TenderWithComputed[] = useMemo(() => {
    if (!allTenders) return [];

    return allTenders.filter((t) => {
      if (!RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? -1)) return false;
      if (t.purpose && !RELEVANT_PURPOSES.has(t.purpose)) return false;
      return true;
    });
  }, [allTenders]);

  // Step 2: Apply user filters from the FilterBar / Zustand store
  const filteredTenders: TenderWithComputed[] = useMemo(() => {
    let result = baseTenders;

    if (filters.cities.length > 0) {
      const set = new Set(filters.cities);
      result = result.filter((t) => t.city != null && set.has(t.city));
    }
    if (filters.regions.length > 0) {
      const set = new Set(filters.regions);
      result = result.filter((t) => t.region != null && set.has(t.region));
    }
    if (filters.purposes.length > 0) {
      const set = new Set(filters.purposes);
      result = result.filter((t) => t.purpose != null && set.has(t.purpose));
    }
    if (filters.statuses.length > 0) {
      const set = new Set(filters.statuses);
      result = result.filter((t) => t.status != null && set.has(t.status));
    }

    return result;
  }, [baseTenders, filters.cities, filters.regions, filters.purposes, filters.statuses]);

  // Step 3: Score all tenders
  const scoredTenders: ScoredTender[] = useMemo(
    () => scoreAllTenders(filteredTenders),
    [filteredTenders],
  );

  // Step 4: Extract unique filter options from the base set
  // (so changing one filter does not remove options from other dropdowns)
  const filterOptions = useMemo(() => {
    const cities = new Set<string>();
    const regions = new Set<string>();
    const purposes = new Set<string>();
    const statuses = new Set<string>();

    for (const t of baseTenders) {
      if (t.city) cities.add(t.city);
      if (t.region) regions.add(t.region);
      if (t.purpose) purposes.add(t.purpose);
      if (t.status) statuses.add(t.status);
    }

    return {
      cities: [...cities].sort(),
      regions: [...regions].sort(),
      purposes: [...purposes].sort(),
      statuses: [...statuses].sort(),
    };
  }, [baseTenders]);

  return (
    <div className="space-y-4">
      <PageHeader
        title={"\u05E1\u05D9\u05D9\u05E8 \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD"}
      />

      <FilterBar
        cities={filterOptions.cities}
        regions={filterOptions.regions}
        purposes={filterOptions.purposes}
        statuses={filterOptions.statuses}
      />

      <div className="flex items-center justify-end">
        <CsvExport data={scoredTenders} />
      </div>

      <ExplorerTable
        data={scoredTenders}
        isLoading={isLoading}
        onRowSelect={setSelectedTender}
        selectedId={selectedTender?.tender_id ?? null}
      />

      <DetailViewer
        tenders={filteredTenders}
        selectedTender={selectedTender}
        autoExpand={false}
      />
    </div>
  );
}
