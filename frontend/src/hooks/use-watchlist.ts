/**
 * React Query hooks for user watchlist management.
 *
 * Provides read hooks (useWatchlist, useTeamWatchlist) and mutation hooks
 * (useAddToWatchlist, useRemoveFromWatchlist, useSetWatchlistNote) that
 * automatically invalidate the query cache on success.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { SUPABASE_PAGE_SIZE, TEAM_EMAIL } from "@/lib/constants";
import { supabase } from "@/lib/supabase/client";
import type {
  Tender,
  UserWatchlistItem,
  WatchlistItemWithTender,
} from "@/types/database";

// ---------------------------------------------------------------------------
// useWatchlist — user's watchlist items with tender data
// ---------------------------------------------------------------------------

/**
 * Fetch the current user's watchlist and join with tender details.
 */
export function useWatchlist(email: string | null | undefined) {
  return useQuery<WatchlistItemWithTender[]>({
    queryKey: ["watchlist", email],
    queryFn: async () => {
      if (!email) return [];

      const normalEmail = email.toLowerCase().trim();

      // Step 1: Fetch watchlist rows
      const allItems: UserWatchlistItem[] = [];
      let offset = 0;

      while (true) {
        const { data, error } = await supabase
          .from("user_watchlist")
          .select("id, tender_id, created_at, notes, active, user_email")
          .eq("user_email", normalEmail)
          .eq("active", 1)
          .order("created_at", { ascending: false })
          .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

        if (error) throw new Error(`Fetch watchlist failed: ${error.message}`);

        const rows = (data ?? []) as UserWatchlistItem[];
        allItems.push(...rows);

        if (rows.length < SUPABASE_PAGE_SIZE) break;
        offset += SUPABASE_PAGE_SIZE;
      }

      if (allItems.length === 0) return [];

      // Step 2: Fetch tender data for watched IDs
      const tenderIds = allItems.map((item) => item.tender_id);
      const tenderMap = new Map<number, Tender>();

      const BATCH = 500;
      for (let i = 0; i < tenderIds.length; i += BATCH) {
        const batch = tenderIds.slice(i, i + BATCH);
        const { data: tenderData } = await supabase
          .from("tenders")
          .select("*")
          .in("tender_id", batch);

        for (const t of (tenderData ?? []) as Tender[]) {
          tenderMap.set(t.tender_id, t);
        }
      }

      // Step 3: Merge
      return allItems.map((item) => ({
        ...item,
        tender: tenderMap.get(item.tender_id) ?? null,
      }));
    },
    enabled: !!email,
    staleTime: 30 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useTeamWatchlist — TEAM_EMAIL watchlist
// ---------------------------------------------------------------------------

/**
 * Convenience hook for the shared team watchlist.
 */
export function useTeamWatchlist() {
  return useWatchlist(TEAM_EMAIL);
}

// ---------------------------------------------------------------------------
// useAddToWatchlist — mutation
// ---------------------------------------------------------------------------

/**
 * Add a tender to a user's watchlist.
 *
 * Invalidates the watchlist query cache on success.
 */
export function useAddToWatchlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      email,
      tenderId,
    }: {
      email: string;
      tenderId: number;
    }) => {
      const normalEmail = email.toLowerCase().trim();

      const { error } = await supabase
        .from("user_watchlist")
        .upsert(
          {
            user_email: normalEmail,
            tender_id: tenderId,
            created_at: new Date().toISOString().slice(0, 10),
            active: 1,
          },
          { onConflict: "user_email,tender_id", ignoreDuplicates: true },
        );

      if (error) throw new Error(`Add to watchlist failed: ${error.message}`);
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["watchlist", variables.email.toLowerCase().trim()],
      });
    },
  });
}

// ---------------------------------------------------------------------------
// useRemoveFromWatchlist — mutation
// ---------------------------------------------------------------------------

/**
 * Remove a tender from a user's watchlist.
 */
export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      email,
      tenderId,
    }: {
      email: string;
      tenderId: number;
    }) => {
      const normalEmail = email.toLowerCase().trim();

      const { error } = await supabase
        .from("user_watchlist")
        .delete()
        .eq("user_email", normalEmail)
        .eq("tender_id", tenderId);

      if (error) throw new Error(`Remove from watchlist failed: ${error.message}`);
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["watchlist", variables.email.toLowerCase().trim()],
      });
    },
  });
}

// ---------------------------------------------------------------------------
// useSetWatchlistNote — mutation
// ---------------------------------------------------------------------------

/**
 * Set or update a personal note on a watched tender.
 */
export function useSetWatchlistNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      email,
      tenderId,
      notes,
    }: {
      email: string;
      tenderId: number;
      notes: string;
    }) => {
      const normalEmail = email.toLowerCase().trim();

      const { error } = await supabase
        .from("user_watchlist")
        .update({ notes })
        .eq("user_email", normalEmail)
        .eq("tender_id", tenderId);

      if (error) throw new Error(`Set watchlist note failed: ${error.message}`);
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["watchlist", variables.email.toLowerCase().trim()],
      });
    },
  });
}
