/**
 * ClosingSoonDashboard component.
 *
 * Dashboard-specific version of the closing-soon table. Unlike the management
 * version, this is NOT collapsible (always visible) and fetches its own data
 * using useActiveTenders + getClosingSoonTenders. Shows tenders closing within
 * CLOSING_SOON_DAYS with brochure toggle filter and click-to-open detail modal.
 */
"use client";

import { useState, useMemo } from "react";
import { type ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/data-table";
import { BrochureToggle, type BrochureFilter } from "@/components/brochure-toggle";
import { DeadlineBadge } from "@/components/deadline-badge";
import { TenderDetailModal } from "@/components/tender-detail-modal";
import { useTenderLots, useTenderBuildingRights } from "@/hooks/use-lots";
import { useActiveTenders } from "@/hooks";
import {
  CLOSING_SOON_DAYS,
  RELEVANT_TENDER_TYPES,
} from "@/lib/constants";
import { getClosingSoonTenders } from "@/lib/utils/tenders";
import type { TenderWithComputed } from "@/types/database";

// ---------------------------------------------------------------------------
// Row type
// ---------------------------------------------------------------------------

interface ClosingRow {
  tender_id: number;
  tender_name: string;
  city: string;
  tender_type: string;
  purpose: string;
  units: number | null;
  deadline: string;
  days_to_deadline: number | null;
  published_booklet: boolean;
  /** Full tender object for the modal. */
  _tender: TenderWithComputed;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDeadline(deadline: string | null): string {
  if (!deadline) return "\u2014";
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return "\u2014";
  return d.toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit" });
}

// ---------------------------------------------------------------------------
// Column definitions
// ---------------------------------------------------------------------------

const columns: ColumnDef<ClosingRow, unknown>[] = [
  {
    id: "booklet",
    header: "\u05D7\u05D5\u05D1\u05E8\u05EA",
    cell: ({ row }) =>
      row.original.published_booklet ? "\u2705" : "\u274C",
  },
  {
    accessorKey: "tender_name",
    header: "\u05DE\u05E1\u05E4\u05E8 \u05DE\u05DB\u05E8\u05D6",
    cell: ({ getValue }) => (
      <span className="text-sm font-medium">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "city",
    header: "\u05E2\u05D9\u05E8",
  },
  {
    accessorKey: "tender_type",
    header: "\u05E1\u05D5\u05D2",
  },
  {
    accessorKey: "purpose",
    header: "\u05D9\u05D9\u05E2\u05D5\u05D3",
  },
  {
    accessorKey: "units",
    header: '\u05D9\u05D7"\u05D3',
    cell: ({ getValue }) => getValue<number | null>() ?? "\u2014",
  },
  {
    id: "deadline_fmt",
    header: "\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4",
    cell: ({ row }) => (
      <div className="flex items-center gap-1.5 whitespace-nowrap">
        <DeadlineBadge
          daysRemaining={row.original.days_to_deadline}
          compact
        />
        <span className="text-sm">{formatDeadline(row.original.deadline)}</span>
      </div>
    ),
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ClosingSoonDashboard() {
  const [brochureFilter, setBrochureFilter] = useState<BrochureFilter>("all");

  // Modal state
  const [selectedTender, setSelectedTender] =
    useState<TenderWithComputed | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const { data: modalLots } = useTenderLots(selectedTender?.tender_id);
  const { data: modalBuildingRights } = useTenderBuildingRights(
    selectedTender?.tender_id,
  );

  // Fetch active tenders
  const {
    data: activeTenders,
    isLoading,
    isError,
    refetch,
  } = useActiveTenders();

  // Filter to relevant types, then to closing soon
  const closingSoonTenders = useMemo(() => {
    const relevant = (activeTenders ?? []).filter((t) =>
      RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? 0),
    );
    return getClosingSoonTenders(relevant, CLOSING_SOON_DAYS);
  }, [activeTenders]);

  // Build rows with brochure filter
  const rows: ClosingRow[] = useMemo(() => {
    let filtered = closingSoonTenders;

    if (brochureFilter === "with_brochure") {
      filtered = filtered.filter((t) => Boolean(t.published_booklet));
    }

    return filtered.map((t) => ({
      tender_id: t.tender_id,
      tender_name: t.tender_name ?? String(t.tender_id),
      city: t.city ?? "\u2014",
      tender_type: t.tender_type ?? "\u2014",
      purpose: t.purpose ?? "\u2014",
      units: t.units,
      deadline: t.deadline ?? "",
      days_to_deadline: t.days_to_deadline,
      published_booklet: Boolean(t.published_booklet),
      _tender: t,
    }));
  }, [closingSoonTenders, brochureFilter]);

  const handleRowSelect = (row: ClosingRow | null) => {
    if (row) {
      setSelectedTender(row._tender);
      setModalOpen(true);
    }
  };

  if (isError) {
    return (
      <section dir="rtl">
        <h3 className="mb-2 text-base font-semibold text-megido-text-heading">
          {"\u05E0\u05E1\u05D2\u05E8\u05D9\u05DD \u05D114 \u05D4\u05D9\u05DE\u05D9\u05DD \u05D4\u05E7\u05E8\u05D5\u05D1\u05D9\u05DD"}
        </h3>
        <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm font-medium text-red-700">
            {"\u05E9\u05D2\u05D9\u05D0\u05D4 \u05D1\u05D8\u05E2\u05D9\u05E0\u05EA \u05D4\u05E0\u05EA\u05D5\u05E0\u05D9\u05DD"}
          </p>
          <button
            type="button"
            onClick={() => void refetch()}
            className="rounded-md bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-200"
          >
            {"\u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section dir="rtl">
      <h3 className="mb-2 text-base font-semibold text-megido-text-heading">
        {"\u05E0\u05E1\u05D2\u05E8\u05D9\u05DD \u05D114 \u05D4\u05D9\u05DE\u05D9\u05DD \u05D4\u05E7\u05E8\u05D5\u05D1\u05D9\u05DD"}{" "}
        <span className="text-base font-normal text-megido-text-muted">
          ({closingSoonTenders.length})
        </span>
      </h3>

      {closingSoonTenders.length > 0 ? (
        <>
          <BrochureToggle
            value={brochureFilter}
            onChange={setBrochureFilter}
            className="mb-3"
          />
          <DataTable
            columns={columns}
            data={rows}
            isLoading={isLoading}
            enableSelection
            onRowSelect={handleRowSelect}
            pageSize={10}
            emptyMessage={"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05E0\u05E1\u05D2\u05E8\u05D9\u05DD \u05EA\u05D5\u05DA 14 \u05D9\u05D5\u05DD."}
          />
          <p className="mt-2 text-xs text-megido-text-muted">
            {"\u05DB\u05DC\u05DC \u05D4\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05D9\u05D9\u05E1\u05D2\u05E8\u05D5 \u05D114 \u05D4\u05D9\u05DE\u05D9\u05DD \u05D4\u05E7\u05E8\u05D5\u05D1\u05D9\u05DD"}{" "}
            {"\u2014"} {closingSoonTenders.length}{" "}
            {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD"}
          </p>
        </>
      ) : (
        <p className="py-3 text-sm text-megido-text-muted">
          {"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05E0\u05E1\u05D2\u05E8\u05D9\u05DD \u05EA\u05D5\u05DA 14 \u05D9\u05D5\u05DD."}
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
