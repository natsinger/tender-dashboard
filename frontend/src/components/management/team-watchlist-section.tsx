/**
 * TeamWatchlistSection component for the Management page.
 *
 * Displays the shared team watchlist table with review statuses,
 * lot aggregation data, deadline badges, brochure toggles, and
 * click-to-open tender detail modal. Mirrors Section 1 of the
 * Streamlit management.py page.
 */
"use client";

import { useState, useMemo } from "react";
import { type ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/data-table";
import { BrochureToggle, type BrochureFilter } from "@/components/brochure-toggle";
import { DeadlineBadge } from "@/components/deadline-badge";
import { TenderDetailModal } from "@/components/tender-detail-modal";
import { useTeamWatchlist } from "@/hooks/use-watchlist";
import { useReviewStatuses } from "@/hooks/use-reviews";
import { useBulkLots, type LotAggregation } from "@/hooks/use-bulk-lots";
import { useTenderLots, useTenderBuildingRights } from "@/hooks/use-lots";
import type { Tender, WatchlistItemWithTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Row type for the watchlist table
// ---------------------------------------------------------------------------

interface WatchlistRow {
  tender_id: number;
  tender: Tender | null;
  review_status: string;
  review_notes: string;
  watchlist_notes: string;
  days_to_deadline: number | null;
  lot_agg: LotAggregation;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function computeDays(deadline: string | null): number | null {
  if (!deadline) return null;
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return null;
  return Math.floor((d.getTime() - Date.now()) / 86_400_000);
}

function formatDeadline(deadline: string | null): string {
  if (!deadline) return "\u2014";
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return "\u2014";
  return d.toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit" });
}

// ---------------------------------------------------------------------------
// Empty lot aggregation constant
// ---------------------------------------------------------------------------

const EMPTY_LOT: LotAggregation = {
  free_market: 0,
  target_price: 0,
  total: 0,
  pct: "\u2014",
};

// ---------------------------------------------------------------------------
// Column definitions
// ---------------------------------------------------------------------------

const columns: ColumnDef<WatchlistRow, unknown>[] = [
  {
    accessorKey: "review_status",
    header: "\u05E1\u05D8\u05D8\u05D5\u05E1",
    cell: ({ getValue }) => (
      <span className="text-sm">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "review_notes",
    header: "\u05D4\u05E2\u05E8\u05D5\u05EA \u05E6\u05D5\u05D5\u05EA",
    cell: ({ getValue }) => (
      <span className="text-xs text-slate-500">
        {getValue<string>() || "\u2014"}
      </span>
    ),
  },
  {
    id: "booklet",
    header: "\u05D7\u05D5\u05D1\u05E8\u05EA",
    cell: ({ row }) =>
      row.original.tender?.published_booklet ? "\u2705" : "\u274C",
  },
  {
    id: "tender_name",
    header: "\u05DE\u05E1\u05E4\u05E8 \u05DE\u05DB\u05E8\u05D6",
    cell: ({ row }) => (
      <span className="text-sm font-medium">
        {row.original.tender?.tender_name ?? row.original.tender_id}
      </span>
    ),
  },
  {
    id: "city",
    header: "\u05E2\u05D9\u05E8",
    cell: ({ row }) => row.original.tender?.city ?? "\u2014",
  },
  {
    id: "tender_type",
    header: "\u05E1\u05D5\u05D2",
    cell: ({ row }) => row.original.tender?.tender_type ?? "\u2014",
  },
  {
    id: "units",
    header: '\u05D9\u05D7"\u05D3',
    cell: ({ row }) => row.original.tender?.units ?? "\u2014",
  },
  {
    id: "deadline",
    header: "\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4",
    cell: ({ row }) => {
      const t = row.original.tender;
      return (
        <div className="flex items-center gap-1.5 whitespace-nowrap">
          <DeadlineBadge
            daysRemaining={row.original.days_to_deadline}
            compact
          />
          <span className="text-sm">
            {formatDeadline(t?.deadline ?? null)}
          </span>
        </div>
      );
    },
  },
  {
    id: "free_market",
    header: "\u05E9\u05D5\u05E7 \u05D7\u05D5\u05E4\u05E9\u05D9",
    cell: ({ row }) => row.original.lot_agg.free_market || "\u2014",
  },
  {
    id: "target_price",
    header: "\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4",
    cell: ({ row }) => row.original.lot_agg.target_price || "\u2014",
  },
  {
    id: "total_lot_units",
    header: '\u05E1\u05D4"\u05DB',
    cell: ({ row }) => row.original.lot_agg.total || "\u2014",
  },
  {
    id: "pct_target",
    header: "% \u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4",
    cell: ({ row }) => row.original.lot_agg.pct,
  },
  {
    accessorKey: "watchlist_notes",
    header: "\u05D4\u05E2\u05E8\u05D5\u05EA",
    cell: ({ getValue }) => (
      <span className="text-xs text-slate-500">
        {getValue<string>() || "\u2014"}
      </span>
    ),
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TeamWatchlistSection() {
  const { data: watchlistItems, isLoading: watchlistLoading } =
    useTeamWatchlist();

  // Derive tender IDs for sub-queries
  const tenderIds = useMemo(
    () =>
      (watchlistItems ?? [])
        .filter((item): item is WatchlistItemWithTender & { tender: Tender } =>
          item.tender != null,
        )
        .map((item) => item.tender_id),
    [watchlistItems],
  );

  const { data: reviewMap } = useReviewStatuses(tenderIds);
  const { data: lotMap } = useBulkLots(tenderIds);

  // Brochure filter
  const [brochureFilter, setBrochureFilter] =
    useState<BrochureFilter>("all");

  // Modal state
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Lot and building rights for the modal
  const { data: modalLots } = useTenderLots(selectedTender?.tender_id);
  const { data: modalBuildingRights } = useTenderBuildingRights(
    selectedTender?.tender_id,
  );

  // Build table rows
  const rows: WatchlistRow[] = useMemo(() => {
    if (!watchlistItems) return [];

    let items = watchlistItems.filter(
      (item): item is WatchlistItemWithTender & { tender: Tender } =>
        item.tender != null,
    );

    // Brochure filter
    if (brochureFilter === "with_brochure") {
      items = items.filter((item) => Boolean(item.tender.published_booklet));
    }

    return items.map((item) => {
      const tid = item.tender_id;
      const review = reviewMap?.[tid];
      const days = computeDays(item.tender.deadline);

      return {
        tender_id: tid,
        tender: item.tender,
        review_status: review?.status ?? "\u05DC\u05D0 \u05E0\u05E1\u05E7\u05E8",
        review_notes: review?.notes ?? "",
        watchlist_notes: item.notes ?? "",
        days_to_deadline: days,
        lot_agg: lotMap?.[tid] ?? EMPTY_LOT,
      };
    });
  }, [watchlistItems, reviewMap, lotMap, brochureFilter]);

  // Row click handler
  const handleRowSelect = (row: WatchlistRow | null) => {
    if (row?.tender) {
      setSelectedTender(row.tender);
      setModalOpen(true);
    }
  };

  return (
    <section>
      <h4 className="mb-3 text-lg font-semibold text-slate-800">
        {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD - \u05D7\u05D3\u05E8 \u05E2\u05E1\u05E7\u05D0\u05D5\u05EA"}
      </h4>

      {(watchlistItems ?? []).length > 0 ? (
        <>
          <BrochureToggle
            value={brochureFilter}
            onChange={setBrochureFilter}
            className="mb-3"
          />
          <DataTable
            columns={columns}
            data={rows}
            isLoading={watchlistLoading}
            enableSelection
            onRowSelect={handleRowSelect}
            pageSize={20}
            emptyMessage={"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD."}
          />
        </>
      ) : watchlistLoading ? (
        <DataTable
          columns={columns}
          data={[]}
          isLoading
          emptyMessage=""
        />
      ) : (
        <p className="py-4 text-sm text-slate-500">
          {"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD. \u05D4\u05D5\u05E1\u05E3 \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05D3\u05E8\u05DA \u05D3\u05D0\u05E9\u05D1\u05D5\u05E8\u05D3 \u05D7\u05D3\u05E8 \u05D4\u05E2\u05E1\u05E7\u05D0\u05D5\u05EA."}
        </p>
      )}

      <TenderDetailModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        tender={selectedTender}
        lots={modalLots}
        buildingRights={modalBuildingRights}
      />
    </section>
  );
}
