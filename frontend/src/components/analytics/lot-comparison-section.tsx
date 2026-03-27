/**
 * Multi-lot comparison section for the Analytics page.
 *
 * Displays a grouped table of tenders that have 2+ lots (tiks),
 * allowing side-by-side comparison of winning prices, units, costs,
 * and competitive metrics across lots within the same tender.
 *
 * When building rights data is available (section 5 of Taba), shows
 * a flat sub-table of תאי שטח with their ייעוד and area breakdown.
 */
"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import type { MultiLotTenderGroup } from "@/lib/utils/analytics-engine";
import type { BuildingRight } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LotComparisonSectionProps {
  multiLotData: MultiLotTenderGroup[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtCurrency(value: number | null): string {
  if (value == null || value === 0) return "\u2014";
  return `\u20AA${value.toLocaleString("he-IL", { maximumFractionDigits: 0 })}`;
}

function fmtNumber(value: number | null): string {
  if (value == null) return "\u2014";
  return value.toLocaleString("he-IL");
}

function fmtArea(value: number | null): string {
  if (value == null || value === 0) return "\u2014";
  return value.toLocaleString("he-IL", { maximumFractionDigits: 0 });
}

// Lot table columns — ordered RTL (rightmost = first in array)
const LOT_COLUMNS = [
  { key: "mitcham", label: "\u05DE\u05EA\u05D7\u05DD", align: "text-start" as const },
  { key: "units", label: '\u05DE\u05E1\' \u05D9\u05D7"\u05D3', align: "text-center" as const },
  { key: "winBid", label: "\u05DE\u05D7\u05D9\u05E8 \u05D6\u05DB\u05D9\u05D9\u05D4", align: "text-center" as const },
  { key: "devCosts", label: "\u05E1\u05DB\u05D5\u05DD \u05E4\u05D9\u05EA\u05D5\u05D7", align: "text-center" as const },
  { key: "sqmPerUnit", label: '\u05DE"\u05E8 \u05E2\u05D9\u05E7\u05E8\u05D9 \u05DC\u05D9\u05D7"\u05D3', align: "text-center" as const },
  { key: "valuePerUnit", label: '\u05E9\u05D5\u05D5\u05D9 \u05DC\u05D9\u05D7"\u05D3', align: "text-center" as const },
  { key: "numBids", label: "\u05DE\u05E1\u05F3 \u05D4\u05E6\u05E2\u05D5\u05EA", align: "text-center" as const },
  { key: "rank", label: "\u05DE\u05D9\u05E7\u05D5\u05DD \u05D1\u05D6\u05DB\u05D9\u05D9\u05D4", align: "text-center" as const },
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LotComparisonSection({
  multiLotData,
}: LotComparisonSectionProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedTenders, setExpandedTenders] = useState<Set<number>>(
    () => new Set(),
  );

  // Filter by city or tender ID
  const filteredData = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return multiLotData;
    return multiLotData.filter(
      (g) =>
        g.city.toLowerCase().includes(q) ||
        String(g.tenderId).includes(q) ||
        g.tenderName.toLowerCase().includes(q),
    );
  }, [multiLotData, searchQuery]);

  function toggleTender(tenderId: number): void {
    setExpandedTenders((prev) => {
      const next = new Set(prev);
      if (next.has(tenderId)) {
        next.delete(tenderId);
      } else {
        next.add(tenderId);
      }
      return next;
    });
  }

  function expandAll(): void {
    setExpandedTenders(new Set(filteredData.map((g) => g.tenderId)));
  }

  function collapseAll(): void {
    setExpandedTenders(new Set());
  }

  if (multiLotData.length === 0) {
    return (
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-megido-text-heading">
          {"\u05D4\u05E9\u05D5\u05D5\u05D0\u05EA \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD"}
        </h2>
        <p className="py-6 text-center text-sm text-megido-text-muted">
          {"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E2\u05DD \u05D9\u05D5\u05EA\u05E8 \u05DE\u05DE\u05EA\u05D7\u05DD \u05D0\u05D7\u05D3"}
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-megido-text-heading">
          {"\u05D4\u05E9\u05D5\u05D5\u05D0\u05EA \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD"}
        </h2>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={expandAll}
            className="rounded-md px-2.5 py-1 text-xs font-medium text-megido-text-muted transition-colors hover:bg-megido-neutral-100 hover:text-megido-text-heading"
          >
            {"\u05E4\u05EA\u05D7 \u05D4\u05DB\u05DC"}
          </button>
          <button
            type="button"
            onClick={collapseAll}
            className="rounded-md px-2.5 py-1 text-xs font-medium text-megido-text-muted transition-colors hover:bg-megido-neutral-100 hover:text-megido-text-heading"
          >
            {"\u05E1\u05D2\u05D5\u05E8 \u05D4\u05DB\u05DC"}
          </button>
        </div>
      </div>

      {/* Search input */}
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        placeholder={"\u05D7\u05D9\u05E4\u05D5\u05E9 \u05E2\u05D9\u05E8 \u05D0\u05D5 \u05DE\u05E1\u05E4\u05E8 \u05DE\u05DB\u05E8\u05D6..."}
        className="w-full max-w-sm rounded-lg border border-megido-border bg-megido-bg-card px-3 py-2 text-sm text-megido-text-heading placeholder:text-megido-text-muted/50 focus:border-megido-primary focus:outline-none focus:ring-1 focus:ring-megido-primary"
      />

      <p className="text-xs text-megido-text-muted">
        {`${filteredData.length} \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05E2\u05DD 2+ \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD`}
        {searchQuery && ` (\u05DE\u05EA\u05D5\u05DA ${multiLotData.length})`}
        {" \u2014 \u05DC\u05D7\u05E5 \u05DC\u05D4\u05E8\u05D7\u05D1\u05D4"}
      </p>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-megido-border bg-megido-bg-card">
        <table className="w-full text-sm" dir="rtl">
          <thead>
            <tr className="border-b-2 border-megido-border bg-megido-neutral-50">
              {LOT_COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "whitespace-nowrap px-3 py-2.5 text-xs font-semibold text-megido-text-heading",
                    col.align,
                  )}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredData.map((group) => {
              const isExpanded = expandedTenders.has(group.tenderId);
              return (
                <TenderGroup
                  key={group.tenderId}
                  group={group}
                  isExpanded={isExpanded}
                  onToggle={() => toggleTender(group.tenderId)}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// TenderGroup sub-component
// ---------------------------------------------------------------------------

interface TenderGroupProps {
  group: MultiLotTenderGroup;
  isExpanded: boolean;
  onToggle: () => void;
}

function TenderGroup({ group, isExpanded, onToggle }: TenderGroupProps) {
  const totalCols = LOT_COLUMNS.length;

  return (
    <>
      {/* Tender header row — clickable */}
      <tr
        onClick={onToggle}
        className={cn(
          "cursor-pointer border-b border-megido-border transition-colors",
          isExpanded
            ? "bg-megido-primary/5"
            : "hover:bg-megido-neutral-50/50",
        )}
      >
        <td colSpan={totalCols} className="px-3 py-2.5">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded text-xs transition-transform",
                isExpanded ? "rotate-90" : "",
              )}
            >
              {"\u25B6"}
            </span>
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-0.5">
              <span className="font-semibold text-megido-text-heading">
                {group.tenderName}
              </span>
              <span className="text-xs text-megido-text-muted">
                {group.city} &middot; {group.tenderType} &middot;{" "}
                {group.lots.length} {"\u05DE\u05EA\u05D7\u05DE\u05D9\u05DD"}
              </span>
            </div>
          </div>
        </td>
      </tr>

      {/* Lot rows — shown only when expanded */}
      {isExpanded &&
        group.lots.map((lot) => (
          <tr
            key={lot.tikId}
            className="border-b border-megido-neutral-100 bg-megido-bg-card hover:bg-megido-neutral-50/50"
          >
            <td className="px-3 py-2 pe-4 ps-8 text-start text-xs">
              {lot.mitchamName ?? `\u05EA\u05D9\u05E7 ${lot.tikId}`}
            </td>
            <td className="px-3 py-2 text-center text-xs tabular-nums">
              {fmtNumber(lot.capacityUnits)}
            </td>
            <td className="px-3 py-2 text-center text-xs tabular-nums">
              {fmtCurrency(lot.winningBid)}
            </td>
            <td className="px-3 py-2 text-center text-xs tabular-nums">
              {fmtCurrency(lot.devCosts)}
            </td>
            <td className="px-3 py-2 text-center text-xs tabular-nums">
              {lot.sqmPerUnit != null ? fmtNumber(lot.sqmPerUnit) : "\u2014"}
            </td>
            <td className="px-3 py-2 text-center text-xs tabular-nums">
              {fmtCurrency(lot.valuePerUnit)}
            </td>
            <td className="px-3 py-2 text-center text-xs tabular-nums">
              {fmtNumber(lot.numBids)}
            </td>
            <td className="px-3 py-2 text-center text-xs tabular-nums">
              {lot.winningRank != null ? lot.winningRank : "\u2014"}
            </td>
          </tr>
        ))}

      {/* Building rights sub-table — flat list of תאי שטח */}
      {isExpanded && group.buildingRights.length > 0 && (
        <tr className="border-b border-megido-border">
          <td colSpan={totalCols} className="p-0">
            <BuildingRightsSubTable rights={group.buildingRights} />
          </td>
        </tr>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// BuildingRightsSubTable — flat list of תאי שטח per tender
// ---------------------------------------------------------------------------

const RIGHTS_COLUMNS = [
  { key: "areaCondition", label: "\u05EA\u05D0 \u05E9\u05D8\u05D7", align: "text-center" as const },
  { key: "designation", label: "\u05D9\u05D9\u05E2\u05D5\u05D3", align: "text-start" as const },
  { key: "useType", label: "\u05E9\u05D9\u05DE\u05D5\u05E9", align: "text-start" as const },
  { key: "areaAbove", label: '\u05E2\u05D9\u05E7\u05E8\u05D9 (\u05DE"\u05E8)', align: "text-center" as const },
  { key: "areaService", label: '\u05E9\u05D9\u05E8\u05D5\u05EA (\u05DE"\u05E8)', align: "text-center" as const },
  { key: "units", label: '\u05D9\u05D7"\u05D3', align: "text-center" as const },
] as const;

function BuildingRightsSubTable({ rights }: { rights: BuildingRight[] }) {
  return (
    <div className="mx-6 my-3 overflow-hidden rounded-md border border-megido-neutral-200">
      <div className="flex items-center gap-2 border-b border-megido-neutral-200 bg-megido-neutral-50/80 px-3 py-1.5">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-megido-text-muted">
          {"\u05D6\u05DB\u05D5\u05D9\u05D5\u05EA \u05D1\u05E0\u05D9\u05D9\u05D4 \u2014 \u05EA\u05D0\u05D9 \u05E9\u05D8\u05D7"}
        </span>
        <span className="text-[10px] text-megido-text-muted/60">
          ({rights.length})
        </span>
      </div>
      <table className="w-full text-xs" dir="rtl">
        <thead>
          <tr className="border-b border-megido-neutral-200 bg-megido-neutral-50/40">
            {RIGHTS_COLUMNS.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "whitespace-nowrap px-2.5 py-1.5 text-[10px] font-semibold text-megido-text-muted",
                  col.align,
                )}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rights.map((r) => (
            <tr
              key={`${r.plan_number}-${r.plan_status}-${r.row_index}`}
              className="border-b border-megido-neutral-100 last:border-b-0"
            >
              <td className="px-2.5 py-1.5 text-center tabular-nums">
                {r.area_condition ?? "\u2014"}
              </td>
              <td className="px-2.5 py-1.5 text-start">
                {r.designation ?? "\u2014"}
              </td>
              <td className="px-2.5 py-1.5 text-start text-megido-text-muted">
                {r.use_type ?? "\u2014"}
              </td>
              <td className="px-2.5 py-1.5 text-center tabular-nums">
                {fmtArea(r.building_area_above)}
              </td>
              <td className="px-2.5 py-1.5 text-center tabular-nums">
                {fmtArea(r.building_area_above_service)}
              </td>
              <td className="px-2.5 py-1.5 text-center tabular-nums">
                {fmtNumber(r.housing_units)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
