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

interface GovmapResult {
  /** GovMap or Mavat URL (GovMap preferred, Mavat as fallback). */
  url: string | null;
  /** Whether the on-demand fetch is in progress. */
  isLoading: boolean;
  /** "govmap" if resolved via GovMap, "mavat" if fallback to Mavat search. */
  source: "govmap" | "mavat" | null;
}

/**
 * Build a Mavat search URL from a plan number.
 *
 * Opens the Mavat planning database search page with the plan number
 * pre-filled. Used as fallback when GovMap resolution fails.
 */
function buildMavatSearchUrl(planNumber: string): string {
  return `https://mavat.iplan.gov.il/SV1#/?search=${encodeURIComponent(planNumber)}`;
}

/**
 * Resolve a TABA plan URL for a tender.
 *
 * Priority:
 * 1. Pre-computed `govmap_url` stored on the tender row → GovMap.
 * 2. On-demand fetch via `/api/govmap?planNumber=...` → GovMap.
 * 3. Mavat search URL as fallback when GovMap can't resolve.
 * 4. `null` when no plan_number exists.
 */
export function useGovmapUrl(tender: Tender | null): GovmapResult {
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
    return { url: precomputed, isLoading: false, source: "govmap" };
  }

  if (!planNumber) {
    return { url: null, isLoading: false, source: null };
  }

  // On-demand GovMap fetch succeeded
  if (data?.url) {
    return { url: data.url, isLoading: false, source: "govmap" };
  }

  // GovMap fetch done but no result → fallback to Mavat search
  if (!isLoading && !data?.url) {
    return { url: buildMavatSearchUrl(planNumber), isLoading: false, source: "mavat" };
  }

  return { url: null, isLoading, source: null };
}
