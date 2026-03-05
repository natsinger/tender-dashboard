/**
 * TypeScript interfaces matching all Supabase tables.
 *
 * Generated from the Python db.py TENDER_COLUMNS, user_db.py schemas,
 * and the full Supabase table definitions. Keep in sync with any DB
 * migrations.
 */

// ---------------------------------------------------------------------------
// tenders table (upserted daily from Land Authority API)
// ---------------------------------------------------------------------------

export interface Tender {
  /** MichrazID from the Land Authority API (primary key). */
  tender_id: number;
  tender_name: string | null;
  city_code: number | null;
  city: string | null;
  region: string | null;
  location: string | null;
  tender_type_code: number | null;
  tender_type: string | null;
  purpose_code: number | null;
  purpose: string | null;
  status_code: number | null;
  status: string | null;
  units: number | null;
  /** ISO date string. */
  publish_date: string | null;
  /** ISO date string (submission deadline). */
  deadline: string | null;
  /** ISO date string. */
  committee_date: string | null;
  /** 0 or 1 (treated as boolean). */
  published_booklet: number | null;
  /** 0 or 1 (treated as boolean). */
  targeted: number | null;
  area_sqm: number | null;
  min_price: number | null;
  gush: string | null;
  helka: string | null;
  // Analytics enrichment columns (Sprint 7)
  rmi_region_code: number | null;
  /** ISO date string. */
  official_publish_date: string | null;
  /** ISO date string. */
  brochure_update_date: string | null;
  target_audience: string | null;
  acquisition_form: string | null;
  participation_fee: number | null;
  tender_duration_days: number | null;
  land_area_sqm: number | null;
  plan_number: string | null;
  max_lots_per_bidder: number | null;
  lot_count: number | null;
  /** ISO datetime string set on each upsert. */
  last_updated: string | null;
  // Brochure/extraction pipeline fields
  brochure_summary: string | null;
  lots_data: Record<string, unknown> | null;
  extraction_status: string | null;
  extraction_error: string | null;
  lot_extraction_status: string | null;
  lot_extraction_date: string | null;
}

/**
 * Tender with computed client-side fields (e.g. from addDaysToDeadline).
 */
export interface TenderWithComputed extends Tender {
  days_to_deadline: number | null;
}

/**
 * Tender with scoring columns added by scoreAllTenders().
 */
export interface ScoredTender extends TenderWithComputed {
  total_score: number;
  urgency_score: number;
  size_score: number;
  readiness_score: number;
  location_score: number;
  freshness_score: number;
}

// ---------------------------------------------------------------------------
// tender_history table (daily snapshots for trend analysis)
// ---------------------------------------------------------------------------

export interface TenderHistory {
  id?: number;
  tender_id: number;
  /** ISO date string (snapshot day). */
  snapshot_date: string;
  status_code: number | null;
  status: string | null;
  units: number | null;
  /** ISO date string. */
  deadline: string | null;
}

// ---------------------------------------------------------------------------
// tender_documents table (per-tender document tracking)
// ---------------------------------------------------------------------------

export interface TenderDocument {
  id?: number;
  tender_id: number;
  /** RowID from the API's MichrazDocList. */
  row_id: number;
  doc_name: string | null;
  description: string | null;
  file_type: string | null;
  size: number | null;
  pirsum_type: number | null;
  /** ISO date string. */
  update_date: string | null;
  /** ISO date string (when we first saw this document). */
  first_seen: string | null;
}

/**
 * Document row joined with tender metadata (from get_new_documents).
 */
export interface TenderDocumentWithInfo extends TenderDocument {
  tender_name: string | null;
  city: string | null;
  region: string | null;
}

// ---------------------------------------------------------------------------
// building_rights table (Section 5 from Mavat plan PDFs)
// ---------------------------------------------------------------------------

export interface BuildingRight {
  id?: number;
  plan_number: string;
  plan_status: string | null;
  row_index: number;
  designation: string | null;
  use_type: string | null;
  area_condition: string | null;
  plot_size_absolute: number | null;
  plot_size_minimum: number | null;
  building_area_above: number | null;
  building_area_above_service: number | null;
  building_area_below: number | null;
  building_area_below_service: number | null;
  building_area_total: number | null;
  coverage_pct: number | null;
  housing_units: number | null;
  building_height: number | null;
  floors_above: number | null;
  floors_below: number | null;
  setback_rear: number | null;
  setback_front: number | null;
  setback_side: number | null;
  balcony_area: number | null;
  extra_data: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// tender_lots table (lot-level data from brochure PDFs)
// ---------------------------------------------------------------------------

export interface TenderLot {
  id?: number;
  tender_id: number;
  lot_number: number | null;
  plot_numbers: string | null;
  area_sqm: number | null;
  units_target_price: number | null;
  units_free_market: number | null;
  total_units: number | null;
  min_price: number | null;
  guarantee_amount: number | null;
  sqm_value_appraisal: number | null;
  sqm_value_current: number | null;
  discount_amount: number | null;
  development_costs: number | null;
  zoning_plan: string | null;
  zoning_designation: string | null;
  gush: string | null;
  helka: string | null;
  winner_name: string | null;
  winning_amount: number | null;
  data_source: string | null;
  /** RMI mitcham identifier (from API lots). */
  mitcham_name: string | null;
  /** Raw gush/helka array from API (JSON). */
  gush_helka_raw: Record<string, unknown>[] | null;
  /** ISO datetime string. */
  updated_at: string | null;
}

// ---------------------------------------------------------------------------
// tender_prices table (winning bids, floor prices, appraisals per plot)
// ---------------------------------------------------------------------------

export interface TenderPrice {
  id?: number;
  tender_id: number;
  tik_id: number;
  mitcham_name: string | null;
  land_area: number | null;
  floor_price: number | null;
  appraisal_price: number | null;
  winning_bid: number | null;
  winner_name: string | null;
  num_bids: number | null;
  highest_bid: number | null;
  lowest_bid: number | null;
  dev_costs: number | null;
  capacity_units: number | null;
}

// ---------------------------------------------------------------------------
// taba_analytics table (aggregated plan-level analytics)
// ---------------------------------------------------------------------------

export interface TabaAnalytics {
  id?: number;
  plan_number: string;
  tender_count: number | null;
  total_units: number | null;
  total_land_area: number | null;
  avg_appraisal_price: number | null;
  avg_floor_price: number | null;
  avg_winning_bid: number | null;
  premium_vs_appraisal_pct: number | null;
  premium_vs_floor_pct: number | null;
  region_codes: number[] | null;
  city_codes: number[] | null;
  purpose_codes: number[] | null;
  /** ISO date string. */
  first_seen: string | null;
  /** ISO date string. */
  last_seen: string | null;
}

// ---------------------------------------------------------------------------
// user_watchlist table (per-user tender watchlist)
// ---------------------------------------------------------------------------

export interface UserWatchlistItem {
  id?: number;
  user_email: string;
  tender_id: number;
  /** ISO date string. */
  created_at: string | null;
  /** 0 or 1. */
  active: number;
  notes: string | null;
}

/**
 * Watchlist row with joined tender data for display.
 */
export interface WatchlistItemWithTender extends UserWatchlistItem {
  tender: Tender | null;
}

// ---------------------------------------------------------------------------
// tender_reviews table (shared team review status)
// ---------------------------------------------------------------------------

export interface TenderReview {
  id?: number;
  tender_id: number;
  status: string;
  updated_by: string;
  /** ISO datetime string. */
  updated_at: string | null;
  notes: string;
}

// ---------------------------------------------------------------------------
// alert_history table (deduplication for email alerts)
// ---------------------------------------------------------------------------

export interface AlertHistory {
  id?: number;
  user_email: string;
  tender_id: number;
  doc_row_id: number;
  /** ISO date string. */
  sent_at: string | null;
}
