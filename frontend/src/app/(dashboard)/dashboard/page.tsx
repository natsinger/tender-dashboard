/**
 * Dashboard page (דאשבורד חדר עסקאות).
 *
 * Full operational view for daily users. Composes all dashboard sections:
 *   - Row 0: Compact header with title + date
 *   - Row 1: New documents tables + KPI metric cards
 *   - Row 2: City bar chart (top 10 cities)
 *   - Row 3: Team review status table
 *   - Row 4: Category cards (rental, assisted living, initiative)
 *   - Row 5: Detailed analytics (collapsible 2x2 chart grid)
 *
 * Sidebar content (watchlist management + review status editing)
 * is rendered via DashboardSidebar and integrated into the layout.
 */
"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Separator } from "@/components/ui/separator";
import { NewDocumentsSection } from "@/components/dashboard/new-documents-section";
import { CityBarChart } from "@/components/dashboard/city-bar-chart";
import { ReviewStatusTable } from "@/components/dashboard/review-status-table";
import { CategoryCardsRow } from "@/components/dashboard/category-cards-row";
import { DetailedAnalytics } from "@/components/dashboard/detailed-analytics";
import { DashboardSidebar } from "@/components/dashboard/dashboard-sidebar";

// ---------------------------------------------------------------------------
// Cookie helper (matches the layout pattern)
// ---------------------------------------------------------------------------

function getUserEmailFromCookie(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)user_email=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [userEmail, setUserEmail] = useState("");

  useEffect(() => {
    setUserEmail(getUserEmailFromCookie());
  }, []);

  return (
    <div className="space-y-6">
      {/* Row 0: Compact header */}
      <PageHeader
        title={'\u05DE\u05DB\u05E8\u05D6\u05D9 \u05DE\u05E7\u05E8\u05E7\u05E2\u05D9\u05DF \u05E4\u05E2\u05D9\u05DC\u05D9\u05DD \u05E8\u05DE"\u05D9 (\u05E4\u05D5\u05DE\u05D1\u05D9, \u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4, \u05D3\u05D9\u05D5\u05E8 \u05D1\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D5\u05E4\u05D7\u05EA)'}
      />

      {/* Row 1: New document tables + KPI cards */}
      <NewDocumentsSection />

      <Separator />

      {/* Row 2: City bar chart */}
      <CityBarChart />

      <Separator />

      {/* Row 3: Team review status table */}
      <ReviewStatusTable />

      <Separator />

      {/* Row 4: Category cards */}
      <CategoryCardsRow />

      <Separator />

      {/* Row 5: Detailed analytics (collapsible) */}
      <DetailedAnalytics />

      {/* Sidebar content — rendered outside the main flow,
          picked up by the layout's sidebar slot if available.
          For now we render it inline in a visually hidden container
          that can be portaled or lifted to the layout. */}
      <div className="hidden">
        <DashboardSidebar email={userEmail} />
      </div>
    </div>
  );
}
