/**
 * ClosingSoonSection component for the Management page.
 *
 * Collapsible section showing tenders closing within 14 days.
 * Includes a brochure filter toggle, a compact data table, and
 * click-to-open tender detail modal. Mirrors Section 2 of the
 * Streamlit management.py page.
 */
"use client";

import { useState, useMemo } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/data-table";
import { BrochureToggle, type BrochureFilter } from "@/components/brochure-toggle";
import { DeadlineBadge } from "@/components/deadline-badge";
import { TenderDetailModal } from "@/components/tender-detail-modal";
import { useTenderLots, useTenderBuildingRights } from "@/hooks/use-lots";
import type { TenderWithComputed } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ClosingSoonSectionProps {
  /** Tenders closing within 14 days (pre-filtered by caller). */
  tenders: TenderWithComputed[];
  /** Whether data is still loading. */
  isLoading: boolean;
}

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
      <div className="flex items-center gap-1">
        <span className="text-sm">{formatDeadline(row.original.deadline)}</span>
        <DeadlineBadge
          daysRemaining={row.original.days_to_deadline}
          className="text-[10px]"
        />
      </div>
    ),
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ClosingSoonSection({
  tenders,
  isLoading,
}: ClosingSoonSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const [brochureFilter, setBrochureFilter] = useState<BrochureFilter>("all");

  // Modal state
  const [selectedTender, setSelectedTender] =
    useState<TenderWithComputed | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const { data: modalLots } = useTenderLots(selectedTender?.tender_id);
  const { data: modalBuildingRights } = useTenderBuildingRights(
    selectedTender?.tender_id,
  );

  // Build rows
  const rows: ClosingRow[] = useMemo(() => {
    let filtered = tenders;

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
  }, [tenders, brochureFilter]);

  const handleRowSelect = (row: ClosingRow | null) => {
    if (row) {
      setSelectedTender(row._tender);
      setModalOpen(true);
    }
  };

  return (
    <section>
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 rounded-md py-2 text-right transition-colors hover:bg-slate-50"
      >
        {expanded ? (
          <ChevronUp className="h-5 w-5 text-slate-500" />
        ) : (
          <ChevronDown className="h-5 w-5 text-slate-500" />
        )}
        <h4 className="text-lg font-semibold text-slate-800">
          {"\u05E0\u05E1\u05D2\u05E8\u05D9\u05DD \u05D114 \u05D9\u05DE\u05D9\u05DD \u05D4\u05E7\u05E8\u05D5\u05D1\u05D9\u05DD"}{" "}
          <span className="text-base font-normal text-slate-500">
            ({tenders.length})
          </span>
        </h4>
      </button>

      {/* Collapsible content */}
      {expanded && (
        <div className="mt-2">
          {tenders.length > 0 ? (
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
                pageSize={15}
                emptyMessage={"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05E0\u05E1\u05D2\u05E8\u05D9\u05DD \u05EA\u05D5\u05DA 14 \u05D9\u05D5\u05DD."}
              />
              <p className="mt-2 text-xs text-slate-500">
                {"\u05DB\u05DC\u05DC \u05D4\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05D9\u05D9\u05E1\u05D2\u05E8\u05D5 \u05D114 \u05D4\u05D9\u05DE\u05D9\u05DD \u05D4\u05E7\u05E8\u05D5\u05D1\u05D9\u05DD"}{" "}
                {"\u2014"} {tenders.length}{" "}
                {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD"}
              </p>
            </>
          ) : (
            <p className="py-3 text-sm text-slate-500">
              {"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05E0\u05E1\u05D2\u05E8\u05D9\u05DD \u05EA\u05D5\u05DA 14 \u05D9\u05D5\u05DD."}
            </p>
          )}
        </div>
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
