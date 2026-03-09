/**
 * NewDocumentsSection component.
 *
 * Row 1 of the dashboard: two tables stacked vertically showing new documents
 * and new brochures in the last 7 days. KPI metric cards have been moved to
 * the combined KpiCategoryRow component.
 *
 * Data comes from useNewDocuments(7) for documents, and useActiveTenders()
 * for tender info lookup.
 */
"use client";

import { useMemo } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { Download } from "lucide-react";

import { DataTable } from "@/components/data-table";
import { useNewDocuments, useActiveTenders } from "@/hooks";
import { RELEVANT_TENDER_TYPES } from "@/lib/constants";
import { buildDocumentUrl } from "@/lib/utils/tenders";
import type { TenderDocumentWithInfo, TenderWithComputed } from "@/types/database";

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
          className="inline-flex items-center gap-1 text-sm font-medium text-megido-primary hover:underline"
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
  const {
    data: newDocs,
    isLoading: docsLoading,
    isError: docsError,
    refetch: refetchDocs,
  } = useNewDocuments(7);
  const {
    data: activeTenders,
    isLoading: tendersLoading,
    isError: tendersError,
    refetch: refetchTenders,
  } = useActiveTenders();

  const isLoading = docsLoading || tendersLoading;
  const isError = docsError || tendersError;

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

  if (isError) {
    return (
      <section dir="rtl">
        <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm font-medium text-red-700">
            {"\u05E9\u05D2\u05D9\u05D0\u05D4 \u05D1\u05D8\u05E2\u05D9\u05E0\u05EA \u05D4\u05E0\u05EA\u05D5\u05E0\u05D9\u05DD"}
          </p>
          <button
            type="button"
            onClick={() => {
              void refetchDocs();
              void refetchTenders();
            }}
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
      <div className="space-y-4">
        {/* New documents table */}
        <div>
          <h3 className="mb-2 text-base font-semibold text-megido-text-heading">
            {"\u05D4\u05D5\u05D3\u05E2\u05D5\u05EA \u05D7\u05D3\u05E9\u05D5\u05EA \u05D1\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD (7 \u05D4\u05D9\u05DE\u05D9\u05DD \u05D4\u05D0\u05D7\u05E8\u05D5\u05E0\u05D9\u05DD)"}
          </h3>
          <DataTable
            columns={docColumns}
            data={docTableRows}
            isLoading={isLoading}
            pageSize={5}
            emptyMessage={"\u05D0\u05D9\u05DF \u05E4\u05E8\u05D9\u05D8\u05D9\u05DD \u05D7\u05D3\u05E9\u05D9\u05DD \u05D4\u05E9\u05D1\u05D5\u05E2"}
          />
        </div>

        {/* New brochures table */}
        <div>
          <h3 className="mb-2 text-base font-semibold text-megido-text-heading">
            {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E9\u05E4\u05D5\u05E8\u05E1\u05DE\u05D4 \u05D1\u05D4\u05DD \u05D7\u05D5\u05D1\u05E8\u05EA \u05DE\u05DB\u05E8\u05D6 \u05D7\u05D3\u05E9\u05D4"}
          </h3>
          <DataTable
            columns={docColumns}
            data={brochureTableRows}
            isLoading={isLoading}
            pageSize={5}
            emptyMessage={"\u05D0\u05D9\u05DF \u05E4\u05E8\u05D9\u05D8\u05D9\u05DD \u05D7\u05D3\u05E9\u05D9\u05DD \u05D4\u05E9\u05D1\u05D5\u05E2"}
          />
        </div>
      </div>
    </section>
  );
}
