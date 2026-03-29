/**
 * React Query hooks for tender lot and building rights data.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/lib/supabase/client";
import { paginatedFetch } from "@/hooks/use-tenders";
import type { BuildingRight, TenderLot } from "@/types/database";

// ---------------------------------------------------------------------------
// useTenderLots — lot-level data for a tender
// ---------------------------------------------------------------------------

/**
 * Fetch all lots for a specific tender, ordered by lot_number.
 */
export function useTenderLots(tenderId: number | null | undefined) {
  return useQuery<TenderLot[]>({
    queryKey: ["tender-lots", tenderId],
    queryFn: async () => {
      if (!tenderId) return [];

      return paginatedFetch<TenderLot>("tender_lots", {
        filters: [{ column: "tender_id", op: "eq", value: tenderId }],
        orderBy: "lot_number",
        ascending: true,
      });
    },
    enabled: tenderId != null && tenderId > 0,
    staleTime: 5 * 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useBuildingRights — building rights for a plan number
// ---------------------------------------------------------------------------

/**
 * Fetch building rights rows for a given plan number.
 *
 * Optionally filter by plan_status ("מצב מוצע" or "מצב מאושר").
 */
export function useBuildingRights(
  planNumber: string | null | undefined,
  planStatus?: string | null,
) {
  return useQuery<BuildingRight[]>({
    queryKey: ["building-rights", planNumber, planStatus],
    queryFn: async () => {
      if (!planNumber) return [];

      const filters: Array<{
        column: string;
        op: "eq" | "gt" | "in";
        value: unknown;
      }> = [{ column: "plan_number", op: "eq", value: planNumber }];

      if (planStatus) {
        filters.push({ column: "plan_status", op: "eq", value: planStatus });
      }

      return paginatedFetch<BuildingRight>("building_rights", {
        filters,
        orderBy: "row_index",
        ascending: true,
      });
    },
    enabled: !!planNumber,
    staleTime: 10 * 60 * 1000, // building rights change rarely
  });
}

// ---------------------------------------------------------------------------
// useBuildingRightsForPlans — batch-fetch for multiple plans
// ---------------------------------------------------------------------------

/**
 * Batch-fetch building rights for multiple plan numbers at once.
 *
 * Returns a Map keyed by plan_number for efficient lookup.
 * Used by the analytics engine to enrich multi-lot comparison data.
 */
export function useBuildingRightsForPlans(planNumbers: string[]) {
  const sorted = [...planNumbers].sort();
  return useQuery<Map<string, BuildingRight[]>>({
    queryKey: ["building-rights-batch", sorted],
    queryFn: async () => {
      const result = new Map<string, BuildingRight[]>();
      if (sorted.length === 0) return result;

      const rows = await paginatedFetch<BuildingRight>("building_rights", {
        filters: [{ column: "plan_number", op: "in", value: sorted }],
        orderBy: "row_index",
        ascending: true,
      });

      for (const row of rows) {
        const existing = result.get(row.plan_number);
        if (existing) {
          existing.push(row);
        } else {
          result.set(row.plan_number, [row]);
        }
      }
      return result;
    },
    enabled: sorted.length > 0,
    staleTime: 10 * 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useTenderBuildingRights — convenience: fetch plan_number from tender, then rights
// ---------------------------------------------------------------------------

/**
 * Fetch building rights by first looking up the plan_number from the tender.
 */
export function useTenderBuildingRights(tenderId: number | null | undefined) {
  return useQuery<BuildingRight[]>({
    queryKey: ["tender-building-rights", tenderId],
    queryFn: async () => {
      if (!tenderId) return [];

      // First, get the plan_number from the tender
      const { data, error } = await supabase
        .from("tenders")
        .select("plan_number")
        .eq("tender_id", tenderId)
        .limit(1)
        .single();

      if (error || !data?.plan_number) return [];

      return paginatedFetch<BuildingRight>("building_rights", {
        filters: [
          { column: "plan_number", op: "eq", value: data.plan_number },
        ],
        orderBy: "row_index",
        ascending: true,
      });
    },
    enabled: tenderId != null && tenderId > 0,
    staleTime: 10 * 60 * 1000,
  });
}
