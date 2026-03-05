/**
 * React Query hook for batch lot aggregation.
 *
 * Fetches all lots for a list of tender IDs and returns aggregated
 * free_market, target_price, and total units per tender. Used by the
 * Management page to display lot-level KPI columns in watchlist tables.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/lib/supabase/client";
import { SUPABASE_PAGE_SIZE } from "@/lib/constants";
import type { TenderLot } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LotAggregation {
  free_market: number;
  target_price: number;
  total: number;
  /** Percentage of target price units out of total (e.g. "42%") or "---". */
  pct: string;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Fetch and aggregate lot data for multiple tender IDs.
 *
 * Returns a Record mapping each tender_id to its aggregated lot totals.
 */
export function useBulkLots(tenderIds: number[]) {
  return useQuery<Record<number, LotAggregation>>({
    queryKey: ["bulk-lots", tenderIds],
    queryFn: async () => {
      if (tenderIds.length === 0) return {};

      const allLots: TenderLot[] = [];
      const BATCH = 500;

      for (let i = 0; i < tenderIds.length; i += BATCH) {
        const batch = tenderIds.slice(i, i + BATCH);
        let offset = 0;

        while (true) {
          const { data, error } = await supabase
            .from("tender_lots")
            .select("tender_id, total_units, units_free_market, units_target_price")
            .in("tender_id", batch)
            .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

          if (error) {
            if (process.env.NODE_ENV === "development") {
              console.warn("Failed to fetch bulk lots:", error.message);
            }
            break;
          }

          const rows = (data ?? []) as TenderLot[];
          allLots.push(...rows);

          if (rows.length < SUPABASE_PAGE_SIZE) break;
          offset += SUPABASE_PAGE_SIZE;
        }
      }

      // Aggregate by tender_id
      const result: Record<number, LotAggregation> = {};

      for (const tid of tenderIds) {
        result[tid] = { free_market: 0, target_price: 0, total: 0, pct: "\u2014" };
      }

      for (const lot of allLots) {
        const agg = result[lot.tender_id];
        if (!agg) continue;
        agg.free_market += Number(lot.units_free_market) || 0;
        agg.target_price += Number(lot.units_target_price) || 0;
        agg.total += Number(lot.total_units) || 0;
      }

      // Compute percentage
      for (const agg of Object.values(result)) {
        agg.pct =
          agg.total > 0
            ? `${Math.round((agg.target_price / agg.total) * 100)}%`
            : "\u2014";
      }

      return result;
    },
    enabled: tenderIds.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}
