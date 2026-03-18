-- ==========================================================================
-- Analytics Enrichment Schema
-- Run this in Supabase SQL Editor ONCE to add enrichment columns/tables.
-- Depends on: building_rights_schema.sql (must run that first).
-- ==========================================================================

-- 1. Add enrichment columns to existing tenders table
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS rmi_region_code       INT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS opening_date           TIMESTAMPTZ;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS brochure_update_date   TIMESTAMPTZ;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS target_audience        INT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS acquisition_form       INT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS participation_fee      NUMERIC;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS tender_duration_days   INT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS land_area_sqm          NUMERIC;

CREATE INDEX IF NOT EXISTS idx_tenders_rmi_region ON tenders(rmi_region_code);
CREATE INDEX IF NOT EXISTS idx_tenders_target_audience ON tenders(target_audience);
CREATE INDEX IF NOT EXISTS idx_tenders_duration ON tenders(tender_duration_days);

-- 2. Create tender_prices table (winning bids, floor prices, appraisals per plot/tik)
CREATE TABLE IF NOT EXISTS tender_prices (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tender_id         INT NOT NULL,
    tik_id            TEXT NOT NULL,
    mitcham_name      TEXT,                    -- plot/lot identifier
    land_area         NUMERIC,                 -- Shetach (m^2) for this tik
    floor_price       NUMERIC,                 -- MechirSaf
    appraisal_price   NUMERIC,                 -- mechirShuma
    winning_bid       NUMERIC,                 -- SchumZchiya
    winner_name       TEXT,                    -- ShemZoche
    num_bids          INT,                     -- count of mpHatzaaotMitcham
    highest_bid       NUMERIC,                 -- max(HatzaaSum)
    lowest_bid        NUMERIC,                 -- min(HatzaaSum)
    dev_costs         NUMERIC,                 -- HotzaotPituach
    capacity_units    INT,                     -- Kibolet (housing units capacity)
    extracted_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tender_id, tik_id)
);

CREATE INDEX IF NOT EXISTS idx_tender_prices_tender ON tender_prices(tender_id);
CREATE INDEX IF NOT EXISTS idx_tender_prices_winning ON tender_prices(winning_bid) WHERE winning_bid > 0;

-- 3. Create taba_analytics table (aggregated plan-level analytics)
CREATE TABLE IF NOT EXISTS taba_analytics (
    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_number               TEXT NOT NULL UNIQUE,
    tender_count              INT DEFAULT 0,           -- how many tenders reference this plan
    total_units               INT DEFAULT 0,           -- sum of housing units across tenders
    total_land_area           NUMERIC DEFAULT 0,       -- sum of land area
    avg_appraisal_price       NUMERIC,                 -- avg appraisal (שומה רמ"י) price
    avg_floor_price           NUMERIC,                 -- avg floor (מחיר סף) price
    avg_winning_bid           NUMERIC,                 -- avg winning bid
    premium_vs_appraisal_pct  NUMERIC,                 -- (avg_winning - avg_appraisal) / avg_appraisal * 100
    premium_vs_floor_pct      NUMERIC,                 -- (avg_winning - avg_floor) / avg_floor * 100
    region_codes              JSONB DEFAULT '[]',      -- unique rmi_region_codes
    city_codes                JSONB DEFAULT '[]',      -- unique city codes
    purpose_codes             JSONB DEFAULT '[]',      -- unique purpose codes
    first_seen                DATE,                    -- earliest publish_date for tenders on this plan
    last_seen                 DATE,                    -- latest publish_date
    updated_at                TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_taba_plan ON taba_analytics(plan_number);

-- 4. Grant access to app roles
GRANT SELECT, INSERT, UPDATE ON tender_prices TO anon;
GRANT SELECT, INSERT, UPDATE ON tender_prices TO service_role;
GRANT USAGE ON SEQUENCE tender_prices_id_seq TO anon;
GRANT USAGE ON SEQUENCE tender_prices_id_seq TO service_role;

GRANT SELECT, INSERT, UPDATE ON taba_analytics TO anon;
GRANT SELECT, INSERT, UPDATE ON taba_analytics TO service_role;
GRANT USAGE ON SEQUENCE taba_analytics_id_seq TO anon;
GRANT USAGE ON SEQUENCE taba_analytics_id_seq TO service_role;
