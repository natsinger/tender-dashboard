/**
 * DetailViewer component.
 *
 * Expandable panel below the explorer table showing full tender details.
 * Features a select dropdown (format: "ID - Name (City)"), basic info
 * fields, location/gush/helka, building rights, brochure summary, and
 * lots data table. Uses useTenderLots() and useTenderBuildingRights()
 * hooks for sub-entity data.
 *
 * Mirrors the Streamlit explorer.py detail expander.
 */
"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DeadlineBadge } from "@/components/deadline-badge";
import { useTenderLots, useTenderBuildingRights, useTenderDetails } from "@/hooks";
import type { TikEntry } from "@/hooks/use-tender-details";
import { RMI_SITE_URL } from "@/lib/constants";
import type { ScoredTender, TenderWithComputed } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DetailViewerProps {
  /** All tenders available for selection. */
  tenders: TenderWithComputed[];
  /** Externally selected tender (from table row click). */
  selectedTender?: ScoredTender | null;
  /** Whether the panel should auto-expand. */
  autoExpand?: boolean;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function computeDaysRemaining(deadline: string | null): number | null {
  if (!deadline) return null;
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return null;
  const now = new Date();
  return Math.floor((d.getTime() - now.getTime()) / 86_400_000);
}

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

function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "\u2014";
  return `\u20AA${value.toLocaleString("he-IL")}`;
}

function formatLabel(tender: TenderWithComputed): string {
  const name =
    tender.tender_name && tender.tender_name.length > 50
      ? tender.tender_name.slice(0, 50) + "..."
      : tender.tender_name ?? "N/A";
  const city =
    tender.city && tender.city.length > 20
      ? tender.city.slice(0, 20) + "..."
      : tender.city ?? "N/A";
  return `${tender.tender_id} - ${name} (${city})`;
}

// ---------------------------------------------------------------------------
// Detail field row
// ---------------------------------------------------------------------------

function DetailField({
  label,
  value,
  children,
}: {
  label: string;
  value?: string | number | null;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2 py-1">
      <span className="shrink-0 text-sm font-semibold text-megido-neutral-700">
        {label}:
      </span>
      {children ?? (
        <span className="text-sm text-megido-neutral-600">
          {value != null ? String(value) : "\u2014"}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DetailViewer({
  tenders,
  selectedTender,
  autoExpand = false,
  className,
}: DetailViewerProps) {
  const [expanded, setExpanded] = useState(autoExpand);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // Resolve which tender ID to show (external selection takes priority)
  const activeTenderId = selectedTender?.tender_id ?? selectedId;

  // Find the full tender data
  const activeTender = useMemo(
    () => tenders.find((t) => t.tender_id === activeTenderId) ?? null,
    [tenders, activeTenderId],
  );

  // Fetch sub-entity data
  const { data: lots, isLoading: lotsLoading } = useTenderLots(activeTenderId);
  const { data: buildingRights, isLoading: rightsLoading } =
    useTenderBuildingRights(activeTenderId);
  const { data: rmiDetails, isLoading: detailsLoading } =
    useTenderDetails(activeTenderId);

  // Sort tenders for dropdown by deadline descending
  const sortedTenders = useMemo(
    () =>
      [...tenders].sort((a, b) => {
        const da = a.deadline ?? "";
        const db = b.deadline ?? "";
        return db.localeCompare(da);
      }),
    [tenders],
  );

  const daysRemaining = activeTender
    ? computeDaysRemaining(activeTender.deadline)
    : null;

  // Auto-expand when external selection changes
  const prevExpandRef = useMemo(() => {
    if (selectedTender && !expanded) {
      setExpanded(true);
    }
    return selectedTender?.tender_id;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTender?.tender_id]);
  // Suppress unused ref warning
  void prevExpandRef;

  return (
    <div dir="rtl" className={cn("rounded-md border", className)}>
      {/* Collapsible header */}
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold text-megido-text-heading hover:bg-megido-neutral-50"
        onClick={() => setExpanded((prev) => !prev)}
      >
        <span>
          {"\u05E6\u05E4\u05D9\u05D9\u05D4 \u05D1\u05E4\u05E8\u05D8\u05D9 \u05DE\u05DB\u05E8\u05D6"}
        </span>
        {expanded ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </button>

      {expanded && (
        <div className="border-t px-4 pb-4 pt-3 space-y-4">
          {/* Tender selector */}
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-xs font-medium text-megido-neutral-600">
                {"\u05D1\u05D7\u05E8 \u05DE\u05DB\u05E8\u05D6"}
              </label>
              <select
                className="w-full rounded-md border border-megido-border bg-megido-bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                value={activeTenderId ?? ""}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedId(val ? Number(val) : null);
                }}
              >
                <option value="">
                  {"\u05D1\u05D7\u05E8 \u05DE\u05DB\u05E8\u05D6..."}
                </option>
                {sortedTenders.map((t) => (
                  <option key={t.tender_id} value={t.tender_id}>
                    {formatLabel(t)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Detail content */}
          {activeTender ? (
            <div className="space-y-4">
              {/* Overview metrics row */}
              <div className="grid grid-cols-2 gap-x-8 gap-y-1 sm:grid-cols-4">
                <div className="rounded-md bg-megido-neutral-50 p-3 text-center">
                  <p className="text-xs text-megido-text-muted">
                    {"\u05DE\u05E1' \u05DE\u05DB\u05E8\u05D6"}
                  </p>
                  <p className="text-lg font-bold text-megido-text-heading">
                    {activeTender.tender_id}
                  </p>
                </div>
                <div className="rounded-md bg-megido-neutral-50 p-3 text-center">
                  <p className="text-xs text-megido-text-muted">
                    {"\u05E1\u05D8\u05D8\u05D5\u05E1"}
                  </p>
                  <p className="text-lg font-bold text-megido-text-heading">
                    {activeTender.status ?? "\u2014"}
                  </p>
                </div>
                <div className="rounded-md bg-megido-neutral-50 p-3 text-center">
                  <p className="text-xs text-megido-text-muted">
                    {'\u05D9\u05D7"\u05D3'}
                  </p>
                  <p className="text-lg font-bold text-megido-text-heading">
                    {activeTender.units != null
                      ? activeTender.units.toLocaleString("he-IL")
                      : "\u2014"}
                  </p>
                </div>
                <div className="rounded-md bg-megido-neutral-50 p-3 text-center">
                  <p className="text-xs text-megido-text-muted">
                    {"\u05D9\u05DE\u05D9\u05DD \u05DC\u05E1\u05D2\u05D9\u05E8\u05D4"}
                  </p>
                  <div className="flex items-center justify-center gap-2">
                    <p className="text-lg font-bold text-megido-text-heading">
                      {daysRemaining ?? "\u2014"}
                    </p>
                    <DeadlineBadge daysRemaining={daysRemaining} />
                  </div>
                </div>
              </div>

              {/* Basic info grid */}
              <div className="grid grid-cols-1 gap-x-8 gap-y-0.5 sm:grid-cols-2">
                <DetailField
                  label={"\u05E9\u05DD \u05DE\u05DB\u05E8\u05D6"}
                  value={activeTender.tender_name}
                />
                <DetailField
                  label={"\u05E2\u05D9\u05E8"}
                  value={activeTender.city}
                />
                <DetailField
                  label={"\u05DE\u05D7\u05D5\u05D6"}
                  value={activeTender.region}
                />
                <DetailField
                  label={"\u05E1\u05D5\u05D2"}
                  value={activeTender.tender_type}
                />
                <DetailField
                  label={"\u05D9\u05D9\u05E2\u05D5\u05D3"}
                  value={activeTender.purpose}
                />
                <DetailField
                  label={"\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4"}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-megido-neutral-600">
                      {formatDate(activeTender.deadline)}
                    </span>
                    <DeadlineBadge daysRemaining={daysRemaining} />
                  </div>
                </DetailField>

                {/* Booklet status */}
                <DetailField label={"\u05D7\u05D5\u05D1\u05E8\u05EA"}>
                  {activeTender.published_booklet ? (
                    <Badge
                      variant="secondary"
                      className="bg-emerald-50 text-emerald-700 border-emerald-200"
                    >
                      {"\u05D9\u05E9 \u05D7\u05D5\u05D1\u05E8\u05EA"}
                    </Badge>
                  ) : (
                    <Badge variant="outline">
                      {"\u05D0\u05D9\u05DF \u05D7\u05D5\u05D1\u05E8\u05EA"}
                    </Badge>
                  )}
                </DetailField>
              </div>

              {/* Location (shchuna) */}
              {activeTender.location && (
                <DetailField
                  label={"\u05E9\u05DB\u05D5\u05E0\u05D4"}
                  value={activeTender.location}
                />
              )}

              {/* Gush / Helka */}
              {activeTender.gush && (
                <DetailField
                  label={"\u05D2\u05D5\u05E9/\u05D7\u05DC\u05E7\u05D4"}
                  value={`${activeTender.gush} / ${activeTender.helka ?? "\u2014"}`}
                />
              )}

              {/* Land & Pricing Data — only shown when no Supabase lots exist (fallback) */}
              {(!lots || lots.length === 0) && (
              <div className="border-t pt-3">
                <h4 className="mb-2 text-sm font-semibold text-megido-text-heading">
                  {"\u05E0\u05EA\u05D5\u05E0\u05D9 \u05E7\u05E8\u05E7\u05E2 \u05D5\u05DE\u05D7\u05D9\u05E8\u05D9\u05DD"}
                </h4>

                {detailsLoading ? (
                  <div className="h-16 animate-pulse rounded bg-megido-neutral-200" />
                ) : rmiDetails?.Tik && rmiDetails.Tik.length > 0 ? (
                  <div className="space-y-3">
                    {rmiDetails.Tik.map((tik: TikEntry, idx: number) => (
                      <div key={tik.TikID ?? idx}>
                        {rmiDetails.Tik.length > 1 && (
                          <p className="mb-1 text-xs font-semibold text-megido-neutral-600">
                            {'\u05DE\u05D6\u05D4\u05D4 \u05E8\u05DE"\u05D9'} {tik.MitchamName ?? idx + 1}
                          </p>
                        )}

                        {/* Metrics grid */}
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                          <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                            <p className="text-xs text-megido-text-muted">
                              {'\u05E9\u05D8\u05D7 (\u05DE"\u05E8)'}
                            </p>
                            <p className="font-bold text-megido-text-heading">
                              {tik.Shetach
                                ? tik.Shetach.toLocaleString("he-IL")
                                : "\u2014"}
                            </p>
                          </div>
                          <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                            <p className="text-xs text-megido-text-muted">
                              {"\u05DE\u05D7\u05D9\u05E8 \u05E1\u05E3 (\u20AA)"}
                            </p>
                            <p className="font-bold text-megido-text-heading">
                              {tik.MechirSaf
                                ? tik.MechirSaf.toLocaleString("he-IL")
                                : "\u2014"}
                            </p>
                          </div>
                          <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                            <p className="text-xs text-megido-text-muted">
                              {"\u05E9\u05D5\u05DE\u05D4 (\u20AA)"}
                            </p>
                            <p className="font-bold text-megido-text-heading">
                              {tik.mechirShuma
                                ? tik.mechirShuma.toLocaleString("he-IL")
                                : "\u2014"}
                            </p>
                          </div>
                          <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                            <p className="text-xs text-megido-text-muted">
                              {"\u05E2\u05DC\u05D5\u05D9\u05D5\u05EA \u05E4\u05D9\u05EA\u05D5\u05D7 (\u20AA)"}
                            </p>
                            <p className="font-bold text-megido-text-heading">
                              {tik.HotzaotPituach
                                ? tik.HotzaotPituach.toLocaleString("he-IL")
                                : "\u2014"}
                            </p>
                          </div>
                          <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                            <p className="text-xs text-megido-text-muted">
                              {"\u05E2\u05E8\u05D1\u05D5\u05EA (\u20AA)"}
                            </p>
                            <p className="font-bold text-megido-text-heading">
                              {tik.SchumArvut
                                ? tik.SchumArvut.toLocaleString("he-IL")
                                : "\u2014"}
                            </p>
                          </div>
                          <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                            <p className="text-xs text-megido-text-muted">
                              {'\u05D9\u05D7"\u05D3 \u05D1\u05DE\u05EA\u05D7\u05DD'}
                            </p>
                            <p className="font-bold text-megido-text-heading">
                              {tik.Kibolet
                                ? tik.Kibolet.toLocaleString("he-IL")
                                : "\u2014"}
                            </p>
                          </div>
                        </div>

                        {/* Gush/Helka + Plan */}
                        {(tik.GushHelka?.length > 0 ||
                          tik.TochnitMigrash?.length > 0) && (
                          <p className="mt-1 text-xs text-megido-text-muted">
                            {tik.GushHelka?.map(
                              (gh) => `\u05D2\u05D5\u05E9 ${gh.Gush} \u05D7\u05DC\u05E7\u05D4 ${gh.Helka}`,
                            ).join(" | ")}
                            {tik.GushHelka?.length > 0 &&
                              tik.TochnitMigrash?.length > 0 &&
                              " | "}
                            {tik.TochnitMigrash?.map(
                              (tm) =>
                                `\u05EA\u05D1"\u05E2 ${tm.Tochnit?.trim()}${tm.MigrashName?.trim() ? ` \u05DE\u05D2\u05E8\u05E9 ${tm.MigrashName.trim()}` : ""}` ,
                            ).join(" | ")}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-megido-text-muted">
                    {"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9 \u05E7\u05E8\u05E7\u05E2 \u05D5\u05DE\u05D7\u05D9\u05E8\u05D9\u05DD"}
                  </p>
                )}
              </div>
              )}

              {/* Building rights section */}
              <div className="border-t pt-3">
                <h4 className="mb-2 text-sm font-semibold text-megido-text-heading">
                  {"\u05D6\u05DB\u05D5\u05D9\u05D5\u05EA \u05D1\u05E0\u05D9\u05D9\u05D4"}
                </h4>

                {/* Extraction status */}
                {activeTender.extraction_status && (
                  <p className="mb-2 text-xs text-megido-text-muted">
                    {"\u05E1\u05D8\u05D8\u05D5\u05E1 \u05D7\u05D9\u05DC\u05D5\u05E5"}:{" "}
                    {activeTender.extraction_status}
                  </p>
                )}

                {/* Plan number */}
                {activeTender.plan_number && (
                  <p className="mb-2 text-sm text-megido-neutral-600">
                    <span className="font-semibold">
                      {'\u05EA\u05D1"\u05E2'}:
                    </span>{" "}
                    {activeTender.plan_number}
                  </p>
                )}

                {/* Brochure summary */}
                {activeTender.brochure_summary && (
                  <div className="mb-2 rounded-md bg-megido-neutral-50 p-3">
                    <p className="mb-1 text-xs font-medium text-megido-text-muted">
                      {"\u05E1\u05D9\u05DB\u05D5\u05DD \u05D7\u05D5\u05D1\u05E8\u05EA \u05DE\u05DB\u05E8\u05D6"}
                    </p>
                    <p className="whitespace-pre-line text-sm text-megido-neutral-600">
                      {activeTender.brochure_summary}
                    </p>
                  </div>
                )}

                {rightsLoading ? (
                  <div className="h-12 animate-pulse rounded bg-megido-neutral-200" />
                ) : buildingRights && buildingRights.length > 0 ? (
                  <div className="max-h-48 overflow-y-auto rounded-md border">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b bg-megido-neutral-50">
                          <th className="px-2 py-1 text-end">
                            {"\u05D9\u05E2\u05D5\u05D3"}
                          </th>
                          <th className="px-2 py-1 text-end">
                            {"\u05E9\u05D9\u05DE\u05D5\u05E9"}
                          </th>
                          <th className="px-2 py-1 text-end">
                            {'\u05E9\u05D8\u05D7 \u05DE\u05D2\u05E8\u05E9 (\u05DE"\u05E8)'}
                          </th>
                          <th className="px-2 py-1 text-end">
                            {'\u05D9\u05D7"\u05D3'}
                          </th>
                          <th className="px-2 py-1 text-end">
                            {"\u05E7\u05D5\u05DE\u05D5\u05EA"}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {buildingRights.map((r, i) => (
                          <tr key={i} className="border-b last:border-0">
                            <td className="px-2 py-1">
                              {r.designation ?? "\u2014"}
                            </td>
                            <td className="px-2 py-1">
                              {r.use_type ?? "\u2014"}
                            </td>
                            <td className="px-2 py-1">
                              {r.plot_size_absolute?.toLocaleString("he-IL") ??
                                "\u2014"}
                            </td>
                            <td className="px-2 py-1">
                              {r.housing_units ?? "\u2014"}
                            </td>
                            <td className="px-2 py-1">
                              {r.floors_above ?? "\u2014"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-megido-text-muted">
                    {"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9 \u05D6\u05DB\u05D5\u05D9\u05D5\u05EA \u05D1\u05E0\u05D9\u05D9\u05D4"}
                  </p>
                )}
              </div>

              {/* Lots data section — unified table (Supabase lots enriched with live API data) */}
              <div className="border-t pt-3">
                <h4 className="mb-2 text-sm font-semibold text-megido-text-heading">
                  {"\u05E0\u05EA\u05D5\u05E0\u05D9 \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD"}
                  {lots && lots.length > 0 && (
                    <span className="me-1 text-xs font-normal text-megido-text-muted">
                      ({lots.length})
                    </span>
                  )}
                </h4>

                {/* Max lots badge */}
                {activeTender.max_lots_per_bidder != null &&
                  activeTender.max_lots_per_bidder > 0 && (
                    <div className="mb-2 inline-block rounded-full border border-orange-300 bg-orange-50 px-3 py-1 text-xs font-semibold text-orange-700">
                      {"\u05D4\u05D2\u05D1\u05DC\u05EA \u05D4\u05D2\u05E9\u05D4: \u05E2\u05D3"}{" "}
                      {activeTender.max_lots_per_bidder}{" "}
                      {"\u05DE\u05EA\u05D7\u05DE\u05D9\u05DD"}
                    </div>
                  )}

                {lotsLoading ? (
                  <div className="h-12 animate-pulse rounded bg-megido-neutral-200" />
                ) : lots && lots.length > 0 ? (
                  <>
                    <div className="max-h-80 overflow-y-auto rounded-md border">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b bg-megido-neutral-50">
                            <th className="px-2 py-1 text-end">
                              {"\u05DE\u05EA\u05D7\u05DD"}
                            </th>
                            {lots.some((l) => l.mitcham_name) && (
                              <th className="px-2 py-1 text-end">
                                {'\u05DE\u05D6\u05D4\u05D4 \u05E8\u05DE"\u05D9'}
                              </th>
                            )}
                            <th className="px-2 py-1 text-end">
                              {"\u05D2\u05D5\u05E9"}
                            </th>
                            <th className="px-2 py-1 text-end">
                              {"\u05D7\u05DC\u05E7\u05D4"}
                            </th>
                            <th className="px-2 py-1 text-end">
                              {'\u05E9\u05D8\u05D7 \u05D1\u05DE"\u05E8'}
                            </th>
                            <th className="px-2 py-1 text-end">
                              {'\u05E1\u05D4"\u05DB \u05D9\u05D7"\u05D3'}
                            </th>
                            <th className="px-2 py-1 text-end">
                              {"\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4"}
                            </th>
                            <th className="px-2 py-1 text-end">
                              {"\u05E9\u05D5\u05E7 \u05D7\u05D5\u05E4\u05E9\u05D9"}
                            </th>
                            <th className="px-2 py-1 text-end">
                              {"\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D9\u05E0\u05D9\u05DE\u05D5\u05DD"}
                            </th>
                            <th className="px-2 py-1 text-end">
                              {"\u05E9\u05D5\u05DE\u05D4"}
                            </th>
                            <th className="px-2 py-1 text-end">
                              {"\u05E2\u05E8\u05D1\u05D5\u05EA"}
                            </th>
                            <th className="px-2 py-1 text-end">
                              {"\u05D6\u05D5\u05DB\u05D4"}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {lots.map((lot, i) => {
                            /* Match this lot to a live API Tik entry for enrichment fields */
                            const tikMatch = rmiDetails?.Tik?.find(
                              (tik: TikEntry) =>
                                lot.mitcham_name != null &&
                                String(tik.MitchamName) === lot.mitcham_name
                            ) ?? rmiDetails?.Tik?.[i] ?? null;
                            return (
                            <tr key={i} className="border-b last:border-0">
                              <td className="px-2 py-1">
                                {lot.lot_number ?? "\u2014"}
                              </td>
                              {lots.some((l) => l.mitcham_name) && (
                                <td className="px-2 py-1">
                                  {lot.mitcham_name ?? "\u2014"}
                                </td>
                              )}
                              <td className="px-2 py-1">
                                {lot.gush ?? tikMatch?.GushHelka?.map((gh) => gh.Gush).join(", ") ?? "\u2014"}
                              </td>
                              <td className="px-2 py-1">
                                {lot.helka ?? tikMatch?.GushHelka?.map((gh) => gh.Helka).join(", ") ?? "\u2014"}
                              </td>
                              <td className="px-2 py-1">
                                {lot.area_sqm?.toLocaleString("he-IL") ??
                                  tikMatch?.Shetach?.toLocaleString("he-IL") ??
                                  "\u2014"}
                              </td>
                              <td className="px-2 py-1">
                                {(lot.units_target_price ?? 0) + (lot.units_free_market ?? 0) > 0
                                    ? (lot.units_target_price ?? 0) + (lot.units_free_market ?? 0)
                                    : lot.total_units ?? "\u2014"}
                              </td>
                              <td className="px-2 py-1">
                                {lot.units_target_price ?? "\u2014"}
                              </td>
                              <td className="px-2 py-1">
                                {lot.units_free_market ?? "\u2014"}
                              </td>
                              <td className="px-2 py-1">
                                {formatCurrency(lot.min_price ?? tikMatch?.MechirSaf)}
                              </td>
                              <td className="px-2 py-1">
                                {formatCurrency(lot.sqm_value_appraisal ?? tikMatch?.mechirShuma)}
                              </td>
                              <td className="px-2 py-1">
                                {formatCurrency(lot.guarantee_amount ?? tikMatch?.SchumArvut)}
                              </td>
                              <td className="px-2 py-1">
                                {lot.winner_name ?? tikMatch?.ShemZoche ?? "\u2014"}
                              </td>
                            </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    {/* Lot summary metrics */}
                    <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                      <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                        <p className="text-xs text-megido-text-muted">
                          {'\u05E1\u05D4"\u05DB \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD'}
                        </p>
                        <p className="font-bold text-megido-text-heading">
                          {lots.length}
                        </p>
                      </div>
                      <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                        <p className="text-xs text-megido-text-muted">
                          {'\u05E1\u05D4"\u05DB \u05D9\u05D7"\u05D3'}
                        </p>
                        <p className="font-bold text-megido-text-heading">
                          {lots
                            .reduce(
                              (sum, l) => {
                                const split = (Number(l.units_target_price) || 0) + (Number(l.units_free_market) || 0);
                                return sum + (split > 0 ? split : Number(l.total_units) || 0);
                              },
                              0,
                            )
                            .toLocaleString("he-IL")}
                        </p>
                      </div>
                      <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                        <p className="text-xs text-megido-text-muted">
                          {'\u05D9\u05D7"\u05D3 \u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4'}
                        </p>
                        <p className="font-bold text-megido-text-heading">
                          {lots
                            .reduce(
                              (sum, l) =>
                                sum + (Number(l.units_target_price) || 0),
                              0,
                            )
                            .toLocaleString("he-IL")}
                        </p>
                      </div>
                      <div className="rounded bg-megido-neutral-50 px-3 py-2 text-center">
                        <p className="text-xs text-megido-text-muted">
                          {'\u05D9\u05D7"\u05D3 \u05E9\u05D5\u05E7 \u05D7\u05D5\u05E4\u05E9\u05D9'}
                        </p>
                        <p className="font-bold text-megido-text-heading">
                          {lots
                            .reduce(
                              (sum, l) =>
                                sum + (Number(l.units_free_market) || 0),
                              0,
                            )
                            .toLocaleString("he-IL")}
                        </p>
                      </div>
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-megido-text-muted">
                    {"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9 \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD \u05DC\u05DE\u05DB\u05E8\u05D6 \u05D6\u05D4"}
                  </p>
                )}
              </div>

              {/* RMI link */}
              <div className="border-t pt-3">
                <Button variant="outline" size="sm" asChild>
                  <a
                    href={`${RMI_SITE_URL}/${activeTender.tender_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5"
                  >
                    {'\u05E6\u05E4\u05D4 \u05D1\u05D0\u05EA\u05E8 \u05E8\u05DE"\u05D9'}
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </Button>
              </div>
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-megido-text-muted">
              {"\u05D1\u05D7\u05E8 \u05DE\u05DB\u05E8\u05D6 \u05DE\u05D4\u05E8\u05E9\u05D9\u05DE\u05D4 \u05D0\u05D5 \u05DC\u05D7\u05E5 \u05E2\u05DC \u05E9\u05D5\u05E8\u05D4 \u05D1\u05D8\u05D1\u05DC\u05D4"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
