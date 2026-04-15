/**
 * Pure utility functions for tender data manipulation.
 *
 * These are TypeScript ports of the Python functions in dashboard_utils.py
 * and analytics_engine.py. They operate on plain arrays/objects (no Supabase
 * calls) so they can run on both client and server.
 */

import {
  CLOSING_SOON_DAYS,
  DOCUMENT_DOWNLOAD_API,
  NON_ACTIVE_STATUSES,
  SCORE_WEIGHTS,
} from "@/lib/constants";
import type {
  ScoredTender,
  Tender,
  TenderDocument,
  TenderOutcome,
  TenderWithComputed,
} from "@/types/database";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Check if a watchlisted tender should be in the "expired" section.
 *
 * A tender is expired if:
 * 1. Manually forced via drag-and-drop (forced_expired = true), OR
 * 2. Deadline has passed AND results are published (status_code 2 = נדון בוועדת מכרזים)
 */
export function isExpiredTender(
  tender: Tender,
  outcome: TenderOutcome | undefined,
): boolean {
  if (outcome?.forced_expired) return true;
  const deadline = parseDate(tender.deadline);
  const deadlinePassed = deadline != null && deadline <= new Date();
  const hasResults = tender.status_code === 2;
  return deadlinePassed && hasResults;
}

/** Parse an ISO date string to a Date, returning null on failure. */
function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Calendar days between two dates (a - b). */
function diffDays(a: Date, b: Date): number {
  return Math.floor((a.getTime() - b.getTime()) / 86_400_000);
}

// ---------------------------------------------------------------------------
// filterActive
// ---------------------------------------------------------------------------

/**
 * Return only tenders with a future deadline and whose status is not in
 * NON_ACTIVE_STATUSES.
 *
 * Mirrors the Python `filter_active()` from dashboard_utils.py which
 * filters purely on deadline > now, plus we also exclude known closed
 * status strings for extra safety.
 */
export function filterActive(tenders: Tender[]): Tender[] {
  const now = new Date();
  return tenders.filter((t) => {
    // Exclude by status label
    if (t.status && NON_ACTIVE_STATUSES.includes(t.status)) {
      return false;
    }
    // Must have a future deadline
    const deadline = parseDate(t.deadline);
    if (!deadline) return false;
    return deadline > now;
  });
}

// ---------------------------------------------------------------------------
// addDaysToDeadline
// ---------------------------------------------------------------------------

/**
 * Add a computed `days_to_deadline` field to each tender.
 *
 * Positive = days remaining, negative = deadline passed.
 */
export function addDaysToDeadline(tenders: Tender[]): TenderWithComputed[] {
  const now = new Date();
  return tenders.map((t) => {
    const deadline = parseDate(t.deadline);
    return {
      ...t,
      days_to_deadline: deadline ? diffDays(deadline, now) : null,
    };
  });
}

// ---------------------------------------------------------------------------
// Scoring sub-scores (ported from analytics_engine.py)
// ---------------------------------------------------------------------------

function urgencyScore(daysToDeadline: number | null): number {
  if (daysToDeadline == null) return 0;
  if (daysToDeadline < 0) return 0;
  if (daysToDeadline <= 7) return 100;
  if (daysToDeadline <= 14) return 80;
  if (daysToDeadline <= 30) return 60;
  if (daysToDeadline <= 60) return 40;
  return 20;
}

function sizeScore(units: number | null, percentileRank: number): number {
  if (units == null || units <= 0) return 0;
  return Math.round(percentileRank * 1000) / 10; // one decimal
}

function readinessScore(hasBrochure: boolean, docsCount: number): number {
  let score = hasBrochure ? 60 : 0;
  score += Math.min(docsCount * 10, 40);
  return Math.min(score, 100);
}

function freshnessScore(publishDate: string | null): number {
  const d = parseDate(publishDate);
  if (!d) return 0;
  const daysOld = diffDays(new Date(), d);
  if (daysOld < 7) return 100;
  if (daysOld < 30) return 80;
  if (daysOld < 90) return 50;
  if (daysOld < 180) return 30;
  return 10;
}

function locationScore(
  region: string | null,
  regionDensity: Record<string, number>,
): number {
  if (!region || !(region in regionDensity)) return 50;
  return Math.round(regionDensity[region] * 1000) / 10;
}

// ---------------------------------------------------------------------------
// scoreAllTenders
// ---------------------------------------------------------------------------

/**
 * Compute composite scores for all tenders.
 *
 * Matches the scoring algorithm from analytics_engine.py `score_all_tenders`.
 * Weights: urgency 20%, size 20%, readiness 25%, location 20%, freshness 15%.
 */
export function scoreAllTenders(
  tenders: TenderWithComputed[],
): ScoredTender[] {
  if (tenders.length === 0) return [];

  // Pre-compute region density (percentile rank of count per region)
  const regionCounts: Record<string, number> = {};
  for (const t of tenders) {
    if (t.region) {
      regionCounts[t.region] = (regionCounts[t.region] ?? 0) + 1;
    }
  }

  const countValues = Object.values(regionCounts).sort((a, b) => a - b);
  const regionDensity: Record<string, number> = {};
  for (const [region, count] of Object.entries(regionCounts)) {
    // Percentile rank: fraction of values <= this count
    const rank =
      countValues.filter((v) => v <= count).length / countValues.length;
    regionDensity[region] = rank;
  }

  // Pre-compute units percentile rank
  const unitValues = tenders
    .map((t) => (t.units != null && t.units > 0 ? t.units : 0))
    .sort((a, b) => a - b);

  function getUnitsPercentile(units: number | null): number {
    const u = units != null && units > 0 ? units : 0;
    const rank = unitValues.filter((v) => v <= u).length / unitValues.length;
    return rank;
  }

  return tenders.map((t) => {
    const urg = urgencyScore(t.days_to_deadline);
    const sz = sizeScore(t.units, getUnitsPercentile(t.units));
    const rdy = readinessScore(
      Boolean(t.published_booklet),
      0, // docs_count not on the Tender type; pass 0 (same as Python default)
    );
    const loc = locationScore(t.region, regionDensity);
    const fresh = freshnessScore(t.publish_date);

    const total =
      urg * SCORE_WEIGHTS.urgency +
      sz * SCORE_WEIGHTS.size +
      rdy * SCORE_WEIGHTS.readiness +
      loc * SCORE_WEIGHTS.location +
      fresh * SCORE_WEIGHTS.freshness;

    return {
      ...t,
      total_score: Math.round(total * 10) / 10,
      urgency_score: urg,
      size_score: sz,
      readiness_score: rdy,
      location_score: loc,
      freshness_score: fresh,
    };
  });
}

// ---------------------------------------------------------------------------
// findNewTenderIds
// ---------------------------------------------------------------------------

/**
 * Detect tender IDs present in `current` but absent from `previous`.
 */
export function findNewTenderIds(
  current: Tender[],
  previous: Tender[],
): Set<number> {
  const prevIds = new Set(previous.map((t) => t.tender_id));
  const newIds = new Set<number>();
  for (const t of current) {
    if (!prevIds.has(t.tender_id)) {
      newIds.add(t.tender_id);
    }
  }
  return newIds;
}

// ---------------------------------------------------------------------------
// getClosingSoonTenders
// ---------------------------------------------------------------------------

/**
 * Filter tenders closing within the next N days (default: CLOSING_SOON_DAYS).
 */
export function getClosingSoonTenders(
  tenders: TenderWithComputed[],
  days: number = CLOSING_SOON_DAYS,
): TenderWithComputed[] {
  return tenders.filter((t) => {
    if (t.days_to_deadline == null) return false;
    return t.days_to_deadline >= 0 && t.days_to_deadline <= days;
  });
}

// ---------------------------------------------------------------------------
// buildDocumentUrl
// ---------------------------------------------------------------------------

/**
 * Build a direct download URL for a tender document.
 *
 * Mirrors the Python `build_document_url()` from data_client.py. The RMI
 * GetFileContent endpoint accepts query params to serve the file directly.
 */
export function buildDocumentUrl(doc: TenderDocument): string {
  const params = new URLSearchParams({
    michrazId: String(doc.tender_id),
    rowId: String(doc.row_id),
    size: String(doc.size ?? 0),
    typePirsum: String(doc.pirsum_type ?? 0),
    fileName: doc.doc_name ?? "document.pdf",
    teur: doc.description ?? "",
    fileType: doc.file_type ?? "application/pdf",
  });
  return `${DOCUMENT_DOWNLOAD_API}?${params.toString()}`;
}
