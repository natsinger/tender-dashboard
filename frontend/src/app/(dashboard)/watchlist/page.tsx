/**
 * Watchlist Management page (רשימת מעקב).
 *
 * Dedicated page for managing personal and team watchlists, viewing
 * team-watched tenders in a table, and updating review statuses.
 *
 * Two collapsible card sections:
 *   1. רשימת מעקב — team watchlist add/remove/notes management
 *   2. מכרזים מועדפים — team watchlist table + add tender + review status editor
 */
"use client";

import { useMemo, useState, useCallback } from "react";
import { ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Download } from "lucide-react";
import * as XLSX from "xlsx";

import { PageHeader } from "@/components/page-header";
import { WatchlistManager } from "@/components/watchlist-manager";
import { ReviewStatusEditor } from "@/components/review-status-editor";
import { ExpiredTendersTable } from "@/components/watchlist/expired-tenders-table";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  useActiveTenders,
  useReviewStatuses,
  useTeamWatchlist,
} from "@/hooks";
import { RELEVANT_TENDER_TYPES, TEAM_EMAIL } from "@/lib/constants";
import { useAuthStore } from "@/stores/auth-store";
import type { Tender, WatchlistItemWithTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Format an ISO date string to dd/MM using Hebrew locale. */
function formatDeadline(deadline: string | null): string {
  if (!deadline) return "\u2014";
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return "\u2014";
  return d.toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit" });
}

/** Map review status string to a badge variant. */
function getReviewBadgeVariant(
  status: string,
): "default" | "secondary" | "outline" | "destructive" {
  switch (status) {
    case "\u05D0\u05D5\u05E9\u05E8 \u05D1\u05E4\u05D5\u05E8\u05D5\u05DD":
      return "default";
    case "\u05D4\u05D5\u05E6\u05D2 \u05D1\u05E4\u05D5\u05E8\u05D5\u05DD":
      return "secondary";
    case "\u05D1\u05D3\u05D9\u05E7\u05D4 \u05DE\u05E2\u05DE\u05D9\u05E7\u05D4":
      return "secondary";
    case "\u05E1\u05E7\u05D9\u05E8\u05D4 \u05E8\u05D0\u05E9\u05D5\u05E0\u05D9\u05EA":
      return "outline";
    default:
      return "destructive";
  }
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function WatchlistPage() {
  const userEmail = useAuthStore((s) => s.email) ?? "";
  const [watchlistOpen, setWatchlistOpen] = useState(true);
  const [favoritesOpen, setFavoritesOpen] = useState(true);

  // ---- Data hooks ----

  const { data: activeTenders, isLoading: tendersLoading } =
    useActiveTenders();

  // Filter to relevant tender types for the WatchlistManager select dropdown
  const relevantTenders = useMemo<Tender[]>(
    () =>
      (activeTenders ?? []).filter((t) =>
        RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? 0),
      ),
    [activeTenders],
  );

  // Team watchlist
  const { data: teamWatchlist, isLoading: teamLoading } = useTeamWatchlist();

  // Team tender IDs for review statuses
  const teamTenderIds = useMemo(
    () =>
      (teamWatchlist ?? [])
        .filter(
          (item): item is WatchlistItemWithTender & { tender: Tender } =>
            item.tender != null,
        )
        .map((item) => item.tender_id),
    [teamWatchlist],
  );

  // Tenders in team watchlist (for the review editor tender select)
  const teamTenders = useMemo<Tender[]>(
    () =>
      (teamWatchlist ?? [])
        .filter(
          (item): item is WatchlistItemWithTender & { tender: Tender } =>
            item.tender != null,
        )
        .map((item) => item.tender),
    [teamWatchlist],
  );

  const { data: reviewMap } = useReviewStatuses(teamTenderIds);

  // ---- Derived data for Card 2 table ----

  const teamWatchlistWithTender = useMemo(
    () =>
      (teamWatchlist ?? []).filter(
        (item): item is WatchlistItemWithTender & { tender: Tender } =>
          item.tender != null,
      ),
    [teamWatchlist],
  );

  // Split into active (deadline in future or no deadline) vs expired
  const { activeWatchlist, expiredWatchlist } = useMemo(() => {
    const now = new Date();
    const active: (WatchlistItemWithTender & { tender: Tender })[] = [];
    const expired: (WatchlistItemWithTender & { tender: Tender })[] = [];

    for (const item of teamWatchlistWithTender) {
      const deadline = item.tender.deadline;
      if (deadline && new Date(deadline) <= now) {
        expired.push(item);
      } else {
        active.push(item);
      }
    }

    return { activeWatchlist: active, expiredWatchlist: expired };
  }, [teamWatchlistWithTender]);

  // ---- Export to Excel ----

  const exportToExcel = useCallback(() => {
    const rows = teamWatchlistWithTender.map((item) => {
      const t = item.tender;
      const review = reviewMap?.[item.tender_id];
      return {
        "\u05DE\u05E1\u05E4\u05E8 \u05DE\u05DB\u05E8\u05D6": t.tender_id,
        "\u05E9\u05DD \u05DE\u05DB\u05E8\u05D6": t.tender_name ?? "",
        "\u05E2\u05D9\u05E8": t.city ?? "",
        "\u05DE\u05D7\u05D5\u05D6": t.region ?? "",
        "\u05DE\u05D9\u05E7\u05D5\u05DD": t.location ?? "",
        "\u05E1\u05D5\u05D2 \u05DE\u05DB\u05E8\u05D6": t.tender_type ?? "",
        "\u05D9\u05D9\u05E2\u05D5\u05D3": t.purpose ?? "",
        "\u05E1\u05D8\u05D8\u05D5\u05E1": t.status ?? "",
        '\u05D9\u05D7"\u05D3': t.units ?? "",
        '\u05E9\u05D8\u05D7 (מ"ר)': t.area_sqm ?? "",
        '\u05E9\u05D8\u05D7 \u05E7\u05E8\u05E7\u05E2 (מ"ר)': t.land_area_sqm ?? "",
        "\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D9\u05E0\u05D9\u05DE\u05D5\u05DD": t.min_price ?? "",
        "\u05EA\u05D0\u05E8\u05D9\u05DA \u05E4\u05E8\u05E1\u05D5\u05DD": t.publish_date ?? "",
        "\u05DE\u05D5\u05E2\u05D3 \u05D0\u05D7\u05E8\u05D5\u05DF": t.deadline ?? "",
        "\u05EA\u05D0\u05E8\u05D9\u05DA \u05D5\u05E2\u05D3\u05D4": t.committee_date ?? "",
        "\u05EA\u05D0\u05E8\u05D9\u05DA \u05E4\u05EA\u05D9\u05D7\u05D4": t.opening_date ?? "",
        "\u05D7\u05D5\u05D1\u05E8\u05EA \u05DE\u05DB\u05E8\u05D6": t.published_booklet ? "\u05DB\u05DF" : "\u05DC\u05D0",
        "\u05DE\u05DE\u05D5\u05E7\u05D3": t.targeted ? "\u05DB\u05DF" : "\u05DC\u05D0",
        "\u05D2\u05D5\u05E9": t.gush ?? "",
        "\u05D7\u05DC\u05E7\u05D4": t.helka ?? "",
        "\u05EA\u05DB\u05E0\u05D9\u05EA": t.plan_number ?? "",
        "\u05E7\u05D4\u05DC \u05D9\u05E2\u05D3": t.target_audience ?? "",
        "\u05E6\u05D5\u05E8\u05EA \u05E8\u05DB\u05D9\u05E9\u05D4": t.acquisition_form ?? "",
        "\u05D3\u05DE\u05D9 \u05D4\u05E9\u05EA\u05EA\u05E4\u05D5\u05EA": t.participation_fee ?? "",
        "\u05DE\u05E1\' \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD": t.lot_count ?? "",
        "\u05DE\u05E7\u05E1\u05D9\u05DE\u05D5\u05DD \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD \u05DC\u05DE\u05E6\u05D9\u05E2": t.max_lots_per_bidder ?? "",
        "\u05DE\u05E9\u05DA \u05DE\u05DB\u05E8\u05D6 (\u05D9\u05DE\u05D9\u05DD)": t.tender_duration_days ?? "",
        "\u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4": review?.status ?? "\u05DC\u05D0 \u05E0\u05E1\u05E7\u05E8",
        "\u05D4\u05E2\u05E8\u05D5\u05EA \u05E1\u05E7\u05D9\u05E8\u05D4": review?.notes ?? "",
      };
    });

    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD");

    const today = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(wb, `watchlist_${today}.xls`, { bookType: "xls" });
  }, [teamWatchlistWithTender, reviewMap]);

  // ---- Pagination for active watchlist ----
  const PAGE_SIZE = 10;
  const [activePage, setActivePage] = useState(0);
  const activePageCount = Math.ceil(activeWatchlist.length / PAGE_SIZE);
  const pagedActiveWatchlist = useMemo(
    () => activeWatchlist.slice(activePage * PAGE_SIZE, (activePage + 1) * PAGE_SIZE),
    [activeWatchlist, activePage],
  );

  // ---- Loading state ----

  const isWatchlistLoading = tendersLoading || teamLoading;

  return (
    <div dir="rtl" className="space-y-6">
      {/* Page header */}
      <PageHeader
        title={"\u05E8\u05E9\u05D9\u05DE\u05EA \u05DE\u05E2\u05E7\u05D1"}
        subtitle={
          "\u05E0\u05D9\u05D4\u05D5\u05DC \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD \u05D5\u05DE\u05E2\u05E7\u05D1"
        }
      />

      {/* Card 1: Watchlist Management */}
      <section className="rounded-xl border border-megido-border bg-megido-bg-card shadow-sm">
        <button
          type="button"
          onClick={() => setWatchlistOpen((prev) => !prev)}
          className="flex w-full items-center justify-between p-4 transition-colors hover:bg-megido-neutral-50/50 md:p-6"
        >
          <h3 className="text-lg font-semibold text-megido-text-heading">
            {"\u05E8\u05E9\u05D9\u05DE\u05EA \u05DE\u05E2\u05E7\u05D1"}
          </h3>
          {watchlistOpen ? (
            <ChevronUp className="h-5 w-5 text-megido-text-muted" />
          ) : (
            <ChevronDown className="h-5 w-5 text-megido-text-muted" />
          )}
        </button>

        {watchlistOpen && (
          <div className="px-4 pb-4 md:px-6 md:pb-6">
            <Separator className="mb-4" />

            <WatchlistManager
              email={TEAM_EMAIL}
              isTeam
              tenders={relevantTenders}
              watchlistItems={teamWatchlist ?? []}
              isLoading={isWatchlistLoading}
            />
          </div>
        )}
      </section>

      {/* Card 2: Team Watched Tenders Table + Review Editor */}
      <section className="rounded-xl border border-megido-border bg-megido-bg-card shadow-sm">
        <div className="flex items-center justify-between p-4 md:p-6">
          <button
            type="button"
            onClick={() => setFavoritesOpen((prev) => !prev)}
            className="flex items-center gap-2 transition-colors hover:text-megido-primary"
          >
            <h3 className="text-lg font-semibold text-megido-text-heading">
              {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD"}
              <span className="mr-2 text-base font-normal text-megido-text-muted">
                ({activeWatchlist.length})
              </span>
            </h3>
            {favoritesOpen ? (
              <ChevronUp className="h-5 w-5 text-megido-text-muted" />
            ) : (
              <ChevronDown className="h-5 w-5 text-megido-text-muted" />
            )}
          </button>

          {/* Export button — top left (RTL end) */}
          <button
            type="button"
            onClick={exportToExcel}
            disabled={teamWatchlistWithTender.length === 0}
            className="flex items-center gap-1.5 rounded-lg border border-megido-border px-3 py-1.5 text-xs font-medium text-megido-text-heading transition-colors hover:bg-megido-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Download className="h-3.5 w-3.5" />
            {"\u05D9\u05D9\u05E6\u05D5\u05D0 \u05DC\u05D0\u05E7\u05E1\u05DC"}
          </button>
        </div>

        {favoritesOpen && (
          <div className="px-4 pb-4 md:px-6 md:pb-6">
            <Separator className="mb-4" />

            {/* Add tender to preferred list */}
            <WatchlistManager
              email={TEAM_EMAIL}
              isTeam
              tenders={relevantTenders}
              watchlistItems={teamWatchlist ?? []}
              isLoading={isWatchlistLoading}
            />

            <Separator className="my-4" />

            {teamLoading ? (
              /* Loading skeleton */
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-10 animate-pulse rounded-md bg-megido-neutral-100"
                  />
                ))}
              </div>
            ) : activeWatchlist.length === 0 ? (
              <p className="py-4 text-sm text-megido-text-muted">
                {"אין מכרזים מועדפים"}
              </p>
            ) : (
              <>
                {/* Team watchlist table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" dir="rtl">
                    <thead>
                      <tr className="border-b border-megido-border text-xs font-medium text-megido-text-muted">
                        <th className="px-2 py-2 text-right">
                          {"\u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4"}
                        </th>
                        <th className="px-2 py-2 text-right">
                          {"\u05D4\u05E2\u05E8\u05D5\u05EA"}
                        </th>
                        <th className="px-2 py-2 text-right">
                          {"\u05DE\u05D5\u05E2\u05D3 \u05D0\u05D7\u05E8\u05D5\u05DF"}
                        </th>
                        <th className="px-2 py-2 text-right">
                          {"\u05E1\u05D5\u05D2"}
                        </th>
                        <th className="px-2 py-2 text-right">
                          {'\u05D9\u05D7"\u05D3'}
                        </th>
                        <th className="px-2 py-2 text-right">
                          {"\u05E2\u05D9\u05E8"}
                        </th>
                        <th className="px-2 py-2 text-right">
                          {"\u05E9\u05DD \u05DE\u05DB\u05E8\u05D6"}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {pagedActiveWatchlist.map((item) => {
                        const tender = item.tender;
                        const review = reviewMap?.[item.tender_id];
                        const statusText =
                          review?.status ??
                          "\u05DC\u05D0 \u05E0\u05E1\u05E7\u05E8";

                        return (
                          <tr
                            key={item.tender_id}
                            className="border-b border-megido-border/50 transition-colors hover:bg-megido-neutral-50/50"
                          >
                            {/* Review status */}
                            <td className="px-2 py-2">
                              <Badge
                                variant={getReviewBadgeVariant(statusText)}
                                className="text-[0.64rem]"
                              >
                                {statusText}
                              </Badge>
                            </td>

                            {/* Review notes */}
                            <td className="px-2 py-2 text-xs text-megido-text-muted">
                              {review?.notes || "\u2014"}
                            </td>

                            {/* Deadline */}
                            <td className="px-2 py-2 text-xs">
                              {formatDeadline(tender.deadline)}
                            </td>

                            {/* Type / purpose */}
                            <td className="px-2 py-2 text-xs">
                              {tender.purpose ?? "\u2014"}
                            </td>

                            {/* Units */}
                            <td className="px-2 py-2 text-xs">
                              {tender.units ?? "\u2014"}
                            </td>

                            {/* City */}
                            <td className="px-2 py-2 text-xs">
                              {tender.city ?? "\u2014"}
                            </td>

                            {/* Tender name (truncated) */}
                            <td className="max-w-[200px] truncate px-2 py-2 text-xs font-medium">
                              {(tender.tender_name ?? String(item.tender_id)).slice(
                                0,
                                40,
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {activePageCount > 1 && (
                  <div className="mt-3 flex items-center justify-between text-xs text-megido-text-muted">
                    <span>
                      {activePage * PAGE_SIZE + 1}–{Math.min((activePage + 1) * PAGE_SIZE, activeWatchlist.length)} {"\u05DE\u05EA\u05D5\u05DA"} {activeWatchlist.length}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setActivePage((p) => Math.max(0, p - 1))}
                        disabled={activePage === 0}
                        className="rounded border border-megido-border p-1 transition-colors hover:bg-megido-neutral-50 disabled:opacity-40"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setActivePage((p) => Math.min(activePageCount - 1, p + 1))}
                        disabled={activePage >= activePageCount - 1}
                        className="rounded border border-megido-border p-1 transition-colors hover:bg-megido-neutral-50 disabled:opacity-40"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}

                {/* Review Status Editor */}
                <Separator className="my-4" />

                <div>
                  <h4 className="mb-3 text-sm font-semibold text-megido-text-heading">
                    {"\u05E2\u05D3\u05DB\u05D5\u05DF \u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4"}
                  </h4>
                  <ReviewStatusEditor
                    email={userEmail}
                    tenders={teamTenders}
                    reviewMap={reviewMap ?? {}}
                  />
                </div>
              </>
            )}
          </div>
        )}
      </section>

      {/* Card 3: Expired Tenders */}
      {expiredWatchlist.length > 0 && (
        <section className="rounded-xl border border-megido-border bg-megido-bg-card p-4 shadow-sm md:p-6">
          <ExpiredTendersTable
            items={expiredWatchlist}
            reviewMap={reviewMap}
            userEmail={userEmail}
          />
        </section>
      )}
    </div>
  );
}
