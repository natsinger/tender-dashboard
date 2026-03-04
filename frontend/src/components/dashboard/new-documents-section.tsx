/**
 * NewDocumentsSection component.
 *
 * Row 1 of the dashboard: two tables (new documents + new brochures in last 7 days)
 * on the left, with two MetricCards (active tenders count, closing soon count)
 * on the right. Tables stack vertically on mobile.
 *
 * Data comes from useNewDocuments(7) for documents, and useActiveTenders()
 * for KPI metrics.
 */
"use client";

import { useMemo } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { Download } from "lucide-react";

import { DataTable } from "@/components/data-table";
import { MetricCard } from "@/components/metric-card";
import { useNewDocuments, useActiveTenders } from "@/hooks";
import {
  CLOSING_SOON_DAYS,
  RELEVANT_TENDER_TYPES,
} from "@/lib/constants";
import { buildDocumentUrl, getClosingSoonTenders } from "@/lib/utils/tenders";
import type { TenderDocumentWithInfo, TenderWithComputed } from "@/types/database";

// ---------------------------------------------------------------------------
// Tender type codes for the "active (excluding initiative)" KPI card
// ---------------------------------------------------------------------------

/** Tender type codes for the KPI card: public(1), target price(5), reduced(8). */
const CARD_TENDER_TYPES = new Set([1, 5, 8]);

// ---------------------------------------------------------------------------
// Row type for the document tables
// ---------------------------------------------------------------------------

interface DocTableRow {
  tender_id: number;
  tender_name: string;
  units: number | null;
  city: string;
  tender_type: string;
  doc_description: string;
  download_url: string;
}

// ---------------------------------------------------------------------------
// Column definitions (shared by both tables)
// ---------------------------------------------------------------------------

const docColumns: ColumnDef<DocTableRow, unknown>[] = [
  {
    accessorKey: "tender_name",
    header: "\u05E9\u05DD \u05DE\u05DB\u05E8\u05D6",
    cell: ({ getValue }) => (
      <span className="text-sm">{getValue<string>()}</span>
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
    id: "download",
    header: "\u05DE\u05E1\u05DE\u05DA \u05D7\u05D3\u05E9",
    cell: ({ row }) => {
      const { download_url, doc_description } = row.original;
      if (!download_url) return "\u2014";
      return (
        <a
          href={download_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline"
        >
          <Download className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{doc_description || "\u05DE\u05E1\u05DE\u05DA"}</span>
        </a>
      );
    },
    enableSorting: false,
  },
];

// ---------------------------------------------------------------------------
// Helper: build table rows from active tenders filtered by tender IDs
// ---------------------------------------------------------------------------

/**
 * Build table rows by matching active tenders with new documents.
 * For each tender, picks the most recently updated document and builds
 * a direct download URL instead of linking to the RMI site.
 */
function buildDocRows(
  activeTenders: TenderWithComputed[],
  tenderIds: Set<number>,
  docs: TenderDocumentWithInfo[],
): DocTableRow[] {
  // Group docs by tender_id, keep the most recent per tender
  const latestDocByTender = new Map<number, TenderDocumentWithInfo>();
  for (const doc of docs) {
    if (!tenderIds.has(doc.tender_id)) continue;
    const existing = latestDocByTender.get(doc.tender_id);
    if (
      !existing ||
      (doc.update_date ?? "") > (existing.update_date ?? "")
    ) {
      latestDocByTender.set(doc.tender_id, doc);
    }
  }

  return activeTenders
    .filter((t) => tenderIds.has(t.tender_id))
    .map((t) => {
      const doc = latestDocByTender.get(t.tender_id);
      return {
        tender_id: t.tender_id,
        tender_name: t.tender_name ?? "",
        units: t.units,
        city: t.city ?? "",
        tender_type: t.tender_type ?? "",
        doc_description: doc?.description ?? "",
        download_url: doc ? buildDocumentUrl(doc) : "",
      };
    })
    .sort((a, b) => (b.units ?? 0) - (a.units ?? 0));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function NewDocumentsSection() {
  const { data: newDocs, isLoading: docsLoading } = useNewDocuments(7);
  const { data: activeTenders, isLoading: tendersLoading } = useActiveTenders();

  const isLoading = docsLoading || tendersLoading;

  // Derive relevant-type active tenders
  const relevantActive = useMemo(
    () =>
      (activeTenders ?? []).filter((t) =>
        RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? 0),
      ),
    [activeTenders],
  );

  // Build sets of tender IDs that have new docs / new brochures
  const { newDocTenderIds, newBrochureTenderIds } = useMemo(() => {
    const docIds = new Set<number>();
    const brochureIds = new Set<number>();

    for (const doc of newDocs ?? []) {
      docIds.add(doc.tender_id);
      const name = (doc.doc_name ?? "").toLowerCase();
      const desc = (doc.description ?? "").toLowerCase();
      if (name.includes("\u05D7\u05D5\u05D1\u05E8\u05EA") || desc.includes("\u05D7\u05D5\u05D1\u05E8\u05EA")) {
        brochureIds.add(doc.tender_id);
      }
    }

    return { newDocTenderIds: docIds, newBrochureTenderIds: brochureIds };
  }, [newDocs]);

  // Filter brochure-only docs for the brochure table
  const brochureDocs = useMemo(
    () =>
      (newDocs ?? []).filter((doc) => {
        const name = (doc.doc_name ?? "").toLowerCase();
        const desc = (doc.description ?? "").toLowerCase();
        return name.includes("\u05D7\u05D5\u05D1\u05E8\u05EA") || desc.includes("\u05D7\u05D5\u05D1\u05E8\u05EA");
      }),
    [newDocs],
  );

  // Build table rows (only from active tenders that intersect with new docs)
  const docTableRows = useMemo(
    () => buildDocRows(relevantActive, newDocTenderIds, newDocs ?? []),
    [relevantActive, newDocTenderIds, newDocs],
  );

  const brochureTableRows = useMemo(
    () => buildDocRows(relevantActive, newBrochureTenderIds, brochureDocs),
    [relevantActive, newBrochureTenderIds, brochureDocs],
  );

  // KPI metrics
  const cardActiveCount = useMemo(
    () =>
      relevantActive.filter((t) =>
        CARD_TENDER_TYPES.has(t.tender_type_code ?? 0),
      ).length,
    [relevantActive],
  );

  const closingSoonCount = useMemo(
    () => getClosingSoonTenders(relevantActive, CLOSING_SOON_DAYS).length,
    [relevantActive],
  );

  return (
    <section dir="rtl">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[3fr_2fr]">
        {/* Left: two tables stacked */}
        <div className="space-y-4">
          {/* New documents table */}
          <div>
            <h3 className="mb-2 text-[15px] font-semibold text-slate-800">
              {"\u05DE\u05D5\u05D3\u05E2\u05D5\u05EA \u05D7\u05D3\u05E9\u05D5\u05EA \u05D1\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD (7 \u05D4\u05D9\u05DE\u05D9\u05DD \u05D4\u05D0\u05D7\u05E8\u05D5\u05E0\u05D9\u05DD)"}
            </h3>
            <DataTable
              columns={docColumns}
              data={docTableRows}
              isLoading={isLoading}
              pageSize={8}
              emptyMessage={"\u05D0\u05D9\u05DF \u05E4\u05E8\u05D9\u05D8\u05D9\u05DD \u05D7\u05D3\u05E9\u05D9\u05DD \u05D4\u05E9\u05D1\u05D5\u05E2"}
            />
          </div>

          {/* New brochures table */}
          <div>
            <h3 className="mb-2 text-[15px] font-semibold text-slate-800">
              {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05E4\u05D5\u05E8\u05E1\u05DE\u05D4 \u05D1\u05D4\u05DD \u05D7\u05D5\u05D1\u05E8\u05EA \u05DE\u05DB\u05E8\u05D6 \u05D7\u05D3\u05E9\u05D4"}
            </h3>
            <DataTable
              columns={docColumns}
              data={brochureTableRows}
              isLoading={isLoading}
              pageSize={8}
              emptyMessage={"\u05D0\u05D9\u05DF \u05E4\u05E8\u05D9\u05D8\u05D9\u05DD \u05D7\u05D3\u05E9\u05D9\u05DD \u05D4\u05E9\u05D1\u05D5\u05E2"}
            />
          </div>
        </div>

        {/* Right: KPI metric cards */}
        <div className="flex flex-col gap-4">
          <MetricCard
            label={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD (\u05DC\u05DC\u05D0 \u05D9\u05D9\u05D6\u05D5\u05DD)"}
            value={isLoading ? "\u2026" : cardActiveCount.toLocaleString("he-IL")}
          />
          <MetricCard
            label={"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05D9\u05D9\u05E1\u05D2\u05E8\u05D5 \u05D1\u05E9\u05D1\u05D5\u05E2\u05D9\u05D9\u05DD \u05D4\u05E7\u05E8\u05D5\u05D1\u05D9\u05DD"}
            value={isLoading ? "\u2026" : closingSoonCount.toLocaleString("he-IL")}
          />
        </div>
      </div>
    </section>
  );
}
