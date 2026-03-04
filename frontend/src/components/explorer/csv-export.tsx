/**
 * CsvExport component.
 *
 * Download button that exports filtered tenders as a UTF-8 CSV file
 * with BOM prefix (\uFEFF) for proper Hebrew display in Microsoft Excel.
 * Uses Blob + URL.createObjectURL + anchor click pattern.
 *
 * Filename format: land_tenders_YYYYMMDD.csv
 */
"use client";

import { useCallback } from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ScoredTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CsvExportProps {
  /** Tenders to export (already filtered). */
  data: ScoredTender[];
  /** Additional CSS classes on the button. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Column mapping for CSV headers (Hebrew)
// ---------------------------------------------------------------------------

const CSV_COLUMNS: { key: keyof ScoredTender; label: string }[] = [
  { key: "total_score", label: "\u05E6\u05D9\u05D5\u05DF" },
  { key: "tender_name", label: "\u05E9\u05DD \u05DE\u05DB\u05E8\u05D6" },
  { key: "units", label: '\u05D9\u05D7"\u05D3' },
  { key: "city", label: "\u05E2\u05D9\u05E8" },
  { key: "region", label: "\u05DE\u05D7\u05D5\u05D6" },
  { key: "tender_type", label: "\u05E1\u05D5\u05D2" },
  { key: "purpose", label: "\u05D9\u05D9\u05E2\u05D5\u05D3" },
  { key: "lot_count", label: "\u05DE\u05EA\u05D7\u05DE\u05D9\u05DD" },
  {
    key: "max_lots_per_bidder",
    label: "\u05DE\u05E7\u05E1' \u05DC\u05D6\u05D5\u05DB\u05D4",
  },
  {
    key: "deadline",
    label: "\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4",
  },
  { key: "status", label: "\u05E1\u05D8\u05D8\u05D5\u05E1" },
  { key: "published_booklet", label: "\u05D7\u05D5\u05D1\u05E8\u05EA" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Escape a CSV cell value (wrap in quotes if it contains comma, quote, or newline). */
function escapeCsvCell(value: unknown): string {
  if (value == null) return "";
  const str = String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/** Format today as YYYYMMDD. */
function todayStamp(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}${m}${d}`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CsvExport({ data, className }: CsvExportProps) {
  const handleDownload = useCallback(() => {
    // Build CSV header
    const header = CSV_COLUMNS.map((c) => escapeCsvCell(c.label)).join(",");

    // Build CSV rows
    const rows = data.map((tender) =>
      CSV_COLUMNS.map((c) => escapeCsvCell(tender[c.key])).join(","),
    );

    // Combine with BOM for Hebrew Excel support
    const csvContent = "\uFEFF" + [header, ...rows].join("\n");

    // Create blob and trigger download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `land_tenders_${todayStamp()}.csv`;
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();

    // Cleanup
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }, [data]);

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleDownload}
      disabled={data.length === 0}
      className={className}
    >
      <Download className="h-4 w-4" />
      {"\u05D4\u05D5\u05E8\u05D3 CSV"}
    </Button>
  );
}
