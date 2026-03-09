/**
 * Dashboard page (דאשבורד חדר עסקאות).
 *
 * Full operational view for daily users. Composes all dashboard sections:
 *   - Row 0: Compact header with title + date
 *   - Row 1: New documents tables (docs + brochures)
 *   - Row 2: Closing soon tenders (14-day window)
 *   - Row 3: Team review status table
 *   - Row 4: City bar chart (top 10 cities)
 *   - Row 5: KPI + category cards (compact summary row)
 *   - Row 6: Detailed analytics (collapsible 2x2 chart grid)
 *
 * Watchlist management + review editing now lives on the /watchlist page.
 */
"use client";

import { PageHeader } from "@/components/page-header";
import { ErrorBoundary } from "@/components/error-boundary";
import { Separator } from "@/components/ui/separator";
import { NewDocumentsSection } from "@/components/dashboard/new-documents-section";
import { ClosingSoonDashboard } from "@/components/dashboard/closing-soon-dashboard";
import { ReviewStatusTable } from "@/components/dashboard/review-status-table";
import { CityBarChart } from "@/components/dashboard/city-bar-chart";
import { KpiCategoryRow } from "@/components/dashboard/kpi-category-row";
import { DetailedAnalytics } from "@/components/dashboard/detailed-analytics";
// ---------------------------------------------------------------------------
// (Watchlist management + review editing moved to /watchlist page)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Row 0: Compact header */}
      <PageHeader title={"\u05D3\u05D0\u05E9\u05D1\u05D5\u05E8\u05D3 \u05D7\u05D3\u05E8 \u05E2\u05E1\u05E7\u05D0\u05D5\u05EA"} />

      {/* Row 1: New document tables */}
      <ErrorBoundary sectionLevel>
        <NewDocumentsSection />
      </ErrorBoundary>

      <Separator />

      {/* Row 2: Closing soon tenders (14 days) */}
      <ErrorBoundary sectionLevel>
        <ClosingSoonDashboard />
      </ErrorBoundary>

      <Separator />

      {/* Row 3: Team review status table */}
      <ErrorBoundary sectionLevel>
        <ReviewStatusTable />
      </ErrorBoundary>

      <Separator />

      {/* Row 4: City bar chart */}
      <ErrorBoundary sectionLevel>
        <CityBarChart />
      </ErrorBoundary>

      <Separator />

      {/* Row 5: KPI + category cards summary */}
      <ErrorBoundary sectionLevel>
        <KpiCategoryRow />
      </ErrorBoundary>

      <Separator />

      {/* Row 6: Detailed analytics (collapsible) */}
      <ErrorBoundary sectionLevel>
        <DetailedAnalytics />
      </ErrorBoundary>

    </div>
  );
}
