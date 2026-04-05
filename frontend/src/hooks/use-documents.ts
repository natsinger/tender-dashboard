/**
 * React Query hooks for tender document data.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { SUPABASE_PAGE_SIZE } from "@/lib/constants";
import { supabase } from "@/lib/supabase/client";
import type { TenderDocument, TenderDocumentWithInfo } from "@/types/database";

// ---------------------------------------------------------------------------
// useTenderDocuments — all documents for a single tender
// ---------------------------------------------------------------------------

/**
 * Fetch all documents belonging to a specific tender.
 */
export function useTenderDocuments(tenderId: number | null | undefined) {
  return useQuery<TenderDocument[]>({
    queryKey: ["tender-documents", tenderId],
    queryFn: async () => {
      if (!tenderId) return [];

      const allDocs: TenderDocument[] = [];
      let offset = 0;

      while (true) {
        const { data, error } = await supabase
          .from("tender_documents")
          .select("*")
          .eq("tender_id", tenderId)
          .order("update_date", { ascending: true })
          .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

        if (error) throw new Error(`Fetch docs for tender ${tenderId} failed: ${error.message}`);

        const rows = (data ?? []) as TenderDocument[];
        allDocs.push(...rows);

        if (rows.length < SUPABASE_PAGE_SIZE) break;
        offset += SUPABASE_PAGE_SIZE;
      }

      return allDocs;
    },
    enabled: tenderId != null && tenderId > 0,
    staleTime: 5 * 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useNewDocuments — new docs in last N days with tender info
// ---------------------------------------------------------------------------

/**
 * Fetch documents published (update_date) in the last `sinceDays` days,
 * joined with tender name, city, and region.
 *
 * Uses `update_date` (the Land Authority publication date) rather than
 * `first_seen` (when our system discovered it) so that old documents
 * synced late don't appear as "new".
 */
export function useNewDocuments(sinceDays: number = 7) {
  return useQuery<TenderDocumentWithInfo[]>({
    queryKey: ["new-documents", sinceDays],
    queryFn: async () => {
      const sinceDate = new Date();
      sinceDate.setDate(sinceDate.getDate() - sinceDays);
      const sinceDateStr = sinceDate.toISOString().slice(0, 10);

      // Step 1: Fetch recently published documents (paginated)
      const allDocs: TenderDocument[] = [];
      let offset = 0;

      while (true) {
        const { data, error } = await supabase
          .from("tender_documents")
          .select("*")
          .gt("update_date", sinceDateStr)
          .order("update_date", { ascending: false })
          .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

        if (error) throw new Error(`Fetch new documents failed: ${error.message}`);

        const rows = (data ?? []) as TenderDocument[];
        allDocs.push(...rows);

        if (rows.length < SUPABASE_PAGE_SIZE) break;
        offset += SUPABASE_PAGE_SIZE;
      }

      if (allDocs.length === 0) return [];

      // Step 2: Fetch tender info for matching tender_ids
      const uniqueIds = [...new Set(allDocs.map((d) => d.tender_id))];
      const tenderInfoMap = new Map<
        number,
        { tender_name: string | null; city: string | null; region: string | null }
      >();

      // Batch in chunks of 500 (Supabase .in() has practical limits)
      const BATCH_SIZE = 500;
      for (let i = 0; i < uniqueIds.length; i += BATCH_SIZE) {
        const batch = uniqueIds.slice(i, i + BATCH_SIZE);
        const { data: tenderData, error: tenderErr } = await supabase
          .from("tenders")
          .select("tender_id, tender_name, city, region")
          .in("tender_id", batch);

        if (tenderErr) {
          if (process.env.NODE_ENV === "development") {
            console.warn("Failed to fetch tender info for new docs:", tenderErr.message);
          }
          continue;
        }

        for (const t of tenderData ?? []) {
          tenderInfoMap.set(t.tender_id as number, {
            tender_name: t.tender_name as string | null,
            city: t.city as string | null,
            region: t.region as string | null,
          });
        }
      }

      // Step 3: Merge
      return allDocs.map((doc) => {
        const info = tenderInfoMap.get(doc.tender_id);
        return {
          ...doc,
          tender_name: info?.tender_name ?? null,
          city: info?.city ?? null,
          region: info?.region ?? null,
        };
      });
    },
    staleTime: 5 * 60 * 1000,
  });
}
