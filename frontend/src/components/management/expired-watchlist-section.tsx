/**
 * ExpiredWatchlistSection for the Management page.
 *
 * Self-contained section showing watchlisted tenders that have expired
 * (forced_expired OR deadline passed + results published). Displays
 * outcome data (did we bid, our offer, winning bid, position, notes).
 * Rendered at the bottom of the management page.
 */
"use client";

import { useMemo } from "react";
import { type ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { useTeamWatchlist } from "@/hooks/use-watchlist";
import { useReviewStatuses } from "@/hooks/use-reviews";
import { useTenderOutcomes } from "@/hooks/use-outcomes";
import { useTenderPrices } from "@/hooks/use-prices";
import { isExpiredTender } from "@/lib/utils/tenders";
import type { Tender, TenderPrice, WatchlistItemWithTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDateWithYear(date: string | null): string {
  if (!date) return "\u2014";
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return "\u2014";
  return d.toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null || value === 0) return "\u2014";
  return `\u20AA${value.toLocaleString("he-IL", { maximumFractionDigits: 0 })}`;
}

function getReviewBadgeVariant(
  status: string,
): "default" | "secondary" | "outline" {
  if (status.includes("\u05D0\u05D5\u05E9\u05E8")) return "default";
  if (status.includes("\u05D4\u05D5\u05E6\u05D2") || status.includes("\u05D1\u05D3\u05D9\u05E7\u05D4")) return "secondary";
  return "outline";
}

// ---------------------------------------------------------------------------
// Row type + columns
// ---------------------------------------------------------------------------

interface ExpiredRow {
  tender_id: number;
  tender: Tender | null;
  review_status: string;
  did_bid: boolean;
  our_offer: number | null;
  winning_bid: number | null;
  our_position: number | null;
  outcome_notes: string;
}

const columns: ColumnDef<ExpiredRow, unknown>[] = [
  {
    id: "tender_name",
    header: "\u05E9\u05DD \u05DE\u05DB\u05E8\u05D6",
    cell: ({ row }) => (
      <span className="text-sm font-medium truncate block max-w-[180px]">
        {row.original.tender?.tender_name ?? row.original.tender_id}
      </span>
    ),
  },
  {
    id: "city",
    header: "\u05E2\u05D9\u05E8",
    cell: ({ row }) => (
      <span className="text-sm">{row.original.tender?.city ?? "\u2014"}</span>
    ),
  },
  {
    id: "units",
    header: '\u05D9\u05D7"\u05D3',
    cell: ({ row }) => (
      <span className="text-sm">{row.original.tender?.units ?? "\u2014"}</span>
    ),
  },
  {
    id: "purpose",
    header: "\u05E1\u05D5\u05D2",
    cell: ({ row }) => (
      <span className="text-sm truncate block max-w-[90px]">
        {row.original.tender?.purpose ?? "\u2014"}
      </span>
    ),
  },
  {
    id: "deadline",
    header: "\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4",
    cell: ({ row }) => (
      <span className="text-sm">{formatDateWithYear(row.original.tender?.deadline ?? null)}</span>
    ),
  },
  {
    id: "review_status",
    header: "\u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4",
    cell: ({ row }) => (
      <Badge variant={getReviewBadgeVariant(row.original.review_status)} className="text-[0.64rem]">
        {row.original.review_status}
      </Badge>
    ),
  },
  {
    id: "notes",
    header: "\u05D4\u05E2\u05E8\u05D5\u05EA",
    cell: ({ row }) => (
      <span className="text-xs text-megido-text-muted line-clamp-2">
        {row.original.outcome_notes || "\u2014"}
      </span>
    ),
  },
  {
    id: "did_bid",
    header: "\u05D4\u05D2\u05E9\u05E0\u05D5?",
    cell: ({ row }) => (
      <span className="text-sm">{row.original.did_bid ? "\u2705" : "\u2014"}</span>
    ),
  },
  {
    id: "our_offer",
    header: "\u05D4\u05D4\u05E6\u05E2\u05D4 \u05E9\u05DC\u05E0\u05D5",
    cell: ({ row }) => (
      <span className="text-sm">{formatCurrency(row.original.our_offer)}</span>
    ),
  },
  {
    id: "winning_bid",
    header: "\u05D4\u05E6\u05E2\u05D4 \u05D6\u05D5\u05DB\u05D4",
    cell: ({ row }) => (
      <span className="text-sm font-semibold text-emerald-600">{formatCurrency(row.original.winning_bid)}</span>
    ),
  },
  {
    id: "position",
    header: "\u05DE\u05D9\u05E7\u05D5\u05DD",
    cell: ({ row }) => (
      <span className="text-sm">{row.original.our_position ?? "\u2014"}</span>
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
        review_status: review?.status ?? "\u05DC\u05D0 \u05E0\u05E1\u05E7\u05E8",
        did_bid: outcome?.did_bid ?? false,
        our_offer: outcome?.our_offer ?? null,
        winning_bid: winBid,
        our_position: outcome?.our_position ?? null,
        outcome_notes: outcome?.outcome_notes ?? "",
      };
    });
  }, [expiredItems, reviewMap, outcomeMap, pricesByTender]);

  if (rows.length === 0) return null;

  return (
    <section>
      <h3 className="mb-3 text-lg font-semibold text-megido-text-heading">
        {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05D4\u05D5\u05E1\u05E8\u05D5 \u05DE\u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD"} ({rows.length})
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
