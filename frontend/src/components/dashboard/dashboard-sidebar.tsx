/**
 * DashboardSidebar component.
 *
 * Interactive sidebar content for the dashboard page, rendered inside
 * the existing layout sidebar. Contains:
 *   - WatchlistManager (personal mode) with header "ניהול מועדפים"
 *   - WatchlistManager (team mode) with header "מועדפים - חדר עסקאות"
 *   - ReviewStatusEditor with header "עדכון סטטוס סקירה"
 *   - Footer: last update timestamp and record counts
 *
 * Mirrors the sidebar from the Streamlit pages/dashboard.py.
 */
"use client";

import { useMemo } from "react";

import { WatchlistManager } from "@/components/watchlist-manager";
import { ReviewStatusEditor } from "@/components/review-status-editor";
import { Separator } from "@/components/ui/separator";
import {
  useActiveTenders,
  useWatchlist,
  useTeamWatchlist,
  useReviewStatuses,
} from "@/hooks";
import { RELEVANT_TENDER_TYPES, TEAM_EMAIL } from "@/lib/constants";
import type { Tender, WatchlistItemWithTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DashboardSidebarProps {
  /** Currently authenticated user email. */
  email: string | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DashboardSidebar({ email }: DashboardSidebarProps) {
  const { data: activeTenders, isLoading: tendersLoading } = useActiveTenders();

  // Filter to relevant tender types for the select dropdowns
  const relevantTenders = useMemo<Tender[]>(
    () =>
      (activeTenders ?? []).filter((t) =>
        RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? 0),
      ),
    [activeTenders],
  );

  // Personal watchlist
  const { data: personalWatchlist, isLoading: personalLoading } =
    useWatchlist(email);

  // Team watchlist
  const { data: teamWatchlist, isLoading: teamLoading } = useTeamWatchlist();

  // Team tender IDs for review status editor
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

  // Tenders in team watchlist (for review editor tender select)
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

  // Record counts for footer
  const totalRecords = activeTenders?.length ?? 0;
  const relevantCount = relevantTenders.length;
  const now = new Date();
  const dateStr = now.toLocaleDateString("he-IL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  if (!email) {
    return (
      <div dir="rtl" className="space-y-4 px-3 py-2">
        <p className="text-xs text-slate-400">
          {"\u05D9\u05E9 \u05DC\u05D4\u05D6\u05D3\u05D4\u05D5\u05EA \u05DB\u05D3\u05D9 \u05DC\u05E0\u05D4\u05DC \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD"}
        </p>
      </div>
    );
  }

  return (
    <div dir="rtl" className="space-y-1 px-3 py-2">
      {/* Section 1: Personal Watchlist */}
      <Separator className="bg-sidebar-border" />
      <h4 className="pt-2 text-sm font-semibold text-slate-200">
        {"\u05E0\u05D9\u05D4\u05D5\u05DC \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD"}
      </h4>
      <p className="mb-1 text-[11px] text-slate-400">
        {"\u05DE\u05E9\u05EA\u05DE\u05E9: "}{email}
      </p>
      <WatchlistManager
        email={email}
        tenders={relevantTenders}
        watchlistItems={personalWatchlist ?? []}
        isLoading={tendersLoading || personalLoading}
      />

      {/* Section 2: Team Watchlist */}
      <Separator className="!my-3 bg-sidebar-border" />
      <h4 className="text-sm font-semibold text-slate-200">
        {"\u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD - \u05D7\u05D3\u05E8 \u05E2\u05E1\u05E7\u05D0\u05D5\u05EA"}
      </h4>
      <WatchlistManager
        email={TEAM_EMAIL}
        isTeam
        tenders={relevantTenders}
        watchlistItems={teamWatchlist ?? []}
        isLoading={tendersLoading || teamLoading}
      />

      {/* Section 3: Review Status Editor */}
      <Separator className="!my-3 bg-sidebar-border" />
      <h4 className="text-sm font-semibold text-slate-200">
        {"\u05E2\u05D3\u05DB\u05D5\u05DF \u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4"}
      </h4>
      <ReviewStatusEditor
        email={email}
        tenders={teamTenders}
        reviewMap={reviewMap ?? {}}
      />

      {/* Footer */}
      <Separator className="!my-3 bg-sidebar-border" />
      <p className="text-[11px] text-slate-400">
        {"\u05E2\u05D3\u05DB\u05D5\u05DF: "}{dateStr}
      </p>
      <p className="text-[11px] text-slate-400">
        {"\u05E8\u05E9\u05D5\u05DE\u05D5\u05EA: "}{relevantCount.toLocaleString("he-IL")}
        {" (\u05DE-"}{totalRecords.toLocaleString("he-IL")}{")"}
      </p>
    </div>
  );
}
