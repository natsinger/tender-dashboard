/**
 * Analytics page -- market intelligence and competitive analysis (ניתוח שוק).
 *
 * Top-level tab navigation replaces the long vertical scroll. Each tab
 * renders one analysis section while the sidebar filters stay persistent.
 *
 * Tabs:
 *   1. סקירה  — Market Overview (KPIs + supply pipeline)
 *   2. מגמות  — Trends (regional volume, momentum, monthly, moving avg)
 *   3. תחרות  — Competitive Intelligence (lifecycle, overlap, saturation, docs)
 *   4. מחירים — Price Analytics (price trends, taba, premium)
 *   5. מתחמים — Multi-lot comparison
 *   6. ניקוד  — Scoring (top tenders, distribution, radar)
 */
"use client";

import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useAnalytics } from "@/hooks/use-analytics";
import type { AnalyticsFilters } from "@/hooks/use-analytics";

import { MarketOverviewSection } from "@/components/analytics/market-overview-section";
import { TrendsSection } from "@/components/analytics/trends-section";
import { CompetitiveSection } from "@/components/analytics/competitive-section";
import { PriceSection } from "@/components/analytics/price-section";
import { ScoringSection } from "@/components/analytics/scoring-section";
import { LotComparisonSection } from "@/components/analytics/lot-comparison-section";
import { AnalyticsSidebar } from "@/components/analytics/analytics-sidebar";

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function AnalyticsPage() {
  const [startDate, setStartDate] = useState<string | null>(null);
  const [endDate, setEndDate] = useState<string | null>(null);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);

  const filters: AnalyticsFilters = {
    startDate,
    endDate,
    regions: selectedRegions,
  };

  const analytics = useAnalytics(filters);

  if (analytics.isLoading) {
    return (
      <div dir="rtl" className="space-y-6">
        <PageHeader
          title="MEGIDO | ניתוח שוק"
          subtitle="מגמות, ניקוד ומודיעין תחרותי"
        />
        <div className="flex items-center justify-center py-20">
          <div className="space-y-3 text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            <p className="text-sm text-megido-text-muted">טוען נתוני ניתוח...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div dir="rtl" className="space-y-6">
      <PageHeader
        title="MEGIDO | ניתוח שוק"
        subtitle="מגמות, ניקוד ומודיעין תחרותי"
      />

      {/* Main content + sidebar grid */}
      <div className="flex flex-col gap-6 lg:flex-row-reverse">
        {/* Sidebar */}
        <div className="w-full shrink-0 lg:w-64">
          <AnalyticsSidebar
            minDate={analytics.dateRange.min}
            maxDate={analytics.dateRange.max}
            startDate={startDate}
            endDate={endDate}
            regions={analytics.availableRegions}
            selectedRegions={selectedRegions}
            filteredCount={analytics.filteredTenders.length}
            totalCount={analytics.totalRelevant}
            onStartDateChange={setStartDate}
            onEndDateChange={setEndDate}
            onRegionsChange={setSelectedRegions}
            className="sticky top-4"
          />
        </div>

        {/* Main content — single tab visible at a time */}
        <div className="min-w-0 flex-1">
          <Tabs defaultValue="overview" dir="rtl">
            <TabsList variant="line" className="mb-6 w-full justify-start border-b border-megido-border pb-0">
              <TabsTrigger value="overview">{"\u05E1\u05E7\u05D9\u05E8\u05D4"}</TabsTrigger>
              <TabsTrigger value="trends">{"\u05DE\u05D2\u05DE\u05D5\u05EA"}</TabsTrigger>
              <TabsTrigger value="competitive">{"\u05EA\u05D7\u05E8\u05D5\u05EA"}</TabsTrigger>
              <TabsTrigger value="pricing">{"\u05DE\u05D7\u05D9\u05E8\u05D9\u05DD"}</TabsTrigger>
              <TabsTrigger value="lots">{"\u05DE\u05EA\u05D7\u05DE\u05D9\u05DD"}</TabsTrigger>
              <TabsTrigger value="scoring">{"\u05E0\u05D9\u05E7\u05D5\u05D3"}</TabsTrigger>
            </TabsList>

            <TabsContent value="overview">
              <MarketOverviewSection
                totalTenders={analytics.kpis.totalTenders}
                avgScore={analytics.kpis.avgScore}
                activeRegions={analytics.kpis.activeRegions}
                totalUnits={analytics.kpis.totalUnits}
                pipelineData={analytics.pipelineData}
              />
            </TabsContent>

            <TabsContent value="trends">
              <TrendsSection
                regionalVolumeData={analytics.regionalVolumeData}
                momentumData={analytics.momentumData}
                monthlyData={analytics.monthlyData}
                movingAvgData={analytics.movingAvgData}
              />
            </TabsContent>

            <TabsContent value="competitive">
              <CompetitiveSection
                lifecycleData={analytics.lifecycleData}
                overlapData={analytics.overlapData}
                saturationData={analytics.saturationData}
                docIntelData={analytics.docIntelData}
              />
            </TabsContent>

            <TabsContent value="pricing">
              <PriceSection
                priceTrends={analytics.priceTrends}
                tabaSummary={analytics.tabaSummary}
                premiumData={analytics.premiumData}
              />
            </TabsContent>

            <TabsContent value="lots">
              <LotComparisonSection multiLotData={analytics.multiLotData} />
            </TabsContent>

            <TabsContent value="scoring">
              <ScoringSection
                topTenders={analytics.topTenders}
                scoreDist={analytics.scoreDist}
                scoredTenders={analytics.scoredTenders}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
