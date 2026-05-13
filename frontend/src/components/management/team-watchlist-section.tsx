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
import { ChevronDown, ChevronUp, Download, Layers } from "lucide-react";
import * as XLSX from "xlsx";

import { DataTable } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { BrochureToggle, type BrochureFilter } from "@/components/brochure-toggle";
import { DeadlineBadge } from "@/components/deadline-badge";
import { GovMapLink } from "@/components/govmap-link";
import { TenderDetailModal } from "@/components/tender-detail-modal";
import { Separator } from "@/components/ui/separator";
import { useTeamWatchlist } from "@/hooks/use-watchlist";
import { useReviewStatuses } from "@/hooks/use-reviews";
import { useTenderOutcomes } from "@/hooks/use-outcomes";
import { useBulkLots, type LotAggregation } from "@/hooks/use-bulk-lots";
import { useTenderLots, useTenderBuildingRights } from "@/hooks/use-lots";
import { isExpiredTender } from "@/lib/utils/tenders";
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
  if (!deadline) return "—";
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit" });
}

function formatDateWithYear(date: string | null): string {
  if (!date) return "—";
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

// ---------------------------------------------------------------------------
// Empty lot aggregation constant
// ---------------------------------------------------------------------------

/** Derive a short category label from purpose + tender_type_code. */
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
// Category display order for grouped view
// ---------------------------------------------------------------------------

const CATEGORY_ORDER = [
  "שוק חופשי",
  "מחיר מטרה",
  "דיור להשכרה",
  "דיור מוגן",
  "ייזום",
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TeamWatchlistSection() {
  const { data: watchlistItems, isLoading: watchlistLoading } =
    useTeamWatchlist();

  // Group-by-type state (toggled by clicking the "סוג" column header)
  const [groupByType, setGroupByType] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = useCallback((cat: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }, []);

  // Column definitions — defined inside the component so the "סוג"
  // header can close over groupByType state.
  const columns = useMemo<ColumnDef<WatchlistRow, unknown>[]>(
    () => [
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
              <DeadlineBadge
                daysRemaining={row.original.days_to_deadline}
                compact
              />
              <span className="text-sm">
                {formatDateWithYear(t?.deadline ?? null)}
              </span>
            </div>
          );
        },
      },
      {
        id: "publish_date",
        header: "תאריך פרסום",
        size: 80,
        cell: ({ row }) => {
          const t = row.original.tender;
          return (
            <span className="text-sm whitespace-nowrap">
              {formatDateWithYear(t?.publish_date ?? null)}
            </span>
          );
        },
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
        header: () => (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setGroupByType((prev) => !prev);
            }}
            className="flex items-center gap-1 cursor-pointer hover:text-megido-primary"
            title={groupByType ? "בטל קיבוץ לפי סוג" : "קבץ לפי סוג"}
          >
            <span>{"סוג"}</span>
            <Layers
              className={
                groupByType
                  ? "h-3.5 w-3.5 text-megido-primary"
                  : "h-3.5 w-3.5 text-megido-text-muted"
              }
            />
          </button>
        ),
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
        accessorKey: "review_notes",
        header: "הערות צוות",
        size: 110,
        cell: ({ getValue }) => (
          <span className="text-xs text-megido-text-muted line-clamp-2">
            {getValue<string>() || "—"}
          </span>
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
        id: "govmap",
        header: 'תב"ע',
        size: 50,
        cell: ({ row }) => <GovMapLink tender={row.original.tender} />,
      },
    ],
    [groupByType],
  );

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
  const { data: outcomeMap } = useTenderOutcomes(tenderIds);

  // Brochure filter
  const [brochureFilter, setBrochureFilter] =
    useState<BrochureFilter>("with_brochure");

  // Modal state
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Lot and building rights for the modal
  const { data: modalLots } = useTenderLots(selectedTender?.tender_id);
  const { data: modalBuildingRights } = useTenderBuildingRights(
    selectedTender?.tender_id,
  );

  // Split watchlist into active vs expired (forced_expired OR terminal status OR deadline passed)
  const { activeItems, expiredItems } = useMemo(() => {
    if (!watchlistItems) return { activeItems: [] as (WatchlistItemWithTender & { tender: Tender })[], expiredItems: [] as (WatchlistItemWithTender & { tender: Tender })[] };

    const withTender = watchlistItems.filter(
      (item): item is WatchlistItemWithTender & { tender: Tender } =>
        item.tender != null,
    );

    const active: (WatchlistItemWithTender & { tender: Tender })[] = [];
    const expired: (WatchlistItemWithTender & { tender: Tender })[] = [];

    for (const item of withTender) {
      if (isExpiredTender(item.tender, outcomeMap?.[item.tender_id])) {
        expired.push(item);
      } else {
        active.push(item);
      }
    }

    return { activeItems: active, expiredItems: expired };
  }, [watchlistItems, outcomeMap]);

  // Build active table rows (with brochure filter)
  const rows: WatchlistRow[] = useMemo(() => {
    let items = activeItems;

    if (brochureFilter === "with_brochure") {
      items = items.filter((item) => Boolean(item.tender.published_booklet));
    }

    return items
      .map((item) => {
        const tid = item.tender_id;
        const review = reviewMap?.[tid];
        const days = computeDays(item.tender.deadline);

        return {
          tender_id: tid,
          tender: item.tender,
          review_status: review?.status ?? "לא נסקר",
          review_notes: review?.notes ?? "",
          watchlist_notes: item.notes ?? "",
          days_to_deadline: days,
          lot_agg: lotMap?.[tid] ?? EMPTY_LOT,
        };
      })
      .sort((a, b) => {
        const aBook = a.tender.published_booklet ? 0 : 1;
        const bBook = b.tender.published_booklet ? 0 : 1;
        if (aBook !== bBook) return aBook - bBook;
        const aDays = a.days_to_deadline ?? Infinity;
        const bDays = b.days_to_deadline ?? Infinity;
        return aDays - bDays;
      });
  }, [activeItems, reviewMap, lotMap, brochureFilter]);

  // Bucket rows by category for grouped view (preserves deadline ordering within group)
  const groupedRows = useMemo(() => {
    if (!groupByType) return null;
    const buckets = new Map<string, WatchlistRow[]>();
    for (const r of rows) {
      const cat = getCategoryLabel(r.tender);
      const arr = buckets.get(cat);
      if (arr) arr.push(r);
      else buckets.set(cat, [r]);
    }
    return CATEGORY_ORDER.filter((cat) => buckets.has(cat)).map((cat) => ({
      category: cat,
      rows: buckets.get(cat)!,
    }));
  }, [rows, groupByType]);

  // Expired tenders are rendered by ExpiredWatchlistSection at page bottom

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
        "סטטוס סקירה": r.review_status,
        "הערות צוות": r.review_notes || "",
        "חוברת": t?.published_booklet ? "כן" : "לא",
        "מספר מכרז": t?.tender_name ?? r.tender_id,
        "עיר": t?.city ?? "",
        "סוג מכרז": t?.tender_type ?? "",
        "ייעוד": t?.purpose ?? "",
        'יח"ד': t?.units ?? "",
        "מועד סגירה": t?.deadline ?? "",
        "שוק חופשי": r.lot_agg.free_market || "",
        "מחיר מטרה": r.lot_agg.target_price || "",
        'סה"כ מגרשים': r.lot_agg.total || "",
        "% מחיר מטרה": r.lot_agg.pct,
        "הערות": r.watchlist_notes || "",
        "מחוז": t?.region ?? "",
        "מיקום": t?.location ?? "",
        'שטח (מ"ר)': t?.area_sqm ?? "",
        "מחיר מינימום": t?.min_price ?? "",
        "תאריך פרסום": t?.publish_date ?? "",
        "תכנית": t?.plan_number ?? "",
        "מס׳ מתחמים": t?.lot_count ?? "",
      };
    });

    const ws = XLSX.utils.json_to_sheet(xlsRows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "חדר עסקאות");

    const today = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(wb, `watchlist_${today}.xls`, { bookType: "xls" });
  }, [rows]);

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-lg font-semibold text-megido-text-heading">
          {"מכרזים מועדפים - חדר עסקאות"}
        </h4>
        <button
          type="button"
          onClick={exportToExcel}
          disabled={rows.length === 0}
          className="flex items-center gap-1.5 rounded-lg border border-megido-border px-3 py-1.5 text-xs font-medium text-megido-text-heading transition-colors hover:bg-megido-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Download className="h-3.5 w-3.5" />
          {"ייצוא לאקסל"}
        </button>
      </div>

      {(watchlistItems ?? []).length > 0 ? (
        <>
          <BrochureToggle
            value={brochureFilter}
            onChange={setBrochureFilter}
            className="mb-3"
          />
          {groupByType && groupedRows ? (
            <div className="space-y-4">
              {groupedRows.map(({ category, rows: groupRows }) => {
                const collapsed = collapsedGroups.has(category);
                return (
                  <div key={category}>
                    <button
                      type="button"
                      onClick={() => toggleGroup(category)}
                      className="flex w-full items-center gap-2 rounded-md py-1.5 text-end transition-colors hover:bg-megido-neutral-50"
                    >
                      {collapsed ? (
                        <ChevronDown className="h-4 w-4 text-megido-text-muted" />
                      ) : (
                        <ChevronUp className="h-4 w-4 text-megido-text-muted" />
                      )}
                      <h5 className="text-base font-semibold text-megido-text-heading">
                        {category}{" "}
                        <span className="text-sm font-normal text-megido-text-muted">
                          ({groupRows.length})
                        </span>
                      </h5>
                    </button>
                    {!collapsed && (
                      <DataTable
                        columns={columns}
                        data={groupRows}
                        isLoading={watchlistLoading}
                        onRowClick={handleRowClick}
                        pageSize={100}
                        emptyMessage={"אין מכרזים בקטגוריה זו."}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <DataTable
              columns={columns}
              data={rows}
              isLoading={watchlistLoading}
              onRowClick={handleRowClick}
              pageSize={20}
              emptyMessage={"אין מכרזים מועדפים."}
            />
          )}
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
          {"אין מכרזים מועדפים. הוסף מכרזים דרך דאשבורד חדר העסקאות."}
        </p>
      )}

      {/* Expired tenders are rendered separately at page bottom */}

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
