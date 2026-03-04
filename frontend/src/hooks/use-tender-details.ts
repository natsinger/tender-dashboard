/**
 * React Query hook for fetching raw tender details from the RMI API.
 *
 * Returns the full API response including the Tik[] array with per-lot
 * financial/property data (area, reserve price, appraisal, development
 * costs, guarantee, gush/helka, zoning plan).
 *
 * Uses the /api/tender-details proxy route to avoid CORS issues.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

// ---------------------------------------------------------------------------
// Types for the RMI detail API response (relevant subset)
// ---------------------------------------------------------------------------

export interface GushHelkaEntry {
  Gush: string;
  Helka: string;
}

export interface TochnitMigrashEntry {
  Tochnit: string;
  MigrashName: string;
}

export interface TikEntry {
  TikID: string;
  MitchamName: string;
  Shetach: number;
  ShetachBniya: number;
  Kibolet: number;
  HotzaotPituach: number;
  MechirSaf: number;
  mechirShuma: number;
  SchumArvut: number;
  ShemZoche: string | null;
  SchumZchiya: number | null;
  GushHelka: GushHelkaEntry[];
  TochnitMigrash: TochnitMigrashEntry[];
}

export interface RmiTenderDetails {
  MichrazID: number;
  MichrazName: string;
  YechidotDiur: number;
  Tik: TikEntry[];
  MechirSafMichraz: number | null;
  SchumArvut: number | null;
  // Other fields exist but we only type what we need
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useTenderDetails(tenderId: number | null | undefined) {
  return useQuery<RmiTenderDetails | null>({
    queryKey: ["rmi-tender-details", tenderId],
    queryFn: async () => {
      if (!tenderId) return null;

      const res = await fetch(`/api/tender-details?id=${tenderId}`);
      if (!res.ok) return null;

      return (await res.json()) as RmiTenderDetails;
    },
    enabled: tenderId != null && tenderId > 0,
    staleTime: 30 * 60 * 1000, // 30 min — detail data rarely changes
  });
}
