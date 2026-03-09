/**
 * ExplorerTable component.
 *
 * Sortable, paginated data table for the tender explorer page. Built on
 * @tanstack/react-table with RTL support. Columns match the Streamlit
 * explorer: total_score (progress bar), tender_name, units, city, region,
 * tender_type, purpose, lot_count, max_lots_per_bidder, deadline, status,
 * and published_booklet (checkbox icon).
 *
 * Default sort: deadline ascending, null/NaN last.
 * Single row selection triggers detail panel.
 * Pagination: 20 rows per page.
 * Footer shows record count.
 */
"use client";

import { useMemo, useState, useCallback } from "react";
import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Circle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import type { ScoredTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExplorerTableProps {
  /** Scored tender data. */
  data: ScoredTender[];
  /** Whether data is loading. */
  isLoading?: boolean;
  /** Callback when a row is selected. */
  onRowSelect?: (tender: ScoredTender | null) => void;
  /** Currently selected tender ID. */
  selectedId?: number | null;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Score progress bar cell
// ---------------------------------------------------------------------------

function ScoreCell({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const color =
    pct >= 70
      ? "bg-emerald-500"
      : pct >= 40
        ? "bg-amber-500"
        : "bg-red-400";

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-16 overflow-hidden rounded-full bg-megido-neutral-200">
        <div
          className={cn("h-full rounded-full", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-megido-neutral-600">
        {Math.round(pct)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(value: string | null): string {
  if (!value) return "\u2014";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "\u2014";
  return d.toLocaleDateString("he-IL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/** Custom sort function that pushes null/NaN to the bottom (last). */
function nullsLastSort(
  a: number | string | null | undefined,
  b: number | string | null | undefined,
  desc: boolean,
): number {
  const aNull = a == null || (typeof a === "number" && Number.isNaN(a)) || a === "";
  const bNull = b == null || (typeof b === "number" && Number.isNaN(b)) || b === "";

  if (aNull && bNull) return 0;
  if (aNull) return 1; // a goes last
  if (bNull) return -1; // b goes last

  if (a! < b!) return desc ? 1 : -1;
  if (a! > b!) return desc ? -1 : 1;
  return 0;
}

// ---------------------------------------------------------------------------
// Skeleton row
// ---------------------------------------------------------------------------

function SkeletonRow({ colCount }: { colCount: number }) {
  return (
    <TableRow>
      {Array.from({ length: colCount }).map((_, i) => (
        <TableCell key={i}>
          <div className="h-4 animate-pulse rounded bg-megido-neutral-200" />
        </TableCell>
      ))}
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// Column definitions
// ---------------------------------------------------------------------------

const PAGE_SIZE = 20;

function useExplorerColumns(): ColumnDef<ScoredTender, unknown>[] {
  return useMemo(
    (): ColumnDef<ScoredTender, unknown>[] => [
      {
        accessorKey: "total_score",
        header: "\u05E6\u05D9\u05D5\u05DF", // ציון
        cell: ({ getValue }) => (
          <ScoreCell value={getValue<number>() ?? 0} />
        ),
        sortingFn: (rowA, rowB, columnId) => {
          const a = rowA.getValue<number>(columnId);
          const b = rowB.getValue<number>(columnId);
          return (a ?? 0) - (b ?? 0);
        },
        meta: { widthPercent: "9%" },
      },
      {
        accessorKey: "tender_name",
        header: "\u05E9\u05DD \u05DE\u05DB\u05E8\u05D6", // שם מכרז
        cell: ({ getValue }) => (
          <span className="line-clamp-1">
            {getValue<string>() ?? "\u2014"}
          </span>
        ),
        meta: { widthPercent: "20%" },
      },
      {
        accessorKey: "units",
        header: '\u05D9\u05D7"\u05D3', // יח"ד
        cell: ({ getValue }) => {
          const v = getValue<number>();
          return v != null ? v.toLocaleString("he-IL") : "\u2014";
        },
        sortingFn: (rowA, rowB, columnId) =>
          nullsLastSort(
            rowA.getValue<number>(columnId),
            rowB.getValue<number>(columnId),
            false,
          ),
        meta: { widthPercent: "5%" },
      },
      {
        accessorKey: "city",
        header: "\u05E2\u05D9\u05E8", // עיר
        cell: ({ getValue }) => (
          <span className="truncate block">
            {getValue<string>() ?? "\u2014"}
          </span>
        ),
        meta: { widthPercent: "8%" },
      },
      {
        accessorKey: "region",
        header: "\u05DE\u05D7\u05D5\u05D6", // מחוז
        cell: ({ getValue }) => getValue<string>() ?? "\u2014",
        meta: { widthPercent: "6%" },
      },
      {
        accessorKey: "tender_type",
        header: "\u05E1\u05D5\u05D2", // סוג
        cell: ({ getValue }) => (
          <span className="truncate block">
            {getValue<string>() ?? "\u2014"}
          </span>
        ),
        meta: { widthPercent: "9%" },
      },
      {
        accessorKey: "purpose",
        header: "\u05D9\u05D9\u05E2\u05D5\u05D3", // ייעוד
        cell: ({ getValue }) => (
          <span className="truncate block">
            {getValue<string>() ?? "\u2014"}
          </span>
        ),
        meta: { widthPercent: "9%" },
      },
      {
        accessorKey: "lot_count",
        header: "\u05DE\u05EA\u05D7\u05DE\u05D9\u05DD", // מתחמים
        cell: ({ getValue }) => {
          const v = getValue<number>();
          return v != null ? String(v) : "\u2014";
        },
        sortingFn: (rowA, rowB, columnId) =>
          nullsLastSort(
            rowA.getValue<number>(columnId),
            rowB.getValue<number>(columnId),
            false,
          ),
        meta: { widthPercent: "6%" },
      },
      {
        accessorKey: "max_lots_per_bidder",
        header: "\u05DE\u05E7\u05E1' \u05DC\u05D6\u05D5\u05DB\u05D4", // מקס' לזוכה
        cell: ({ getValue }) => {
          const v = getValue<number>();
          return v != null ? String(v) : "\u2014";
        },
        sortingFn: (rowA, rowB, columnId) =>
          nullsLastSort(
            rowA.getValue<number>(columnId),
            rowB.getValue<number>(columnId),
            false,
          ),
        meta: { widthPercent: "7%" },
      },
      {
        accessorKey: "deadline",
        header: "\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4", // מועד סגירה
        cell: ({ getValue }) => formatDate(getValue<string>()),
        sortingFn: (rowA, rowB, columnId) => {
          const a = rowA.getValue<string>(columnId);
          const b = rowB.getValue<string>(columnId);
          return nullsLastSort(a ?? null, b ?? null, false);
        },
        meta: { widthPercent: "9%" },
      },
      {
        accessorKey: "status",
        header: "\u05E1\u05D8\u05D8\u05D5\u05E1", // סטטוס
        cell: ({ getValue }) => getValue<string>() ?? "\u2014",
        meta: { widthPercent: "7%" },
      },
      {
        accessorKey: "published_booklet",
        header: "\u05D7\u05D5\u05D1\u05E8\u05EA", // חוברת
        cell: ({ getValue }) => {
          const val = getValue<number>();
          return val ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          ) : (
            <Circle className="h-4 w-4 text-megido-neutral-300" />
          );
        },
        sortingFn: (rowA, rowB, columnId) => {
          const a = rowA.getValue<number>(columnId) ?? 0;
          const b = rowB.getValue<number>(columnId) ?? 0;
          return a - b;
        },
        meta: { widthPercent: "5%" },
      },
    ],
    [],
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ExplorerTable({
  data,
  isLoading = false,
  onRowSelect,
  selectedId,
  className,
}: ExplorerTableProps) {
  const columns = useExplorerColumns();

  // Default sort: deadline ascending
  const [sorting, setSorting] = useState<SortingState>([
    { id: "deadline", desc: false },
  ]);

  const handleRowClick = useCallback(
    (tender: ScoredTender) => {
      if (!onRowSelect) return;
      // Toggle: deselect if same row clicked again
      if (selectedId === tender.tender_id) {
        onRowSelect(null);
      } else {
        onRowSelect(tender);
      }
    },
    [onRowSelect, selectedId],
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize: PAGE_SIZE },
    },
  });

  const pageIndex = table.getState().pagination.pageIndex;
  const pageCount = table.getPageCount();
  const totalRows = data.length;

  return (
    <div dir="rtl" className={cn("w-full", className)}>
      {/* Record count */}
      <p className="mb-2 text-sm text-megido-text-muted">
        {totalRows.toLocaleString("he-IL")}{" "}
        {"\u05E8\u05E9\u05D5\u05DE\u05D5\u05EA"}{" "}
        {"\u2014"}{" "}
        {"\u05DC\u05D7\u05E5 \u05E2\u05DC \u05E9\u05D5\u05E8\u05D4 \u05DC\u05E6\u05E4\u05D9\u05D9\u05D4 \u05D1\u05E4\u05E8\u05D8\u05D9 \u05D4\u05DE\u05DB\u05E8\u05D6"}
      </p>

      <div className="rounded-md border overflow-hidden">
        <Table className="table-fixed">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();
                  const widthPercent = (
                    header.column.columnDef.meta as
                      | { widthPercent?: string }
                      | undefined
                  )?.widthPercent;

                  return (
                    <TableHead
                      key={header.id}
                      style={widthPercent ? { width: widthPercent } : undefined}
                      className={cn(
                        "text-end whitespace-nowrap overflow-hidden",
                        canSort && "cursor-pointer select-none",
                      )}
                      onClick={
                        canSort
                          ? header.column.getToggleSortingHandler()
                          : undefined
                      }
                    >
                      <div className="flex items-center gap-1">
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                        {canSort && (
                          <span className="shrink-0">
                            {sorted === "asc" ? (
                              <ArrowUp className="h-3.5 w-3.5" />
                            ) : sorted === "desc" ? (
                              <ArrowDown className="h-3.5 w-3.5" />
                            ) : (
                              <ArrowUpDown className="h-3.5 w-3.5 text-megido-text-muted" />
                            )}
                          </span>
                        )}
                      </div>
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>

          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <SkeletonRow
                  key={`skeleton-${i}`}
                  colCount={columns.length}
                />
              ))
            ) : table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => {
                const tender = row.original;
                const isSelected = selectedId === tender.tender_id;

                return (
                  <TableRow
                    key={row.id}
                    className={cn(
                      "cursor-pointer",
                      isSelected && "bg-megido-primary-50",
                    )}
                    onClick={() => handleRowClick(tender)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell
                        key={cell.id}
                        className="text-end overflow-hidden text-ellipsis"
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-megido-text-muted"
                >
                  {"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9\u05DD \u05DC\u05D4\u05E6\u05D2\u05D4"}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination + record count footer */}
      <div className="flex items-center justify-between px-2 py-3">
        <span className="text-sm text-megido-text-muted">
          {"\u05E2\u05DE\u05D5\u05D3"} {pageIndex + 1}{" "}
          {"\u05DE\u05EA\u05D5\u05DA"} {Math.max(pageCount, 1)}
          {" "}
          ({totalRows.toLocaleString("he-IL")}{" "}
          {"\u05E8\u05E9\u05D5\u05DE\u05D5\u05EA"})
        </span>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon-sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
