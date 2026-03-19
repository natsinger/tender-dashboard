/**
 * Analytics page -- market intelligence and competitive analysis (ניתוח שוק).
 *
 * Comprehensive market analytics dashboard with trends, competitive analysis,
 * price analytics, and a composite scoring system. All analytics are computed
 * via analytics-engine.ts functions, and data is loaded via React Query hooks.
 *
 * Sections:
 *   1. Header + Sidebar Filters (date range, region)
 *   2. Market Overview (KPIs + supply pipeline)
 *   3. Trends (regional volume, momentum, monthly distribution, moving averages)
 *   4. Competitive Intelligence (lifecycle, deadline overlap, saturation, docs)
 *   5. Price Analytics (price trends, taba summary, price premium)
 *   6. Scoring (top tenders, distribution, radar deep-dive)
 *
 * Branded for MEGIDO BY AURA.
 */
"use client";

import { useState, useCallback } from "react";

import { PageHeader } from "@/components/page-header";
import { Separator } from "@/components/ui/separator";
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
  // Filter state (local, not in Zustand since this is page-specific)
  const [startDate, setStartDate] = useState<string | null>(null);
  const [endDate, setEndDate] = useState<string | null>(null);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);

  const filters: AnalyticsFilters = {
    startDate,
    endDate,
    regions: selectedRegions,
  };

  const analytics = useAnalytics(filters);

  // Loading state
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
        {/* Sidebar (right in RTL, rendered first for mobile-first) */}
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

        {/* Main content area */}
        <div className="min-w-0 flex-1 space-y-6">
          {/* Section 1: Market Overview */}
          <MarketOverviewSection
            totalTenders={analytics.kpis.totalTenders}
            avgScore={analytics.kpis.avgScore}
            activeRegions={analytics.kpis.activeRegions}
            totalUnits={analytics.kpis.totalUnits}
            pipelineData={analytics.pipelineData}
          />

          <Separator />

          {/* Section 2: Trends */}
          <TrendsSection
            regionalVolumeData={analytics.regionalVolumeData}
            momentumData={analytics.momentumData}
            monthlyData={analytics.monthlyData}
            movingAvgData={analytics.movingAvgData}
          />

          <Separator />

          {/* Section 3: Competitive Intelligence */}
          <CompetitiveSection
            lifecycleData={analytics.lifecycleData}
            overlapData={analytics.overlapData}
            saturationData={analytics.saturationData}
            docIntelData={analytics.docIntelData}
          />

          <Separator />

          {/* Section 4: Price Analytics */}
          <PriceSection
            priceTrends={analytics.priceTrends}
            tabaSummary={analytics.tabaSummary}
            premiumData={analytics.premiumData}
          />

          <Separator />

          {/* Section 5: Multi-lot comparison */}
          <LotComparisonSection multiLotData={analytics.multiLotData} />

          <Separator />

          {/* Section 6: Scoring */}
          <ScoringSection
            topTenders={analytics.topTenders}
            scoreDist={analytics.scoreDist}
            scoredTenders={analytics.scoredTenders}
          />
        </div>
      </div>
    </div>
  );
}
