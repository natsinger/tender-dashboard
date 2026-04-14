/**
 * React Query hooks for tender review status management.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { supabase } from "@/lib/supabase/client";
import type { TenderReview } from "@/types/database";

// ---------------------------------------------------------------------------
// useReviewStatuses — bulk fetch for multiple tender IDs
// ---------------------------------------------------------------------------

/**
 * Fetch review statuses for a list of tender IDs.
 *
 * Returns a map of tender_id -> TenderReview for easy lookup.
 */
export function useReviewStatuses(tenderIds: number[]) {
  return useQuery<Record<number, TenderReview>>({
    queryKey: ["review-statuses", tenderIds],
    queryFn: async () => {
      if (tenderIds.length === 0) return {};

      const result: Record<number, TenderReview> = {};

      // Batch in chunks of 500 (Supabase .in() limit)
      const BATCH = 500;
      for (let i = 0; i < tenderIds.length; i += BATCH) {
        const batch = tenderIds.slice(i, i + BATCH);
        const { data, error } = await supabase
          .from("tender_reviews")
          .select("*")
          .in("tender_id", batch);

        if (error) {
          if (process.env.NODE_ENV === "development") {
            console.warn("Failed to fetch review statuses:", error.message);
          }
          continue;
        }

        for (const row of (data ?? []) as TenderReview[]) {
          result[row.tender_id] = row;
        }
      }

      return result;
    },
    enabled: tenderIds.length > 0,
    staleTime: 30 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useSetReviewStatus — mutation
// ---------------------------------------------------------------------------

/**
 * Set or update the review status for a tender.
 *
 * Invalidates the review-statuses cache on success so any list showing
 * review badges re-fetches.
 */
export function useSetReviewStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      tenderId,
      status,
      updatedBy,
      notes,
    }: {
      tenderId: number;
      status: string;
      updatedBy: string;
      notes?: string;
    }) => {
      const now = new Date().toISOString().slice(0, 19);

      const { error } = await supabase.from("tender_reviews").upsert(
        {
          tender_id: tenderId,
          status,
          updated_by: updatedBy,
          updated_at: now,
          notes: notes ?? "",
        },
        { onConflict: "tender_id" },
      );

      if (error) throw new Error(`Set review status failed: ${error.message}`);
    },
    onSuccess: () => {
      // Invalidate all review-status queries since they may contain this tender
      void queryClient.invalidateQueries({ queryKey: ["review-statuses"] });
    },
  });
}
