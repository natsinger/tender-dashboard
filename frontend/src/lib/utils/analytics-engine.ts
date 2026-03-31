/**
 * Market analytics engine for the MEGIDO tender dashboard.
 *
 * TypeScript port of analytics_engine.py. Provides pure functions
 * over tender arrays for regional hotspot analysis, supply pipeline
 * metrics, seasonal patterns, price analytics, and competitive
 * intelligence. Every public function accepts typed arrays and returns
 * plain objects/arrays suitable for Recharts charting.
 *
 * Sections:
 *   1. Regional Hotspot Analysis
 *   2. Supply Pipeline Analysis
 *   3. Seasonal Patterns
 *   4. Price Analytics
 *   5. Competitive Intelligence
 *   6. Scoring System (re-exports from tenders.ts)
 */

import { SCORE_WEIGHTS } from "@/lib/constants";
import type {
  Tender,
  TenderPrice,
  TenderWithComputed,
  ScoredTender,
  TabaAnalytics,
  BuildingRight,
} from "@/types/database";

// ---------------------------------------------------------------------------
// Hebrew locale constants
// ---------------------------------------------------------------------------

export const MONTH_NAMES_HE: Record<number, string> = {
  1: "ינואר",
  2: "פברואר",
  3: "מרץ",
  4: "אפריל",
  5: "מאי",
  6: "יוני",
  7: "יולי",
  8: "אוגוסט",
  9: "ספטמבר",
  10: "אוקטובר",
  11: "נובמבר",
  12: "דצמבר",
};

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

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

/** Get year-month key string from a Date, e.g. "2025-03". */
function yearMonthKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

/** Get ISO week start (Monday) for a given date. */
function weekStart(d: Date): Date {
  const result = new Date(d);
  const day = result.getDay();
  // Monday=1 => offset = (day + 6) % 7
  const diff = (day + 6) % 7;
  result.setDate(result.getDate() - diff);
  result.setHours(0, 0, 0, 0);
  return result;
}

/** Round a number to N decimal places. */
function round(value: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  return Math.round(value * factor) / factor;
}

// ---------------------------------------------------------------------------
// 1. REGIONAL HOTSPOT ANALYSIS
// ---------------------------------------------------------------------------

export interface RegionalVolumeRow {
  date: string;
  region: string;
  count: number;
}

/**
 * Tender count by region over time (monthly).
 *
 * Groups tenders by their publish_date (floored to month) and region,
 * counting how many tenders were published in each bucket.
 */
export function regionalTenderVolume(
  tenders: Tender[],
): RegionalVolumeRow[] {
  if (tenders.length === 0) return [];

  const buckets: Record<string, Record<string, number>> = {};

  for (const t of tenders) {
    const pub = parseDate(t.publish_date);
    if (!pub || !t.region) continue;

    const key = yearMonthKey(pub);
    if (!buckets[key]) buckets[key] = {};
    buckets[key][t.region] = (buckets[key][t.region] ?? 0) + 1;
  }

  const result: RegionalVolumeRow[] = [];
  for (const [date, regions] of Object.entries(buckets)) {
    for (const [region, count] of Object.entries(regions)) {
      result.push({ date, region, count });
    }
  }

  return result.sort((a, b) => a.date.localeCompare(b.date));
}

// ---------------------------------------------------------------------------

export interface MomentumRow {
  region: string;
  recentCount: number;
  previousCount: number;
  changePct: number;
  direction: "up" | "down" | "stable";
}

/**
 * Which regions are heating up / cooling down.
 *
 * Compares tender count in the most recent `windowDays` against the
 * preceding window of the same length.
 */
export function regionalMomentum(
  tenders: Tender[],
  windowDays: number = 90,
): MomentumRow[] {
  if (tenders.length === 0) return [];

  const now = new Date();
  const recentStart = new Date(now.getTime() - windowDays * 86_400_000);
  const previousStart = new Date(recentStart.getTime() - windowDays * 86_400_000);

  const recentCounts: Record<string, number> = {};
  const prevCounts: Record<string, number> = {};

  for (const t of tenders) {
    const pub = parseDate(t.publish_date);
    if (!pub || !t.region) continue;

    if (pub >= recentStart && pub < now) {
      recentCounts[t.region] = (recentCounts[t.region] ?? 0) + 1;
    } else if (pub >= previousStart && pub < recentStart) {
      prevCounts[t.region] = (prevCounts[t.region] ?? 0) + 1;
    }
  }

  const allRegions = new Set([
    ...Object.keys(recentCounts),
    ...Object.keys(prevCounts),
  ]);

  const result: MomentumRow[] = [];
  for (const region of allRegions) {
    const recent = recentCounts[region] ?? 0;
    const prev = prevCounts[region] ?? 0;

    let changePct: number;
    if (prev > 0) {
      changePct = round(((recent - prev) / prev) * 100, 1);
    } else {
      changePct = recent > 0 ? 100 : 0;
    }

    let direction: "up" | "down" | "stable";
    if (changePct > 10) direction = "up";
    else if (changePct < -10) direction = "down";
    else direction = "stable";

    result.push({ region, recentCount: recent, previousCount: prev, changePct, direction });
  }

  return result.sort((a, b) => b.changePct - a.changePct);
}

// ---------------------------------------------------------------------------
// 2. SUPPLY PIPELINE ANALYSIS
// ---------------------------------------------------------------------------

export interface SupplyPipelineRow {
  date: string;
  newPublished: number;
  closing: number;
  activeNet: number;
}

/**
 * Active tenders over time: new published, closing, net change.
 *
 * For each month counts how many tenders had their publish_date in
 * that period (new) and how many had their deadline in that period (closing).
 */
export function supplyPipeline(tenders: Tender[]): SupplyPipelineRow[] {
  if (tenders.length === 0) return [];

  const newByMonth: Record<string, number> = {};
  const closeByMonth: Record<string, number> = {};

  for (const t of tenders) {
    const pub = parseDate(t.publish_date);
    if (pub) {
      const key = yearMonthKey(pub);
      newByMonth[key] = (newByMonth[key] ?? 0) + 1;
    }
    const dead = parseDate(t.deadline);
    if (dead) {
      const key = yearMonthKey(dead);
      closeByMonth[key] = (closeByMonth[key] ?? 0) + 1;
    }
  }

  const allMonths = new Set([
    ...Object.keys(newByMonth),
    ...Object.keys(closeByMonth),
  ]);

  const result: SupplyPipelineRow[] = [];
  for (const date of allMonths) {
    const newPublished = newByMonth[date] ?? 0;
    const closing = closeByMonth[date] ?? 0;
    result.push({
      date,
      newPublished,
      closing,
      activeNet: newPublished - closing,
    });
  }

  return result.sort((a, b) => a.date.localeCompare(b.date));
}

// ---------------------------------------------------------------------------
// 3. SEASONAL PATTERNS
// ---------------------------------------------------------------------------

export interface MonthlyDistributionRow {
  month: number;
  monthNameHe: string;
  avgCount: number;
  totalCount: number;
}

/**
 * Monthly distribution of tender publications aggregated across years.
 *
 * For each calendar month (1-12), calculates the average and total number
 * of tenders published in that month across all years in the dataset.
 */
export function monthlyPublicationDistribution(
  tenders: Tender[],
): MonthlyDistributionRow[] {
  if (tenders.length === 0) return [];

  // Group by year-month
  const yearlyMonthly: Record<number, Record<number, number>> = {};
  const years = new Set<number>();

  for (const t of tenders) {
    const pub = parseDate(t.publish_date);
    if (!pub) continue;

    const y = pub.getFullYear();
    const m = pub.getMonth() + 1;
    years.add(y);

    if (!yearlyMonthly[y]) yearlyMonthly[y] = {};
    yearlyMonthly[y][m] = (yearlyMonthly[y][m] ?? 0) + 1;
  }

  const nYears = years.size;
  if (nYears === 0) return [];

  const result: MonthlyDistributionRow[] = [];
  for (let month = 1; month <= 12; month++) {
    let total = 0;
    for (const y of years) {
      total += yearlyMonthly[y]?.[month] ?? 0;
    }
    result.push({
      month,
      monthNameHe: MONTH_NAMES_HE[month],
      avgCount: round(total / nYears, 1),
      totalCount: total,
    });
  }

  return result;
}

// ---------------------------------------------------------------------------

export interface VolumeMovingAverageRow {
  date: string;
  ma30: number;
  ma60: number;
  ma90: number;
}

/**
 * Compute rolling tender publication counts for 30/60/90 day windows.
 *
 * For each calendar day in the dataset, counts how many tenders were
 * published within the trailing N days for each window size.
 */
export function volumeMovingAverages(
  tenders: Tender[],
): VolumeMovingAverageRow[] {
  if (tenders.length === 0) return [];

  // Collect valid publish dates
  const dates: Date[] = [];
  for (const t of tenders) {
    const pub = parseDate(t.publish_date);
    if (pub) dates.push(pub);
  }
  if (dates.length === 0) return [];

  dates.sort((a, b) => a.getTime() - b.getTime());

  const minDate = dates[0];
  const maxDate = dates[dates.length - 1];

  // Build daily counts
  const dailyCounts: Record<string, number> = {};
  for (const d of dates) {
    const key = d.toISOString().slice(0, 10);
    dailyCounts[key] = (dailyCounts[key] ?? 0) + 1;
  }

  // Fill date range
  const allDays: string[] = [];
  const cursor = new Date(minDate);
  cursor.setHours(0, 0, 0, 0);
  const end = new Date(maxDate);
  end.setHours(0, 0, 0, 0);

  while (cursor <= end) {
    allDays.push(cursor.toISOString().slice(0, 10));
    cursor.setDate(cursor.getDate() + 1);
  }

  // Compute rolling sums
  const counts = allDays.map((d) => dailyCounts[d] ?? 0);
  const windows = [30, 60, 90] as const;

  const result: VolumeMovingAverageRow[] = [];
  for (let i = 0; i < allDays.length; i++) {
    const row: VolumeMovingAverageRow = {
      date: allDays[i],
      ma30: 0,
      ma60: 0,
      ma90: 0,
    };

    for (const w of windows) {
      let sum = 0;
      const start = Math.max(0, i - w + 1);
      for (let j = start; j <= i; j++) {
        sum += counts[j];
      }
      const key = `ma${w}` as "ma30" | "ma60" | "ma90";
      row[key] = sum;
    }

    result.push(row);
  }

  // Downsample: return only weekly points to keep data manageable
  // (for charts, every 7th day is plenty of resolution)
  if (result.length > 200) {
    return result.filter((_, i) => i % 7 === 0 || i === result.length - 1);
  }
  return result;
}

// ---------------------------------------------------------------------------
// 4. PRICE ANALYTICS
// ---------------------------------------------------------------------------

export interface PriceTrendRow {
  date: string;
  region: string;
  avgPricePerSqm: number;
  count: number;
}

/**
 * Average winning price per sqm by region over time.
 *
 * Joins price data with tender metadata to get region and publish_date,
 * then computes average price per square metre per region per month.
 */
export function priceTrendsByRegion(
  prices: TenderPrice[],
  tenders: Tender[],
): PriceTrendRow[] {
  if (prices.length === 0 || tenders.length === 0) return [];

  // Build tender lookup
  const tenderMap = new Map<number, Tender>();
  for (const t of tenders) {
    tenderMap.set(t.tender_id, t);
  }

  // Group by month+region
  const buckets: Record<string, { sum: number; count: number }> = {};

  for (const p of prices) {
    const winBid = p.winning_bid;
    const area = p.land_area;
    if (!winBid || !area || winBid <= 0 || area <= 0) continue;

    const tender = tenderMap.get(p.tender_id);
    if (!tender?.region || !tender.publish_date) continue;

    const pub = parseDate(tender.publish_date);
    if (!pub) continue;

    const key = `${yearMonthKey(pub)}|${tender.region}`;
    if (!buckets[key]) buckets[key] = { sum: 0, count: 0 };
    buckets[key].sum += winBid / area;
    buckets[key].count += 1;
  }

  const result: PriceTrendRow[] = [];
  for (const [key, val] of Object.entries(buckets)) {
    const [date, region] = key.split("|");
    result.push({
      date,
      region,
      avgPricePerSqm: round(val.sum / val.count, 2),
      count: val.count,
    });
  }

  return result.sort((a, b) => a.date.localeCompare(b.date));
}

// ---------------------------------------------------------------------------

export interface TabaSummaryRow {
  planNumber: string;
  tenderCount: number;
  totalUnits: number | null;
  totalLandArea: number | null;
  avgAppraisalPrice: number | null;
  avgFloorPrice: number | null;
  avgWinningBid: number | null;
  premiumVsAppraisalPct: number | null;
  premiumVsFloorPct: number | null;
  firstSeen: string | null;
  lastSeen: string | null;
  tenderRatePerYear: number | null;
}

/**
 * Summary of taba (zoning plan) analytics.
 *
 * Passes through key fields from the taba_analytics table and computes
 * a tender_rate_per_year metric.
 */
export function tabaAnalysisSummary(
  tabaData: TabaAnalytics[],
): TabaSummaryRow[] {
  if (tabaData.length === 0) return [];

  return tabaData.map((row) => {
    const firstSeen = parseDate(row.first_seen);
    const lastSeen = parseDate(row.last_seen);
    const tenderCount = row.tender_count ?? 0;

    let tenderRatePerYear: number | null = null;
    if (firstSeen && lastSeen) {
      const spanDays = diffDays(lastSeen, firstSeen);
      const spanYears = spanDays / 365.25;
      tenderRatePerYear =
        spanYears > 0 ? round(tenderCount / spanYears, 2) : tenderCount;
    } else {
      tenderRatePerYear = tenderCount;
    }

    return {
      planNumber: row.plan_number,
      tenderCount,
      totalUnits: row.total_units,
      totalLandArea: row.total_land_area,
      avgAppraisalPrice: row.avg_appraisal_price,
      avgFloorPrice: row.avg_floor_price,
      avgWinningBid: row.avg_winning_bid,
      premiumVsAppraisalPct: row.premium_vs_appraisal_pct,
      premiumVsFloorPct: row.premium_vs_floor_pct,
      firstSeen: row.first_seen,
      lastSeen: row.last_seen,
      tenderRatePerYear,
    };
  });
}

// ---------------------------------------------------------------------------

export interface PricePremiumRow {
  tenderId: number;
  appraisalPrice: number | null;
  floorPrice: number | null;
  winningPrice: number;
  premiumVsAppraisalPct: number | null;
  premiumVsFloorPct: number | null;
  region: string | null;
}

/**
 * Winning bid premium/discount vs RMI appraisal, with floor price.
 *
 * Primary benchmark is the appraisal price. Floor price is kept as
 * a reference column.
 */
export function pricePremiumAnalysis(
  prices: TenderPrice[],
  tenders: Tender[],
): PricePremiumRow[] {
  if (prices.length === 0) return [];

  const tenderMap = new Map<number, Tender>();
  for (const t of tenders) {
    tenderMap.set(t.tender_id, t);
  }

  const result: PricePremiumRow[] = [];

  for (const p of prices) {
    if (!p.winning_bid || p.winning_bid <= 0) continue;

    const tender = tenderMap.get(p.tender_id);
    const region = tender?.region ?? null;

    let premiumVsAppraisal: number | null = null;
    if (p.appraisal_price && p.appraisal_price > 0) {
      premiumVsAppraisal = round(
        ((p.winning_bid - p.appraisal_price) / p.appraisal_price) * 100,
        2,
      );
    }

    let premiumVsFloor: number | null = null;
    if (p.floor_price && p.floor_price > 0) {
      premiumVsFloor = round(
        ((p.winning_bid - p.floor_price) / p.floor_price) * 100,
        2,
      );
    }

    result.push({
      tenderId: p.tender_id,
      appraisalPrice: p.appraisal_price,
      floorPrice: p.floor_price,
      winningPrice: p.winning_bid,
      premiumVsAppraisalPct: premiumVsAppraisal,
      premiumVsFloorPct: premiumVsFloor,
      region,
    });
  }

  return result;
}

// ---------------------------------------------------------------------------
// 5. COMPETITIVE INTELLIGENCE
// ---------------------------------------------------------------------------

export interface LifecycleRow {
  region: string;
  tenderType: string;
  avgLifecycleDays: number;
  medianLifecycleDays: number;
  count: number;
}

/**
 * Compute lifecycle duration statistics for closed tenders by region and type.
 *
 * For closed tenders (status_code === 5), calculates the average and median
 * number of days from publish_date to deadline, grouped by region and tender_type.
 */
export function tenderLifecycleAnalysis(tenders: Tender[]): LifecycleRow[] {
  if (tenders.length === 0) return [];

  // Filter to closed tenders
  const closed = tenders.filter(
    (t) => t.status_code != null && t.status_code === 5,
  );
  if (closed.length === 0) return [];

  // Group by region+type and collect days
  const groups: Record<string, number[]> = {};

  for (const t of closed) {
    const pub = parseDate(t.publish_date);
    const dead = parseDate(t.deadline);
    if (!pub || !dead) continue;

    const days = diffDays(dead, pub);
    const region = t.region ?? "unknown";
    const tType = t.tender_type ?? "unknown";
    const key = `${region}|${tType}`;

    if (!groups[key]) groups[key] = [];
    groups[key].push(days);
  }

  const result: LifecycleRow[] = [];
  for (const [key, daysList] of Object.entries(groups)) {
    const [region, tenderType] = key.split("|");
    const sorted = [...daysList].sort((a, b) => a - b);
    const avg = round(sorted.reduce((s, v) => s + v, 0) / sorted.length, 1);
    const mid = Math.floor(sorted.length / 2);
    const median =
      sorted.length % 2 === 0
        ? round((sorted[mid - 1] + sorted[mid]) / 2, 1)
        : sorted[mid];

    result.push({
      region,
      tenderType,
      avgLifecycleDays: avg,
      medianLifecycleDays: median,
      count: sorted.length,
    });
  }

  return result;
}

// ---------------------------------------------------------------------------

export interface DeadlineOverlapRow {
  weekStart: string;
  tenderCount: number;
  regionsInvolved: string;
  competitionLevel: "low" | "medium" | "high";
}

/**
 * Identify weeks with overlapping tender deadlines and assess competition.
 *
 * Groups tenders by the Monday of their deadline week and counts how many
 * deadlines fall in each week, along with which regions are involved.
 */
export function deadlineOverlapAnalysis(
  tenders: Tender[],
): DeadlineOverlapRow[] {
  if (tenders.length === 0) return [];

  const buckets: Record<string, { count: number; regions: Set<string> }> = {};

  for (const t of tenders) {
    const dead = parseDate(t.deadline);
    if (!dead) continue;

    const ws = weekStart(dead);
    const key = ws.toISOString().slice(0, 10);

    if (!buckets[key]) buckets[key] = { count: 0, regions: new Set() };
    buckets[key].count += 1;
    if (t.region) buckets[key].regions.add(t.region);
  }

  const result: DeadlineOverlapRow[] = [];
  for (const [ws, data] of Object.entries(buckets)) {
    let level: "low" | "medium" | "high";
    if (data.count >= 6) level = "high";
    else if (data.count >= 3) level = "medium";
    else level = "low";

    result.push({
      weekStart: ws,
      tenderCount: data.count,
      regionsInvolved: [...data.regions].sort().join(", "),
      competitionLevel: level,
    });
  }

  return result.sort((a, b) => a.weekStart.localeCompare(b.weekStart));
}

// ---------------------------------------------------------------------------

export interface SaturationRow {
  region: string;
  activeCount: number;
  closedCount: number;
  totalUnits: number;
  saturationScore: number;
  trend: "saturating" | "opening" | "stable";
}

/**
 * Compute a saturation score per region based on active tender density.
 *
 * Looks at tenders published within the last `lookbackMonths` months and
 * counts active vs closed tenders per region. The saturation_score is
 * normalized to 0-100 relative to the maximum active count.
 */
export function regionSaturationIndex(
  tenders: Tender[],
  lookbackMonths: number = 6,
): SaturationRow[] {
  if (tenders.length === 0) return [];

  const now = new Date();
  const cutoff = new Date(now);
  cutoff.setMonth(cutoff.getMonth() - lookbackMonths);

  // Filter to lookback window
  const recent = tenders.filter((t) => {
    const pub = parseDate(t.publish_date);
    return pub && pub >= cutoff && t.region;
  });

  if (recent.length === 0) return [];

  const midpoint = new Date(cutoff.getTime() + (now.getTime() - cutoff.getTime()) / 2);

  // Group by region
  const regionStats: Record<
    string,
    {
      active: number;
      closed: number;
      units: number;
      firstHalfActive: number;
      secondHalfActive: number;
    }
  > = {};

  for (const t of recent) {
    const pub = parseDate(t.publish_date)!;
    const region = t.region!;
    if (!regionStats[region]) {
      regionStats[region] = {
        active: 0,
        closed: 0,
        units: 0,
        firstHalfActive: 0,
        secondHalfActive: 0,
      };
    }

    const isClosed = t.status_code === 5;
    if (isClosed) {
      regionStats[region].closed += 1;
    } else {
      regionStats[region].active += 1;
      if (pub < midpoint) {
        regionStats[region].firstHalfActive += 1;
      } else {
        regionStats[region].secondHalfActive += 1;
      }
    }

    regionStats[region].units += t.units ?? 0;
  }

  const maxActive = Math.max(
    ...Object.values(regionStats).map((s) => s.active),
  );

  const result: SaturationRow[] = [];
  for (const [region, stats] of Object.entries(regionStats)) {
    const score =
      maxActive > 0 ? round((stats.active / maxActive) * 100, 1) : 0;

    let trend: "saturating" | "opening" | "stable";
    const fc = stats.firstHalfActive;
    const sc = stats.secondHalfActive;
    if (fc === 0 && sc === 0) {
      trend = "stable";
    } else if (fc === 0) {
      trend = "saturating";
    } else if (Math.abs(sc - fc) / fc <= 0.2) {
      trend = "stable";
    } else if (sc > fc) {
      trend = "saturating";
    } else {
      trend = "opening";
    }

    result.push({
      region,
      activeCount: stats.active,
      closedCount: stats.closed,
      totalUnits: stats.units,
      saturationScore: score,
      trend,
    });
  }

  return result.sort((a, b) => b.saturationScore - a.saturationScore);
}

// ---------------------------------------------------------------------------

export interface DocumentIntelligenceRow {
  region: string;
  avgDocs: number;
  brochureRatePct: number;
  totalTenders: number;
}

/**
 * Analyse document availability and brochure rates per region.
 *
 * Computes brochure availability percentage per region.
 * Note: docs_count is not on the Tender type, so we use 0 as default.
 */
export function documentIntelligence(
  tenders: Tender[],
): DocumentIntelligenceRow[] {
  if (tenders.length === 0) return [];

  const groups: Record<string, { total: number; withBrochure: number }> = {};

  for (const t of tenders) {
    if (!t.region) continue;
    if (!groups[t.region]) groups[t.region] = { total: 0, withBrochure: 0 };
    groups[t.region].total += 1;
    if (t.published_booklet) {
      groups[t.region].withBrochure += 1;
    }
  }

  const result: DocumentIntelligenceRow[] = [];
  for (const [region, stats] of Object.entries(groups)) {
    result.push({
      region,
      avgDocs: 0, // docs_count not available on Tender type
      brochureRatePct:
        stats.total > 0
          ? round((stats.withBrochure / stats.total) * 100, 1)
          : 0,
      totalTenders: stats.total,
    });
  }

  return result.sort((a, b) => b.totalTenders - a.totalTenders);
}

// ---------------------------------------------------------------------------
// 6. SCORING SYSTEM
// ---------------------------------------------------------------------------

/** Get top N scored tenders, sorted by total_score descending. */
export function getTopTenders(
  tenders: ScoredTender[],
  n: number = 20,
): ScoredTender[] {
  if (tenders.length === 0) return [];
  return [...tenders]
    .sort((a, b) => b.total_score - a.total_score)
    .slice(0, n);
}

export interface ScoreDistribution {
  bins: number[];
  counts: number[];
  mean: number;
  median: number;
  std: number;
}

/**
 * Returns histogram data for score distribution.
 *
 * Bins scores into 10 equal-width bins from 0 to 100.
 */
export function getScoreDistribution(
  tenders: ScoredTender[],
): ScoreDistribution {
  const empty: ScoreDistribution = {
    bins: [],
    counts: [],
    mean: 0,
    median: 0,
    std: 0,
  };

  if (tenders.length === 0) return empty;

  const scores = tenders
    .map((t) => t.total_score)
    .filter((s) => s != null && !Number.isNaN(s));

  if (scores.length === 0) return empty;

  // Build 10 bins from 0 to 100
  const numBins = 10;
  const binWidth = 100 / numBins;
  const bins: number[] = [];
  const counts: number[] = new Array(numBins).fill(0);

  for (let i = 0; i <= numBins; i++) {
    bins.push(i * binWidth);
  }

  for (const s of scores) {
    let idx = Math.floor(s / binWidth);
    if (idx >= numBins) idx = numBins - 1;
    if (idx < 0) idx = 0;
    counts[idx] += 1;
  }

  // Stats
  const sorted = [...scores].sort((a, b) => a - b);
  const sum = sorted.reduce((a, b) => a + b, 0);
  const mean = round(sum / sorted.length, 1);
  const mid = Math.floor(sorted.length / 2);
  const median =
    sorted.length % 2 === 0
      ? round((sorted[mid - 1] + sorted[mid]) / 2, 1)
      : sorted[mid];

  const variance =
    sorted.reduce((acc, v) => acc + (v - mean) ** 2, 0) / sorted.length;
  const std = round(Math.sqrt(variance), 1);

  return { bins, counts, mean, median, std };
}

// ---------------------------------------------------------------------------
// 7. MULTI-LOT COMPARISON
// ---------------------------------------------------------------------------

export interface MultiLotTenderGroup {
  tenderId: number;
  tenderName: string;
  city: string;
  tenderType: string;
  lots: MultiLotRow[];
  /** Building rights rows from section 5 of the Taba, per תא שטח. */
  buildingRights: BuildingRight[];
}

export interface MultiLotRow {
  tikId: number;
  mitchamName: string | null;
  appraisalPrice: number | null;
  winningBid: number | null;
  devCosts: number | null;
  capacityUnits: number | null;
  sqmPerUnit: number | null;
  valuePerUnit: number | null;
  numBids: number | null;
  winningRank: number | null;
}

/**
 * Build comparison data for tenders that have more than one lot (tik).
 *
 * Groups tender_prices rows by tender_id, keeps only tenders with 2+
 * lots, and joins with tender metadata for city/type. Computes derived
 * fields (sqm per unit, value per unit) and winning rank (position
 * among bidders based on winning_bid vs highest_bid).
 *
 * When a buildingRightsMap is provided, enriches each tender group with
 * aggregated designation areas (commercial, employment, public institutions)
 * from section 5 of the Taba document.
 */
export function buildMultiLotComparison(
  prices: TenderPrice[],
  tenders: Tender[],
  buildingRightsMap?: Map<string, BuildingRight[]>,
): MultiLotTenderGroup[] {
  if (prices.length === 0 || tenders.length === 0) return [];

  // Build tender lookup
  const tenderMap = new Map<number, Tender>();
  for (const t of tenders) {
    tenderMap.set(t.tender_id, t);
  }

  // Group prices by tender_id
  const pricesByTender = new Map<number, TenderPrice[]>();
  for (const p of prices) {
    const existing = pricesByTender.get(p.tender_id);
    if (existing) {
      existing.push(p);
    } else {
      pricesByTender.set(p.tender_id, [p]);
    }
  }

  const result: MultiLotTenderGroup[] = [];

  for (const [tenderId, tenderPrices] of pricesByTender) {
    // Only multi-lot tenders
    if (tenderPrices.length < 2) continue;

    // Skip tenders with no actual results (all bids null, 0 bidders)
    const hasResults = tenderPrices.some(
      (p) => p.winning_bid != null || (p.num_bids != null && p.num_bids > 0),
    );
    if (!hasResults) continue;

    const tender = tenderMap.get(tenderId);
    if (!tender) continue;

    const lots: MultiLotRow[] = tenderPrices.map((p) => {
      const units = p.capacity_units;
      const area = p.land_area;
      const bid = p.winning_bid;

      const sqmPerUnit =
        area && units && units > 0 ? round(area / units, 1) : null;
      const valuePerUnit =
        bid && units && units > 0 ? round(bid / units, 0) : null;

      // Winning rank: if we have highest_bid and winning_bid, we can
      // approximate position. Rank 1 = winner had the highest bid.
      let winningRank: number | null = null;
      if (bid && p.num_bids && p.num_bids > 0) {
        // If winning_bid equals highest_bid → rank 1
        if (p.highest_bid && p.highest_bid > 0) {
          winningRank = bid >= p.highest_bid ? 1 : null;
        }
      }

      return {
        tikId: p.tik_id,
        mitchamName: p.mitcham_name,
        appraisalPrice: p.appraisal_price,
        winningBid: bid,
        devCosts: p.dev_costs,
        capacityUnits: units,
        sqmPerUnit,
        valuePerUnit,
        numBids: p.num_bids,
        winningRank,
      };
    });

    // Attach building rights for this tender's plan
    const planNumber = tender.plan_number;
    const rights = planNumber
      ? buildingRightsMap?.get(planNumber) ?? []
      : [];

    result.push({
      tenderId,
      tenderName: tender.tender_name ?? `מכרז ${tenderId}`,
      city: tender.city ?? "\u2014",
      tenderType: tender.tender_type ?? "\u2014",
      lots,
      buildingRights: rights,
    });
  }

  // Sort by tender_id descending (most recent first)
  return result.sort((a, b) => b.tenderId - a.tenderId);
}

// ---------------------------------------------------------------------------
// Radar data helper
// ---------------------------------------------------------------------------

export interface RadarDataPoint {
  dimension: string;
  value: number;
  fullMark: number;
}

/**
 * Get radar chart data for a single scored tender.
 *
 * Returns the 5 scoring dimensions with Hebrew labels.
 */
export function getRadarData(tender: ScoredTender): RadarDataPoint[] {
  return [
    { dimension: "דחיפות", value: tender.urgency_score, fullMark: 100 },
    { dimension: "גודל", value: tender.size_score, fullMark: 100 },
    { dimension: "מוכנות", value: tender.readiness_score, fullMark: 100 },
    { dimension: "מיקום", value: tender.location_score, fullMark: 100 },
    { dimension: "טריות", value: tender.freshness_score, fullMark: 100 },
  ];
}
