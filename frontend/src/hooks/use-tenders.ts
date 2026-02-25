/**
 * React Query hooks for tender data.
 *
 * All hooks use the browser-side Supabase client and handle the 1000-row
 * pagination limit automatically.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { SUPABASE_PAGE_SIZE } from "@/lib/constants";
import { supabase } from "@/lib/supabase/client";
import { addDaysToDeadline, filterActive } from "@/lib/utils/tenders";
import type { Tender, TenderWithComputed } from "@/types/database";

/**
 * Fetch all rows from a Supabase table with automatic pagination.
 *
 * The Supabase REST API returns at most 1000 rows per request.
 * This helper pages through until all rows are retrieved.
 */
async function paginatedFetch<T>(
  table: string,
  options?: {
    select?: string;
    orderBy?: string;
    ascending?: boolean;
    filters?: Array<{ column: string; op: "eq" | "gt" | "in"; value: unknown }>;
  },
): Promise<T[]> {
  const allRows: T[] = [];
  let offset = 0;

  while (true) {
    let query = supabase
      .from(table)
      .select(options?.select ?? "*");

    if (options?.filters) {
      for (const f of options.filters) {
        if (f.op === "eq") {
          query = query.eq(f.column, f.value as string | number);
        } else if (f.op === "gt") {
          query = query.gt(f.column, f.value as string | number);
        } else if (f.op === "in") {
          query = query.in(f.column, f.value as (string | number)[]);
        }
      }
    }

    if (options?.orderBy) {
      query = query.order(options.orderBy, {
        ascending: options.ascending ?? true,
      });
    }

    query = query.range(offset, offset + SUPABASE_PAGE_SIZE - 1);

    const { data, error } = await query;

    if (error) throw new Error(`Supabase ${table} fetch failed: ${error.message}`);

    const rows = (data ?? []) as T[];
    allRows.push(...rows);

    if (rows.length < SUPABASE_PAGE_SIZE) break;
    offset += SUPABASE_PAGE_SIZE;
  }

  return allRows;
}

// ---------------------------------------------------------------------------
// useTenders — paginated fetch of all tenders
// ---------------------------------------------------------------------------

/**
 * Fetch all tenders with pagination and add days_to_deadline.
 */
export function useTenders() {
  return useQuery<TenderWithComputed[]>({
    queryKey: ["tenders"],
    queryFn: async () => {
      const rows = await paginatedFetch<Tender>("tenders", {
        orderBy: "tender_id",
        ascending: true,
      });
      return addDaysToDeadline(rows);
    },
    staleTime: 5 * 60 * 1000, // 5 min
  });
}

// ---------------------------------------------------------------------------
// useTender — single tender by ID
// ---------------------------------------------------------------------------

/**
 * Fetch a single tender by its MichrazID.
 */
export function useTender(id: number | null | undefined) {
  return useQuery<Tender | null>({
    queryKey: ["tender", id],
    queryFn: async () => {
      if (!id) return null;

      const { data, error } = await supabase
        .from("tenders")
        .select("*")
        .eq("tender_id", id)
        .limit(1)
        .single();

      if (error) {
        if (error.code === "PGRST116") return null; // no rows
        throw new Error(`Fetch tender ${id} failed: ${error.message}`);
      }

      return data as Tender;
    },
    enabled: id != null && id > 0,
    staleTime: 5 * 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useActiveTenders — only active (future deadline, non-closed status)
// ---------------------------------------------------------------------------

/**
 * Fetch all tenders, then filter client-side to only active ones.
 *
 * Depends on the same cache key as useTenders so no extra network request
 * if both are used on the same page.
 */
export function useActiveTenders() {
  return useQuery<TenderWithComputed[]>({
    queryKey: ["tenders", "active"],
    queryFn: async () => {
      const rows = await paginatedFetch<Tender>("tenders", {
        orderBy: "tender_id",
        ascending: true,
      });
      const active = filterActive(rows);
      return addDaysToDeadline(active);
    },
    staleTime: 5 * 60 * 1000,
  });
}

// Re-export the paginated helper so other hook files can use it.
export { paginatedFetch };
