/**
 * CategoryTabsSection component for the Management page.
 *
 * Three tabs for additional tender categories: Rental Housing (diur hashkara),
 * Sheltered Housing (diur mugan), and Initiative Tenders (michraz yezum).
 * Each tab shows a brochure toggle, total units metric, and compact data table.
 * Mirrors Section 3 of the Streamlit management.py page.
 */
"use client";

import { useState, useMemo } from "react";
import { type ColumnDef } from "@tanstack/react-table";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DataTable } from "@/components/data-table";
import { BrochureToggle, type BrochureFilter } from "@/components/brochure-toggle";
import { MetricCard } from "@/components/metric-card";
import { DeadlineBadge } from "@/components/deadline-badge";
import type { TenderWithComputed } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CategoryTabsSectionProps {
  /** All active tenders (broad filter -- not just CARD types). */
  allActiveTenders: TenderWithComputed[];
}

interface CompactRow {
  tender_id: number;
  tender_name: string;
  city: string;
  tender_type: string;
  units: number | null;
  deadline: string;
  days_to_deadline: number | null;
  published_booklet: boolean;
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

function toRows(tenders: TenderWithComputed[]): CompactRow[] {
  return tenders.map((t) => ({
    tender_id: t.tender_id,
    tender_name: t.tender_name ?? String(t.tender_id),
    city: t.city ?? "\u2014",
    tender_type: t.tender_type ?? "\u2014",
    units: t.units,
    deadline: t.deadline ?? "",
    days_to_deadline: t.days_to_deadline,
    published_booklet: Boolean(t.published_booklet),
  }));
}

// ---------------------------------------------------------------------------
// Column definitions for the compact table
// ---------------------------------------------------------------------------

const compactColumns: ColumnDef<CompactRow, unknown>[] = [
  {
    id: "booklet",
    header: "\u05D7\u05D5\u05D1\u05E8\u05EA",
    cell: ({ row }) =>
      row.original.published_booklet ? "\u2705" : "\u274C",
  },
  {
    accessorKey: "deadline",
    header: "\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4",
    sortingFn: "alphanumeric",
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
  {
    accessorKey: "city",
    header: "\u05E2\u05D9\u05E8",
  },
  {
    accessorKey: "tender_type",
    header: "\u05E1\u05D5\u05D2",
  },
  {
    accessorKey: "units",
    header: '\u05D9\u05D7"\u05D3',
    cell: ({ getValue }) => getValue<number | null>() ?? "\u2014",
  },
  {
    accessorKey: "tender_name",
    header: "\u05DE\u05E1\u05E4\u05E8 \u05DE\u05DB\u05E8\u05D6",
    cell: ({ getValue }) => (
      <span className="text-sm font-medium">{getValue<string>()}</span>
    ),
  },
];

// ---------------------------------------------------------------------------
// Single category tab content
// ---------------------------------------------------------------------------

interface CategoryTabContentProps {
  label: string;
  tenders: TenderWithComputed[];
  emptyMessage: string;
}

function CategoryTabContent({
  label,
  tenders,
  emptyMessage,
}: CategoryTabContentProps) {
  const [brochureFilter, setBrochureFilter] = useState<BrochureFilter>("with_brochure");

  const filtered = useMemo(() => {
    if (brochureFilter === "with_brochure") {
      return tenders.filter((t) => Boolean(t.published_booklet));
    }
    return tenders;
  }, [tenders, brochureFilter]);

  const totalUnits = useMemo(
    () => tenders.reduce((sum, t) => sum + (t.units ?? 0), 0),
    [tenders],
  );

  const rows = useMemo(() => toRows(filtered), [filtered]);

  if (tenders.length === 0) {
    return (
      <p className="py-4 text-sm text-megido-text-muted">{emptyMessage}</p>
    );
  }

  return (
    <div className="space-y-3">
      <MetricCard
        label={'\u05E1\u05D4"\u05DB \u05D9\u05D7"\u05D3'}
        value={totalUnits.toLocaleString("he-IL")}
        className="max-w-xs"
      />
      <BrochureToggle value={brochureFilter} onChange={setBrochureFilter} />
      <DataTable
        columns={compactColumns}
        data={rows}
        pageSize={10}
        emptyMessage={emptyMessage}
      />
      <p className="text-xs text-megido-text-muted">
        {tenders.length} {label}{" "}
        {"\u05E4\u05E2\u05D9\u05DC\u05D9\u05DD"}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function CategoryTabsSection({
  allActiveTenders,
}: CategoryTabsSectionProps) {
  // Filter per category
  const rentalHousing = useMemo(
    () =>
      allActiveTenders.filter(
        (t) => t.tender_type === "\u05D3\u05D9\u05D5\u05E8 \u05DC\u05D4\u05E9\u05DB\u05E8\u05D4",
      ),
    [allActiveTenders],
  );

  const shelteredHousing = useMemo(
    () =>
      allActiveTenders.filter((t) =>
        (t.purpose ?? "").includes("\u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF"),
      ),
    [allActiveTenders],
  );

  const initiativeTenders = useMemo(
    () =>
      allActiveTenders.filter(
        (t) => t.tender_type === "\u05DE\u05DB\u05E8\u05D6 \u05D9\u05D9\u05D6\u05D5\u05DD",
      ),
    [allActiveTenders],
  );

  return (
    <section>
      <h4 className="mb-4 text-lg font-semibold text-megido-text-heading">
        {"\u05E1\u05D5\u05D2\u05D9\u05DD \u05E0\u05D5\u05E1\u05E4\u05D9\u05DD"}
      </h4>

      <Tabs defaultValue="rental" dir="rtl">
        <TabsList>
          <TabsTrigger value="rental">
            {"\u05D3\u05D9\u05D5\u05E8 \u05DC\u05D4\u05E9\u05DB\u05E8\u05D4"}
          </TabsTrigger>
          <TabsTrigger value="sheltered">
            {"\u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF"}
          </TabsTrigger>
          <TabsTrigger value="initiative">
            {"\u05DE\u05DB\u05E8\u05D6 \u05D9\u05D9\u05D6\u05D5\u05DD"}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="rental">
          <CategoryTabContent
            label={"\u05DE\u05DB\u05E8\u05D6\u05D9 \u05D3\u05D9\u05D5\u05E8 \u05DC\u05D4\u05E9\u05DB\u05E8\u05D4"}
            tenders={rentalHousing}
            emptyMessage={"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9 \u05D3\u05D9\u05D5\u05E8 \u05DC\u05D4\u05E9\u05DB\u05E8\u05D4 \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD \u05DB\u05E8\u05D2\u05E2."}
          />
        </TabsContent>

        <TabsContent value="sheltered">
          <CategoryTabContent
            label={"\u05DE\u05DB\u05E8\u05D6\u05D9 \u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF"}
            tenders={shelteredHousing}
            emptyMessage={"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9 \u05D3\u05D9\u05D5\u05E8 \u05DE\u05D5\u05D2\u05DF \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD \u05DB\u05E8\u05D2\u05E2."}
          />
        </TabsContent>

        <TabsContent value="initiative">
          <CategoryTabContent
            label={"\u05DE\u05DB\u05E8\u05D6\u05D9 \u05D9\u05D9\u05D6\u05D5\u05DD"}
            tenders={initiativeTenders}
            emptyMessage={"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9 \u05D9\u05D9\u05D6\u05D5\u05DD \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD \u05DB\u05E8\u05D2\u05E2."}
          />
        </TabsContent>
      </Tabs>
    </section>
  );
}
