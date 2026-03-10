/**
 * Hook for resolving GovMap TABA URLs.
 *
 * Returns the pre-computed govmap_url from the tender data if available,
 * otherwise falls back to an on-demand API call to /api/govmap.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import type { Tender } from "@/types/database";

// ---------------------------------------------------------------------------
// useGovmapUrl
// ---------------------------------------------------------------------------

/**
 * Resolve a GovMap TABA URL for a tender.
 *
 * Priority:
 * 1. Pre-computed `govmap_url` stored on the tender row.
 * 2. On-demand fetch via `/api/govmap?planNumber=...` when plan_number exists.
 * 3. `null` when neither field is available.
 */
export function useGovmapUrl(tender: Tender | null): {
  url: string | null;
  isLoading: boolean;
} {
  const precomputed = tender?.govmap_url ?? null;
  const planNumber = tender?.plan_number ?? null;
  const needsFetch = !!planNumber && !precomputed;

  const { data, isLoading } = useQuery<{ url: string | null }>({
    queryKey: ["govmap", planNumber],
    queryFn: async () => {
      const res = await fetch(
        `/api/govmap?planNumber=${encodeURIComponent(planNumber!)}`,
      );
      if (!res.ok) return { url: null };
      return res.json() as Promise<{ url: string | null }>;
    },
    enabled: needsFetch,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });

  if (precomputed) {
    return { url: precomputed, isLoading: false };
  }

  if (!planNumber) {
    return { url: null, isLoading: false };
  }

  return { url: data?.url ?? null, isLoading };
}
