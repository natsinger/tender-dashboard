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

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { WatchlistManager } from "@/components/watchlist-manager";
import { ReviewStatusEditor } from "@/components/review-status-editor";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  useActiveTenders,
  useReviewStatuses,
  useTeamWatchlist,
} from "@/hooks";
import { RELEVANT_TENDER_TYPES, TEAM_EMAIL } from "@/lib/constants";
import type { Tender, WatchlistItemWithTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Cookie helper (matches the dashboard page pattern)
// ---------------------------------------------------------------------------

function getUserEmailFromCookie(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)user_email=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

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
  const [userEmail, setUserEmail] = useState("");
  const [watchlistOpen, setWatchlistOpen] = useState(true);
  const [favoritesOpen, setFavoritesOpen] = useState(true);

  useEffect(() => {
    setUserEmail(getUserEmailFromCookie());
  }, []);

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
          className="flex w-full items-center justify-between p-4 transition-colors hover:bg-slate-50/50 md:p-6"
        >
          <h3 className="text-lg font-semibold text-megido-text-heading">
            {"\u05E8\u05E9\u05D9\u05DE\u05EA \u05DE\u05E2\u05E7\u05D1"}
          </h3>
          {watchlistOpen ? (
            <ChevronUp className="h-5 w-5 text-slate-500" />
          ) : (
            <ChevronDown className="h-5 w-5 text-slate-500" />
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
        <button
          type="button"
          onClick={() => setFavoritesOpen((prev) => !prev)}
          className="flex w-full items-center justify-between p-4 transition-colors hover:bg-slate-50/50 md:p-6"
        >
          <h3 className="text-lg font-semibold text-megido-text-heading">
            {"\u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD"}
            <span className="mr-2 text-base font-normal text-megido-text-muted">
              ({teamWatchlistWithTender.length})
            </span>
          </h3>
          {favoritesOpen ? (
            <ChevronUp className="h-5 w-5 text-slate-500" />
          ) : (
            <ChevronDown className="h-5 w-5 text-slate-500" />
          )}
        </button>

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
                    className="h-10 animate-pulse rounded-md bg-slate-100"
                  />
                ))}
              </div>
            ) : teamWatchlistWithTender.length === 0 ? (
              <p className="py-4 text-sm text-megido-text-muted">
                {"אין מכרזים מועדפים"}
              </p>
            ) : (
              <>
                {/* Team watchlist table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" dir="rtl">
                    <thead>
                      <tr className="border-b border-megido-border text-right text-xs font-medium text-megido-text-muted">
                        <th className="px-2 py-2">
                          {"\u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4"}
                        </th>
                        <th className="px-2 py-2">
                          {"\u05D4\u05E2\u05E8\u05D5\u05EA"}
                        </th>
                        <th className="px-2 py-2">
                          {"\u05DE\u05D5\u05E2\u05D3 \u05D0\u05D7\u05E8\u05D5\u05DF"}
                        </th>
                        <th className="px-2 py-2">
                          {"\u05E1\u05D5\u05D2"}
                        </th>
                        <th className="px-2 py-2">
                          {'\u05D9\u05D7"\u05D3'}
                        </th>
                        <th className="px-2 py-2">
                          {"\u05E2\u05D9\u05E8"}
                        </th>
                        <th className="px-2 py-2">
                          {"\u05E9\u05DD \u05DE\u05DB\u05E8\u05D6"}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {teamWatchlistWithTender.map((item) => {
                        const tender = item.tender;
                        const review = reviewMap?.[item.tender_id];
                        const statusText =
                          review?.status ??
                          "\u05DC\u05D0 \u05E0\u05E1\u05E7\u05E8";

                        return (
                          <tr
                            key={item.tender_id}
                            className="border-b border-megido-border/50 transition-colors hover:bg-slate-50/50"
                          >
                            {/* Review status */}
                            <td className="px-2 py-2">
                              <Badge
                                variant={getReviewBadgeVariant(statusText)}
                                className="text-[11px]"
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
    </div>
  );
}
