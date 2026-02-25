/**
 * React Query hooks for tender price and taba analytics data.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { paginatedFetch } from "@/hooks/use-tenders";
import type { TabaAnalytics, TenderPrice } from "@/types/database";

// ---------------------------------------------------------------------------
// useTenderPrices — price data, optionally filtered by tender
// ---------------------------------------------------------------------------

/**
 * Fetch tender price rows. If `tenderId` is provided, filters to that
 * tender only; otherwise returns all prices (paginated).
 */
export function useTenderPrices(tenderId?: number | null) {
  return useQuery<TenderPrice[]>({
    queryKey: ["tender-prices", tenderId ?? "all"],
    queryFn: async () => {
      const filters: Array<{
        column: string;
        op: "eq" | "gt" | "in";
        value: unknown;
      }> = [];

      if (tenderId != null) {
        filters.push({ column: "tender_id", op: "eq", value: tenderId });
      }

      return paginatedFetch<TenderPrice>("tender_prices", {
        filters: filters.length > 0 ? filters : undefined,
        orderBy: "tender_id",
        ascending: true,
      });
    },
    staleTime: 5 * 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useTabaAnalytics — taba (plan-level) analytics data
// ---------------------------------------------------------------------------

/**
 * Fetch taba analytics rows. If `planNumber` is provided, filters to that
 * plan only; otherwise returns all rows (paginated).
 */
export function useTabaAnalytics(planNumber?: string | null) {
  return useQuery<TabaAnalytics[]>({
    queryKey: ["taba-analytics", planNumber ?? "all"],
    queryFn: async () => {
      const filters: Array<{
        column: string;
        op: "eq" | "gt" | "in";
        value: unknown;
      }> = [];

      if (planNumber != null) {
        filters.push({ column: "plan_number", op: "eq", value: planNumber });
      }

      return paginatedFetch<TabaAnalytics>("taba_analytics", {
        filters: filters.length > 0 ? filters : undefined,
        orderBy: "plan_number",
        ascending: true,
      });
    },
    staleTime: 5 * 60 * 1000,
  });
}
