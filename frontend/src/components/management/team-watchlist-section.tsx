/**
 * TeamWatchlistSection component for the Management page.
 *
 * Displays the shared team watchlist table with review statuses,
 * lot aggregation data, deadline badges, brochure toggles, and
 * click-to-open tender detail modal. Mirrors Section 1 of the
 * Streamlit management.py page.
 */
"use client";

import { useState, useMemo, useCallback } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { Download } from "lucide-react";
import * as XLSX from "xlsx";

import { DataTable } from "@/components/data-table";
import { BrochureToggle, type BrochureFilter } from "@/components/brochure-toggle";
import { DeadlineBadge } from "@/components/deadline-badge";
import { GovMapLink } from "@/components/govmap-link";
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

/** Derive a short category label from purpose + tender_type_code. */
function getCategoryLabel(tender: Tender | null): string {
  if (!tender) return "\u2014";
  const purpose = tender.purpose ?? "";
  if (tender.tender_type_code === 9) return "ייזום";
  if (purpose.includes("דיור מוגן")) return "דיור מוגן";
  if (purpose.includes("דיור להשכרה") || tender.tender_type_code === 6) return "דיור להשכרה";
  return "שוק חופשי";
}

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
    id: "deadline",
    header: "\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4",
    accessorFn: (row) => row.days_to_deadline ?? Infinity,
    sortingFn: "basic",
    size: 100,
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
    id: "city",
    header: "\u05E2\u05D9\u05E8",
    size: 80,
    cell: ({ row }) => (
      <span className="truncate block max-w-[80px]">
        {row.original.tender?.city ?? "\u2014"}
      </span>
    ),
  },
  {
    id: "tender_type",
    header: "\u05E1\u05D5\u05D2",
    size: 90,
    cell: ({ row }) => (
      <span className="truncate block max-w-[90px]">
        {getCategoryLabel(row.original.tender)}
      </span>
    ),
  },
  {
    id: "booklet",
    header: "\u05D7\u05D5\u05D1\u05E8\u05EA",
    size: 55,
    cell: ({ row }) =>
      row.original.tender?.published_booklet ? "\u2705" : "\u274C",
  },
  {
    id: "units",
    header: '\u05D9\u05D7"\u05D3',
    size: 60,
    cell: ({ row }) => row.original.lot_agg.total || row.original.tender?.units || "\u2014",
  },
  {
    id: "pct_target",
    header: "% \u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4",
    size: 70,
    cell: ({ row }) => row.original.lot_agg.pct,
  },
  {
    accessorKey: "review_status",
    header: "\u05E1\u05D8\u05D8\u05D5\u05E1",
    size: 80,
    cell: ({ getValue }) => (
      <span className="text-sm">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "review_notes",
    header: "\u05D4\u05E2\u05E8\u05D5\u05EA \u05E6\u05D5\u05D5\u05EA",
    size: 110,
    cell: ({ getValue }) => (
      <span className="text-xs text-megido-text-muted line-clamp-2">
        {getValue<string>() || "\u2014"}
      </span>
    ),
  },
  {
    accessorKey: "watchlist_notes",
    header: "\u05D4\u05E2\u05E8\u05D5\u05EA",
    size: 120,
    cell: ({ getValue }) => (
      <span className="text-xs text-megido-text-muted line-clamp-2">
        {getValue<string>() || "\u2014"}
      </span>
    ),
  },
  {
    id: "govmap",
    header: "תב\"ע",
    size: 50,
    cell: ({ row }) => <GovMapLink tender={row.original.tender} />,
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
  const handleRowClick = (row: WatchlistRow) => {
    if (row.tender) {
      setSelectedTender(row.tender);
      setModalOpen(true);
    }
  };

  // Export to Excel
  const exportToExcel = useCallback(() => {
    const xlsRows = rows.map((r) => {
      const t = r.tender;
      return {
        "\u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4": r.review_status,
        "\u05D4\u05E2\u05E8\u05D5\u05EA \u05E6\u05D5\u05D5\u05EA": r.review_notes || "",
        "\u05D7\u05D5\u05D1\u05E8\u05EA": t?.published_booklet ? "\u05DB\u05DF" : "\u05DC\u05D0",
        "\u05DE\u05E1\u05E4\u05E8 \u05DE\u05DB\u05E8\u05D6": t?.tender_name ?? r.tender_id,
        "\u05E2\u05D9\u05E8": t?.city ?? "",
        "\u05E1\u05D5\u05D2 \u05DE\u05DB\u05E8\u05D6": t?.tender_type ?? "",
        "\u05D9\u05D9\u05E2\u05D5\u05D3": t?.purpose ?? "",
        '\u05D9\u05D7"\u05D3': t?.units ?? "",
        "\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4": t?.deadline ?? "",
        "\u05E9\u05D5\u05E7 \u05D7\u05D5\u05E4\u05E9\u05D9": r.lot_agg.free_market || "",
        "\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4": r.lot_agg.target_price || "",
        '\u05E1\u05D4"\u05DB \u05DE\u05D2\u05E8\u05E9\u05D9\u05DD': r.lot_agg.total || "",
        "% \u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4": r.lot_agg.pct,
        "\u05D4\u05E2\u05E8\u05D5\u05EA": r.watchlist_notes || "",
        "\u05DE\u05D7\u05D5\u05D6": t?.region ?? "",
        "\u05DE\u05D9\u05E7\u05D5\u05DD": t?.location ?? "",
        '\u05E9\u05D8\u05D7 (\u05DE"\u05E8)': t?.area_sqm ?? "",
        "\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D9\u05E0\u05D9\u05DE\u05D5\u05DD": t?.min_price ?? "",
        "\u05EA\u05D0\u05E8\u05D9\u05DA \u05E4\u05E8\u05E1\u05D5\u05DD": t?.publish_date ?? "",
        "\u05EA\u05DB\u05E0\u05D9\u05EA": t?.plan_number ?? "",
        "\u05DE\u05E1\u05F3 \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD": t?.lot_count ?? "",
      };
    });

    const ws = XLSX.utils.json_to_sheet(xlsRows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "\u05D7\u05D3\u05E8 \u05E2\u05E1\u05E7\u05D0\u05D5\u05EA");

    const today = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(wb, `watchlist_${today}.xls`, { bookType: "xls" });
  }, [rows]);

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-lg font-semibold text-megido-text-heading">
          {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD - \u05D7\u05D3\u05E8 \u05E2\u05E1\u05E7\u05D0\u05D5\u05EA"}
        </h4>
        <button
          type="button"
          onClick={exportToExcel}
          disabled={rows.length === 0}
          className="flex items-center gap-1.5 rounded-lg border border-megido-border px-3 py-1.5 text-xs font-medium text-megido-text-heading transition-colors hover:bg-megido-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Download className="h-3.5 w-3.5" />
          {"\u05D9\u05D9\u05E6\u05D5\u05D0 \u05DC\u05D0\u05E7\u05E1\u05DC"}
        </button>
      </div>

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
            onRowClick={handleRowClick}
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
        <p className="py-4 text-sm text-megido-text-muted">
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
