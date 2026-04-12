/**
 * React Query hooks for tender outcome tracking (post-deadline).
 *
 * Manages the tender_outcomes table — manual fields for tracking
 * whether we bid, our offer, position, and notes.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { supabase } from "@/lib/supabase/client";
import type { TenderOutcome } from "@/types/database";

// ---------------------------------------------------------------------------
// useTenderOutcomes — bulk fetch for multiple tender IDs
// ---------------------------------------------------------------------------

/**
 * Fetch tender outcomes for a list of tender IDs.
 *
 * Returns a map of tender_id -> TenderOutcome for easy lookup.
 */
export function useTenderOutcomes(tenderIds: number[]) {
  return useQuery<Record<number, TenderOutcome>>({
    queryKey: ["tender-outcomes", tenderIds],
    queryFn: async () => {
      if (tenderIds.length === 0) return {};

      const result: Record<number, TenderOutcome> = {};

      // Batch in chunks of 500 (Supabase .in() limit)
      const BATCH = 500;
      for (let i = 0; i < tenderIds.length; i += BATCH) {
        const batch = tenderIds.slice(i, i + BATCH);
        const { data, error } = await supabase
          .from("tender_outcomes")
          .select("*")
          .in("tender_id", batch);

        if (error) {
          if (process.env.NODE_ENV === "development") {
            console.warn("Failed to fetch tender outcomes:", error.message);
          }
          continue;
        }

        for (const row of (data ?? []) as TenderOutcome[]) {
          result[row.tender_id] = row;
        }
      }

      return result;
    },
    enabled: tenderIds.length > 0,
    staleTime: 2 * 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useSetTenderOutcome — mutation
// ---------------------------------------------------------------------------

/**
 * Upsert a tender outcome row. Accepts partial fields — only the
 * provided fields are updated, the rest keep their current values.
 */
export function useSetTenderOutcome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      tenderId,
      didBid,
      ourOffer,
      ourPosition,
      outcomeNotes,
      forcedExpired,
      updatedBy,
    }: {
      tenderId: number;
      didBid?: boolean;
      ourOffer?: number | null;
      ourPosition?: number | null;
      outcomeNotes?: string | null;
      forcedExpired?: boolean;
      updatedBy: string;
    }) => {
      const now = new Date().toISOString().slice(0, 19);

      const row: Record<string, unknown> = {
        tender_id: tenderId,
        updated_by: updatedBy,
        updated_at: now,
      };
      if (didBid !== undefined) row.did_bid = didBid;
      if (ourOffer !== undefined) row.our_offer = ourOffer;
      if (ourPosition !== undefined) row.our_position = ourPosition;
      if (outcomeNotes !== undefined) row.outcome_notes = outcomeNotes;
      if (forcedExpired !== undefined) row.forced_expired = forcedExpired;

      const { error } = await supabase
        .from("tender_outcomes")
        .upsert(row, { onConflict: "tender_id" });

      if (error) throw new Error(`Set tender outcome failed: ${error.message}`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tender-outcomes"] });
    },
  });
}
