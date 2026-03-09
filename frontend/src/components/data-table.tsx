/**
 * DataTable component (generic).
 *
 * Fully typed, sortable, paginated data table built on @tanstack/react-table.
 * Features: RTL text alignment, column sorting (click headers), single-row
 * selection, pagination controls, loading skeleton, and Hebrew empty state.
 *
 * Uses the shadcn/ui Table primitives for consistent styling.
 */
"use client";

import { useState, useMemo, useCallback } from "react";
import {
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
  type OnChangeFn,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight } from "lucide-react";
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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DataTableProps<TData> {
  /** Column definitions. */
  columns: ColumnDef<TData, unknown>[];
  /** Table data array. */
  data: TData[];
  /** Show loading skeleton. */
  isLoading?: boolean;
  /** Number of skeleton rows in loading state. Defaults to 5. */
  skeletonRows?: number;
  /** Rows per page. Defaults to 10. */
  pageSize?: number;
  /** Hebrew empty-state message. */
  emptyMessage?: string;
  /** Callback when a row is selected (single mode). */
  onRowSelect?: (row: TData | null) => void;
  /** Enable row selection. Defaults to false. */
  enableSelection?: boolean;
  /** Additional CSS classes on the outer wrapper. */
  className?: string;
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
// Component
// ---------------------------------------------------------------------------

export function DataTable<TData>({
  columns,
  data,
  isLoading = false,
  skeletonRows = 5,
  pageSize = 10,
  emptyMessage = "\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9\u05DD \u05DC\u05D4\u05E6\u05D2\u05D4",
  onRowSelect,
  enableSelection = false,
  className,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  // Single-row selection handler
  const handleRowSelectionChange: OnChangeFn<RowSelectionState> = useCallback(
    (updaterOrValue) => {
      setRowSelection((prev) => {
        const next =
          typeof updaterOrValue === "function"
            ? updaterOrValue(prev)
            : updaterOrValue;

        // Single selection: only keep one row
        const selectedKeys = Object.keys(next).filter((k) => next[k]);
        if (selectedKeys.length > 1) {
          // Keep only the most recently added
          const lastKey = selectedKeys[selectedKeys.length - 1];
          const single: RowSelectionState = { [lastKey]: true };

          if (onRowSelect) {
            const idx = parseInt(lastKey, 10);
            onRowSelect(data[idx] ?? null);
          }
          return single;
        }

        if (onRowSelect) {
          if (selectedKeys.length === 1) {
            const idx = parseInt(selectedKeys[0], 10);
            onRowSelect(data[idx] ?? null);
          } else {
            onRowSelect(null);
          }
        }
        return next;
      });
    },
    [data, onRowSelect],
  );

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      rowSelection,
    },
    onSortingChange: setSorting,
    onRowSelectionChange: enableSelection ? handleRowSelectionChange : undefined,
    enableRowSelection: enableSelection,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize },
    },
  });

  const pageIndex = table.getState().pagination.pageIndex;
  const pageCount = table.getPageCount();

  // Memoize column count for skeleton
  const colCount = useMemo(() => columns.length, [columns]);

  return (
    <div dir="rtl" className={cn("w-full", className)}>
      <div className="rounded-md border overflow-x-auto">
        <Table className="table-auto min-w-[900px]">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();

                  return (
                    <TableHead
                      key={header.id}
                      style={
                        header.column.columnDef.size
                          ? { width: header.column.columnDef.size }
                          : undefined
                      }
                      tabIndex={canSort ? 0 : undefined}
                      onKeyDown={
                        canSort
                          ? (e: React.KeyboardEvent) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                header.column.getToggleSortingHandler()?.(e);
                              }
                            }
                          : undefined
                      }
                      className={cn(
                        "text-end",
                        canSort && "cursor-pointer select-none",
                        canSort && "focus-visible:ring-2 focus-visible:ring-megido-primary focus-visible:ring-offset-2 outline-none",
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
              Array.from({ length: skeletonRows }).map((_, i) => (
                <SkeletonRow key={`skeleton-${i}`} colCount={colCount} />
              ))
            ) : table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() ? "selected" : undefined}
                  className={cn(
                    enableSelection && "cursor-pointer",
                    row.getIsSelected() && "bg-megido-primary-50",
                  )}
                  onClick={
                    enableSelection
                      ? () => row.toggleSelected(!row.getIsSelected())
                      : undefined
                  }
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
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={colCount}
                  className="h-24 text-center text-megido-text-muted"
                >
                  {emptyMessage}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination controls */}
      {pageCount > 1 && (
        <div className="flex items-center justify-between px-2 py-3">
          <span className="text-sm text-megido-text-muted">
            {"\u05E2\u05DE\u05D5\u05D3"} {pageIndex + 1}{" "}
            {"\u05DE\u05EA\u05D5\u05DA"} {pageCount}
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
      )}
    </div>
  );
}
