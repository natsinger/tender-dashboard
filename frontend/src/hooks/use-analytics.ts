/**
 * React Query hooks for analytics computations.
 *
 * Combines data from useTenders / useTenderPrices / useTabaAnalytics
 * with the analytics engine functions to provide computed analytics
 * data ready for charting. Supports date range and region filters.
 */
"use client";

import { useMemo } from "react";

import { useTenders } from "@/hooks/use-tenders";
import { useTenderPrices, useTabaAnalytics } from "@/hooks/use-prices";
import { RELEVANT_TENDER_TYPES } from "@/lib/constants";
import { scoreAllTenders } from "@/lib/utils/tenders";
import {
  supplyPipeline,
  regionalTenderVolume,
  regionalMomentum,
  monthlyPublicationDistribution,
  volumeMovingAverages,
  tenderLifecycleAnalysis,
  deadlineOverlapAnalysis,
  regionSaturationIndex,
  documentIntelligence,
  priceTrendsByRegion,
  tabaAnalysisSummary,
  pricePremiumAnalysis,
  getTopTenders,
  getScoreDistribution,
  buildMultiLotComparison,
} from "@/lib/utils/analytics-engine";
import type { Tender, ScoredTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Filter types
// ---------------------------------------------------------------------------

export interface AnalyticsFilters {
  /** ISO date string for range start. */
  startDate: string | null;
  /** ISO date string for range end. */
  endDate: string | null;
  /** Selected region names. Empty = all regions. */
  regions: string[];
}

// ---------------------------------------------------------------------------
// useAnalytics hook
// ---------------------------------------------------------------------------

/**
 * Master analytics hook.
 *
 * Fetches all tender data, applies date range + region filters, then
 * computes all analytics sections. Memoized for performance.
 */
export function useAnalytics(filters: AnalyticsFilters) {
  const { data: allTenders, isLoading: tendersLoading } = useTenders();
  const { data: allPrices, isLoading: pricesLoading } = useTenderPrices();
  const { data: allTaba, isLoading: tabaLoading } = useTabaAnalytics();

  const isLoading = tendersLoading || pricesLoading || tabaLoading;

  // Step 1: Filter to relevant tender types
  const relevantTenders: Tender[] = useMemo(() => {
    if (!allTenders) return [];
    return allTenders.filter((t) =>
      RELEVANT_TENDER_TYPES.has(t.tender_type_code ?? -1),
    );
  }, [allTenders]);

  // Step 2: Apply date range and region filters
  const filteredTenders: Tender[] = useMemo(() => {
    let result = relevantTenders;

    if (filters.startDate) {
      const start = new Date(filters.startDate).getTime();
      result = result.filter((t) => {
        if (!t.publish_date) return false;
        return new Date(t.publish_date).getTime() >= start;
      });
    }

    if (filters.endDate) {
      const end = new Date(filters.endDate).getTime();
      result = result.filter((t) => {
        if (!t.publish_date) return false;
        return new Date(t.publish_date).getTime() <= end;
      });
    }

    if (filters.regions.length > 0) {
      const regionSet = new Set(filters.regions);
      result = result.filter((t) => t.region != null && regionSet.has(t.region));
    }

    return result;
  }, [relevantTenders, filters.startDate, filters.endDate, filters.regions]);

  // Step 3: Score all filtered tenders
  const scoredTenders: ScoredTender[] = useMemo(() => {
    // scoreAllTenders expects TenderWithComputed, but we can pass Tender
    // since it adds the computed fields internally
    const withDeadline = filteredTenders.map((t) => {
      const deadline = t.deadline ? new Date(t.deadline) : null;
      const now = new Date();
      return {
        ...t,
        days_to_deadline: deadline
          ? Math.floor((deadline.getTime() - now.getTime()) / 86_400_000)
          : null,
      };
    });
    return scoreAllTenders(withDeadline);
  }, [filteredTenders]);

  // Step 4: Compute all analytics sections (each memoized)

  const pipelineData = useMemo(
    () => supplyPipeline(filteredTenders),
    [filteredTenders],
  );

  const regionalVolumeData = useMemo(
    () => regionalTenderVolume(filteredTenders),
    [filteredTenders],
  );

  const momentumData = useMemo(
    () => regionalMomentum(filteredTenders),
    [filteredTenders],
  );

  const monthlyData = useMemo(
    () => monthlyPublicationDistribution(filteredTenders),
    [filteredTenders],
  );

  const movingAvgData = useMemo(
    () => volumeMovingAverages(filteredTenders),
    [filteredTenders],
  );

  const lifecycleData = useMemo(
    () => tenderLifecycleAnalysis(filteredTenders),
    [filteredTenders],
  );

  const overlapData = useMemo(
    () => deadlineOverlapAnalysis(filteredTenders),
    [filteredTenders],
  );

  const saturationData = useMemo(
    () => regionSaturationIndex(filteredTenders),
    [filteredTenders],
  );

  const docIntelData = useMemo(
    () => documentIntelligence(filteredTenders),
    [filteredTenders],
  );

  const priceTrends = useMemo(
    () => priceTrendsByRegion(allPrices ?? [], filteredTenders),
    [allPrices, filteredTenders],
  );

  const tabaSummary = useMemo(
    () => tabaAnalysisSummary(allTaba ?? []),
    [allTaba],
  );

  const premiumData = useMemo(
    () => pricePremiumAnalysis(allPrices ?? [], filteredTenders),
    [allPrices, filteredTenders],
  );

  const topTenders = useMemo(
    () => getTopTenders(scoredTenders, 20),
    [scoredTenders],
  );

  const scoreDist = useMemo(
    () => getScoreDistribution(scoredTenders),
    [scoredTenders],
  );

  const multiLotData = useMemo(
    () => buildMultiLotComparison(allPrices ?? [], filteredTenders),
    [allPrices, filteredTenders],
  );

  // Step 5: Compute KPI values
  const kpis = useMemo(() => {
    const totalTenders = filteredTenders.length;
    const avgScore =
      scoredTenders.length > 0
        ? Math.round(
            (scoredTenders.reduce((s, t) => s + t.total_score, 0) /
              scoredTenders.length) *
              10,
          ) / 10
        : 0;
    const activeRegions = new Set(
      filteredTenders.map((t) => t.region).filter(Boolean),
    ).size;
    const totalUnits = filteredTenders.reduce(
      (s, t) => s + (t.units ?? 0),
      0,
    );
    return { totalTenders, avgScore, activeRegions, totalUnits };
  }, [filteredTenders, scoredTenders]);

  // Step 6: Available regions for filter options
  const availableRegions = useMemo(() => {
    const regions = new Set<string>();
    for (const t of relevantTenders) {
      if (t.region) regions.add(t.region);
    }
    return [...regions].sort();
  }, [relevantTenders]);

  // Step 7: Date range bounds
  const dateRange = useMemo(() => {
    let min: string | null = null;
    let max: string | null = null;
    for (const t of relevantTenders) {
      if (t.publish_date) {
        if (!min || t.publish_date < min) min = t.publish_date;
        if (!max || t.publish_date > max) max = t.publish_date;
      }
    }
    return { min, max };
  }, [relevantTenders]);

  return {
    isLoading,
    filteredTenders,
    scoredTenders,
    kpis,
    pipelineData,
    regionalVolumeData,
    momentumData,
    monthlyData,
    movingAvgData,
    lifecycleData,
    overlapData,
    saturationData,
    docIntelData,
    priceTrends,
    tabaSummary,
    premiumData,
    topTenders,
    scoreDist,
    multiLotData,
    availableRegions,
    dateRange,
    totalRelevant: relevantTenders.length,
  };
}
