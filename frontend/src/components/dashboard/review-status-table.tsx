/**
 * ReviewStatusTable component.
 *
 * Row 3 of the dashboard: read-only table showing the team watchlist
 * with review statuses. Columns: tender name, units, city, type,
 * review status, and notes. Editing is done from the sidebar.
 *
 * Mirrors the Streamlit ROW 3 section from pages/dashboard.py.
 */
"use client";

import { useMemo } from "react";
import { type ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/data-table";
import { useTeamWatchlist, useReviewStatuses } from "@/hooks";
import type { Tender, WatchlistItemWithTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Row type
// ---------------------------------------------------------------------------

interface ReviewRow {
  tender_id: number;
  tender_name: string;
  units: number | null;
  city: string;
  tender_type: string;
  review_status: string;
  notes: string;
}

// ---------------------------------------------------------------------------
// Column definitions
// ---------------------------------------------------------------------------

const columns: ColumnDef<ReviewRow, unknown>[] = [
  {
    accessorKey: "tender_name",
    header: "\u05DE\u05DB\u05E8\u05D6",
    cell: ({ getValue }) => (
      <span className="text-sm font-medium">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "units",
    header: '\u05D9\u05D7"\u05D3',
    cell: ({ getValue }) => {
      const v = getValue<number | null>();
      return v != null && v > 0 ? v : "\u2014";
    },
  },
  {
    accessorKey: "city",
    header: "\u05E2\u05D9\u05E8",
    cell: ({ getValue }) => getValue<string>() || "\u2014",
  },
  {
    accessorKey: "tender_type",
    header: "\u05E1\u05D5\u05D2",
    cell: ({ getValue }) => getValue<string>() || "\u2014",
  },
  {
    accessorKey: "review_status",
    header: "\u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4",
    cell: ({ getValue }) => (
      <span className="text-sm">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "notes",
    header: "\u05D4\u05E2\u05E8\u05D5\u05EA",
    cell: ({ getValue }) => (
      <span className="text-xs text-megido-text-muted">
        {getValue<string>() || "\u2014"}
      </span>
    ),
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ReviewStatusTable() {
  const {
    data: watchlistItems,
    isLoading: wlLoading,
    isError: wlError,
    refetch: refetchWl,
  } = useTeamWatchlist();

  // Get tender IDs for review status lookup
  const tenderIds = useMemo(
    () =>
      (watchlistItems ?? [])
        .filter(
          (item): item is WatchlistItemWithTender & { tender: Tender } =>
            item.tender != null,
        )
        .map((item) => item.tender_id),
    [watchlistItems],
  );

  const {
    data: reviewMap,
    isLoading: reviewLoading,
    isError: reviewError,
    refetch: refetchReviews,
  } = useReviewStatuses(tenderIds);

  const isLoading = wlLoading || reviewLoading;
  const isError = wlError || reviewError;

  // Build table rows
  const rows: ReviewRow[] = useMemo(() => {
    if (!watchlistItems) return [];

    return watchlistItems
      .filter(
        (item): item is WatchlistItemWithTender & { tender: Tender } =>
          item.tender != null,
      )
      .map((item) => {
        const tid = item.tender_id;
        const review = reviewMap?.[tid];

        return {
          tender_id: tid,
          tender_name: item.tender.tender_name ?? "",
          units: item.tender.units,
          city: item.tender.city ?? "",
          tender_type: item.tender.tender_type ?? "",
          review_status:
            review?.status ?? "\u05DC\u05D0 \u05E0\u05E1\u05E7\u05E8",
          notes: review?.notes ?? "",
        };
      });
  }, [watchlistItems, reviewMap]);

  if (isError) {
    return (
      <section dir="rtl">
        <h3 className="mb-2 text-base font-semibold text-megido-text-heading">
          {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD - \u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4"}
        </h3>
        <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm font-medium text-red-700">
            {"שגיאה בטעינת הנתונים"}
          </p>
          <button
            type="button"
            onClick={() => {
              void refetchWl();
              void refetchReviews();
            }}
            className="rounded-md bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-200"
          >
            {"נסה שוב"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section dir="rtl">
      <h3 className="mb-2 text-base font-semibold text-megido-text-heading">
        {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD - \u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4"}
      </h3>

      {isLoading ? (
        <DataTable columns={columns} data={[]} isLoading emptyMessage="" />
      ) : rows.length > 0 ? (
        <DataTable
          columns={columns}
          data={rows}
          pageSize={10}
          emptyMessage={"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD."}
        />
      ) : (
        <p className="py-4 text-sm text-megido-text-muted">
          {"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD. \u05D4\u05D5\u05E1\u05E3 \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05D3\u05E8\u05DA \u05D4\u05EA\u05E4\u05E8\u05D9\u05D8 \u05D4\u05E6\u05D3\u05D3\u05D9 \u2190"}
        </p>
      )}
    </section>
  );
}
