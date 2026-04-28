/**
 * ExpiredWatchlistSection for the Management page.
 *
 * Self-contained section showing watchlisted tenders that have expired
 * (forced_expired OR terminal status [2/4/5/7] OR deadline passed). Columns
 * mirror the top "מכרזים מועדפים - חדר עסקאות" table (cols 1-8 + הערות),
 * with the outcome columns (הגשנו?, ההצעה שלנו, הצעה זוכה, מיקום) appended
 * at the end. Rendered at the bottom of the management page.
 */
"use client";

import { useMemo } from "react";
import { type ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/data-table";
import { DeadlineBadge } from "@/components/deadline-badge";
import { useTeamWatchlist } from "@/hooks/use-watchlist";
import { useReviewStatuses } from "@/hooks/use-reviews";
import { useTenderOutcomes } from "@/hooks/use-outcomes";
import { useTenderPrices } from "@/hooks/use-prices";
import { useBulkLots, type LotAggregation } from "@/hooks/use-bulk-lots";
import { isExpiredTender } from "@/lib/utils/tenders";
import type { Tender, TenderPrice, WatchlistItemWithTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Helpers (mirrors team-watchlist-section.tsx)
// ---------------------------------------------------------------------------

function computeDays(deadline: string | null): number | null {
  if (!deadline) return null;
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return null;
  return Math.floor((d.getTime() - Date.now()) / 86_400_000);
}

function formatDateWithYear(date: string | null): string {
  if (!date) return "—";
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null || value === 0) return "—";
  return `₪${value.toLocaleString("he-IL", { maximumFractionDigits: 0 })}`;
}

function getCategoryLabel(tender: Tender | null): string {
  if (!tender) return "—";
  const purpose = tender.purpose ?? "";
  if (tender.tender_type_code === 9) return "ייזום";
  if (purpose.includes("דיור מוגן")) return "דיור מוגן";
  if (purpose.includes("דיור להשכרה") || tender.tender_type_code === 6) return "דיור להשכרה";
  if (tender.tender_type_code === 5 || tender.tender_type_code === 8) return "מחיר מטרה";
  return "שוק חופשי";
}

const EMPTY_LOT: LotAggregation = {
  free_market: 0,
  target_price: 0,
  total: 0,
  pct: "—",
};

// ---------------------------------------------------------------------------
// Row type + columns
// ---------------------------------------------------------------------------

interface ExpiredRow {
  tender_id: number;
  tender: Tender | null;
  review_status: string;
  watchlist_notes: string;
  days_to_deadline: number | null;
  lot_agg: LotAggregation;
  did_bid: boolean;
  our_offer: number | null;
  winning_bid: number | null;
  our_position: number | null;
}

const columns: ColumnDef<ExpiredRow, unknown>[] = [
  {
    id: "deadline",
    header: "מועד סגירה",
    accessorFn: (row) => row.days_to_deadline ?? Infinity,
    sortingFn: "basic",
    size: 100,
    cell: ({ row }) => {
      const t = row.original.tender;
      return (
        <div className="flex items-center gap-1.5 whitespace-nowrap">
          <DeadlineBadge daysRemaining={row.original.days_to_deadline} compact />
          <span className="text-sm">{formatDateWithYear(t?.deadline ?? null)}</span>
        </div>
      );
    },
  },
  {
    id: "publish_date",
    header: "תאריך פרסום",
    size: 80,
    cell: ({ row }) => (
      <span className="text-sm whitespace-nowrap">
        {formatDateWithYear(row.original.tender?.publish_date ?? null)}
      </span>
    ),
  },
  {
    id: "city",
    header: "עיר",
    size: 80,
    cell: ({ row }) => (
      <span className="truncate block max-w-[80px]">
        {row.original.tender?.city ?? "—"}
      </span>
    ),
  },
  {
    id: "tender_type",
    header: "סוג",
    size: 90,
    cell: ({ row }) => (
      <span className="truncate block max-w-[90px]">
        {getCategoryLabel(row.original.tender)}
      </span>
    ),
  },
  {
    id: "booklet",
    header: "חוברת",
    size: 55,
    cell: ({ row }) =>
      row.original.tender?.published_booklet ? "✅" : "❌",
  },
  {
    id: "units",
    header: 'יח"ד',
    size: 60,
    cell: ({ row }) =>
      row.original.lot_agg.total || row.original.tender?.units || "—",
  },
  {
    id: "pct_target",
    header: "% מחיר מטרה",
    size: 70,
    cell: ({ row }) => row.original.lot_agg.pct,
  },
  {
    accessorKey: "review_status",
    header: "סטטוס",
    size: 80,
    cell: ({ getValue }) => (
      <span className="text-sm">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "watchlist_notes",
    header: "הערות",
    size: 120,
    cell: ({ getValue }) => (
      <span className="text-xs text-megido-text-muted line-clamp-2">
        {getValue<string>() || "—"}
      </span>
    ),
  },
  {
    id: "did_bid",
    header: "הגשנו?",
    cell: ({ row }) => (
      <span className="text-sm">{row.original.did_bid ? "✅" : "—"}</span>
    ),
  },
  {
    id: "our_offer",
    header: "ההצעה שלנו",
    cell: ({ row }) => (
      <span className="text-sm">{formatCurrency(row.original.our_offer)}</span>
    ),
  },
  {
    id: "winning_bid",
    header: "הצעה זוכה",
    cell: ({ row }) => (
      <span className="text-sm font-semibold text-emerald-600">
        {formatCurrency(row.original.winning_bid)}
      </span>
    ),
  },
  {
    id: "position",
    header: "מיקום",
    cell: ({ row }) => (
      <span className="text-sm">{row.original.our_position ?? "—"}</span>
    ),
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ExpiredWatchlistSection() {
  const { data: watchlistItems } = useTeamWatchlist();

  // Get all tender IDs for sub-queries
  const allTenderIds = useMemo(
    () =>
      (watchlistItems ?? [])
        .filter((item): item is WatchlistItemWithTender & { tender: Tender } =>
          item.tender != null,
        )
        .map((item) => item.tender_id),
    [watchlistItems],
  );

  const { data: reviewMap } = useReviewStatuses(allTenderIds);
  const { data: outcomeMap } = useTenderOutcomes(allTenderIds);
  const { data: lotMap } = useBulkLots(allTenderIds);
  const { data: allPrices } = useTenderPrices();

  // Filter to expired only
  const expiredItems = useMemo(() => {
    if (!watchlistItems) return [];
    return watchlistItems.filter(
      (item): item is WatchlistItemWithTender & { tender: Tender } =>
        item.tender != null && isExpiredTender(item.tender, outcomeMap?.[item.tender_id]),
    );
  }, [watchlistItems, outcomeMap]);

  // Group prices by tender
  const pricesByTender = useMemo(() => {
    if (!allPrices) return {} as Record<number, TenderPrice[]>;
    const map: Record<number, TenderPrice[]> = {};
    for (const p of allPrices) {
      if (!map[p.tender_id]) map[p.tender_id] = [];
      map[p.tender_id].push(p);
    }
    return map;
  }, [allPrices]);

  // Build rows
  const rows: ExpiredRow[] = useMemo(() => {
    return expiredItems.map((item) => {
      const tid = item.tender_id;
      const review = reviewMap?.[tid];
      const outcome = outcomeMap?.[tid];
      const prices = pricesByTender[tid] ?? [];
      const winBid = prices.find((p) => p.winning_bid != null && p.winning_bid > 0)?.winning_bid ?? null;

      return {
        tender_id: tid,
        tender: item.tender,
        review_status: review?.status ?? "לא נסקר",
        watchlist_notes: item.notes ?? "",
        days_to_deadline: computeDays(item.tender.deadline),
        lot_agg: lotMap?.[tid] ?? EMPTY_LOT,
        did_bid: outcome?.did_bid ?? false,
        our_offer: outcome?.our_offer ?? null,
        winning_bid: winBid,
        our_position: outcome?.our_position ?? null,
      };
    });
  }, [expiredItems, reviewMap, outcomeMap, lotMap, pricesByTender]);

  if (rows.length === 0) return null;

  return (
    <section>
      <h3 className="mb-3 text-lg font-semibold text-megido-text-heading">
        {"מכרזים שהוסרו ממועדפים"} ({rows.length})
      </h3>
      <DataTable
        columns={columns}
        data={rows}
        isLoading={false}
        pageSize={10}
        emptyMessage=""
      />
    </section>
  );
}
