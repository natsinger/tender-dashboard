/**
 * Security migration: Enable RLS on all tables and add appropriate policies.
 *
 * Addresses critical findings:
 *   C1: Missing RLS on 9 of 10 Supabase tables
 *   C2: Anon key has INSERT/UPDATE on data tables
 *   H4: Cross-user watchlist/review access
 *
 * Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New Query).
 * Review each section before executing.
 */

-- ============================================================================
-- 1. ENABLE RLS ON ALL TABLES
-- ============================================================================

ALTER TABLE IF EXISTS tenders ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tender_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tender_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS alert_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS building_rights ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tender_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS taba_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS lot_count ENABLE ROW LEVEL SECURITY;
-- tender_lots already has RLS enabled

-- ============================================================================
-- 2. REVOKE WRITE ACCESS FROM ANON ON DATA TABLES
--    Only service_role (server-side scripts) should write to these.
-- ============================================================================

REVOKE INSERT, UPDATE, DELETE ON tenders FROM anon;
REVOKE INSERT, UPDATE, DELETE ON tender_documents FROM anon;
REVOKE INSERT, UPDATE, DELETE ON alert_history FROM anon;
REVOKE INSERT, UPDATE ON building_rights FROM anon;
REVOKE INSERT, UPDATE ON tender_prices FROM anon;
REVOKE INSERT, UPDATE ON taba_analytics FROM anon;
REVOKE INSERT, UPDATE ON lot_count FROM anon;
-- Also clean up tender_lots: RLS blocks writes, but remove the GRANT too
REVOKE INSERT, UPDATE ON tender_lots FROM anon;

-- ============================================================================
-- 3. DATA TABLE POLICIES — Read-only for authenticated users
--    These tables contain public tender data, readable by any logged-in user.
-- ============================================================================

-- tenders
CREATE POLICY "Authenticated users can read tenders"
  ON tenders FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role has full access to tenders"
  ON tenders FOR ALL
  TO service_role
  USING (true);

-- tender_documents
CREATE POLICY "Authenticated users can read tender_documents"
  ON tender_documents FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role has full access to tender_documents"
  ON tender_documents FOR ALL
  TO service_role
  USING (true);

-- building_rights
CREATE POLICY "Authenticated users can read building_rights"
  ON building_rights FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role has full access to building_rights"
  ON building_rights FOR ALL
  TO service_role
  USING (true);

-- tender_prices
CREATE POLICY "Authenticated users can read tender_prices"
  ON tender_prices FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role has full access to tender_prices"
  ON tender_prices FOR ALL
  TO service_role
  USING (true);

-- taba_analytics
CREATE POLICY "Authenticated users can read taba_analytics"
  ON taba_analytics FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role has full access to taba_analytics"
  ON taba_analytics FOR ALL
  TO service_role
  USING (true);

-- lot_count
CREATE POLICY "Authenticated users can read lot_count"
  ON lot_count FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role has full access to lot_count"
  ON lot_count FOR ALL
  TO service_role
  USING (true);

-- tender_lots (update existing: change anon policy to authenticated)
DROP POLICY IF EXISTS "Allow anon read access on tender_lots" ON tender_lots;
CREATE POLICY "Authenticated users can read tender_lots"
  ON tender_lots FOR SELECT
  TO authenticated
  USING (true);

-- ============================================================================
-- 4. USER-SCOPED POLICIES — Watchlist & Reviews
--    Users can only see and modify their own data.
-- ============================================================================

-- user_watchlist: user can only access their own rows
CREATE POLICY "Users can read own watchlist"
  ON user_watchlist FOR SELECT
  TO authenticated
  USING (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Users can insert own watchlist"
  ON user_watchlist FOR INSERT
  TO authenticated
  WITH CHECK (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Users can update own watchlist"
  ON user_watchlist FOR UPDATE
  TO authenticated
  USING (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Users can delete own watchlist"
  ON user_watchlist FOR DELETE
  TO authenticated
  USING (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Service role has full access to user_watchlist"
  ON user_watchlist FOR ALL
  TO service_role
  USING (true);

-- tender_reviews: user can only access their own rows
CREATE POLICY "Users can read own reviews"
  ON tender_reviews FOR SELECT
  TO authenticated
  USING (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Users can insert own reviews"
  ON tender_reviews FOR INSERT
  TO authenticated
  WITH CHECK (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Users can update own reviews"
  ON tender_reviews FOR UPDATE
  TO authenticated
  USING (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Users can delete own reviews"
  ON tender_reviews FOR DELETE
  TO authenticated
  USING (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Service role has full access to tender_reviews"
  ON tender_reviews FOR ALL
  TO service_role
  USING (true);

-- alert_history: user can only read their own alert history
CREATE POLICY "Users can read own alert_history"
  ON alert_history FOR SELECT
  TO authenticated
  USING (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Service role has full access to alert_history"
  ON alert_history FOR ALL
  TO service_role
  USING (true);

-- ============================================================================
-- 5. GRANT SELECT TO AUTHENTICATED (needed for RLS policies to work)
-- ============================================================================

GRANT SELECT ON tenders TO authenticated;
GRANT SELECT ON tender_documents TO authenticated;
GRANT SELECT ON building_rights TO authenticated;
GRANT SELECT ON tender_prices TO authenticated;
GRANT SELECT ON taba_analytics TO authenticated;
GRANT SELECT ON lot_count TO authenticated;
GRANT SELECT ON tender_lots TO authenticated;
GRANT SELECT ON alert_history TO authenticated;

-- user_watchlist and tender_reviews need full CRUD for authenticated
GRANT SELECT, INSERT, UPDATE, DELETE ON user_watchlist TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON tender_reviews TO authenticated;

-- Sequences for user tables
GRANT USAGE ON SEQUENCE user_watchlist_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE tender_reviews_id_seq TO authenticated;
