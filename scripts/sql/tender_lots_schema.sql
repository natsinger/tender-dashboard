-- ==========================================================================
-- Tender Lots Schema (lot-level data from brochure PDFs)
-- Run this in Supabase SQL Editor ONCE to set up the new table/columns.
-- Depends on: building_rights_schema.sql (must run that first).
-- ==========================================================================

-- 1. Add lot-related columns to existing tenders table
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS max_lots_per_bidder      INT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS lot_extraction_status    TEXT DEFAULT 'pending';
-- lot_extraction_status values: 'pending' | 'extracted' | 'failed' | 'no_brochure'
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS lot_extraction_date      TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_tenders_lot_extraction_status
    ON tenders(lot_extraction_status);

-- 2. Create tender_lots table (one row per lot/mitcham per tender)
CREATE TABLE IF NOT EXISTS tender_lots (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tender_id               INT NOT NULL,
    lot_number              INT,                     -- מספר מתחם
    plot_numbers            TEXT,                    -- מספר מגרש (e.g. "28,43" or "25-27,40-42")
    area_sqm                NUMERIC,                 -- שטח במ"ר ערך
    units_target_price      INT,                     -- מספר יח"ד מתב"ע במחיר מטרה (CRITICAL)
    units_free_market       INT,                     -- מספר יח"ד מתב"ע בשוק חופשי (CRITICAL)
    min_price               NUMERIC,                 -- מחיר מינימום בש"ח ללא מע"מ
    guarantee_amount        NUMERIC,                 -- גובה ערבות לקיום ההצעה בש"ח
    sqm_value_appraisal     NUMERIC,                 -- שווי מ"ר בנוי עיקרי בש"ח לפי שומה
    sqm_value_current       NUMERIC,                 -- שווי מ"ר בנוי עיקרי לפי שומה עדכנית
    discount_amount         NUMERIC,                 -- גובה ההנחה
    zoning_plan             TEXT,                    -- תב"ע/תכנית (from Section 2)
    zoning_designation      TEXT,                    -- ייעוד (from Section 2)
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tender_id, lot_number)
);

CREATE INDEX IF NOT EXISTS idx_tender_lots_tender ON tender_lots(tender_id);

-- 3. Grant access to app roles (matching existing patterns)
GRANT SELECT, INSERT, UPDATE ON tender_lots TO anon;
GRANT SELECT, INSERT, UPDATE ON tender_lots TO service_role;
GRANT USAGE ON SEQUENCE tender_lots_id_seq TO anon;
GRANT USAGE ON SEQUENCE tender_lots_id_seq TO service_role;

-- 4. Enable RLS (Row Level Security) — allow all reads, restrict writes to service_role
ALTER TABLE tender_lots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read access on tender_lots"
    ON tender_lots FOR SELECT
    TO anon
    USING (true);

CREATE POLICY "Allow service_role full access on tender_lots"
    ON tender_lots FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 5. API-first lot integration — new columns for structured API data
--    These columns were previously only available via PDF extraction;
--    now populated from the Tik[] array in tender details API response.
ALTER TABLE tender_lots ADD COLUMN IF NOT EXISTS total_units         INT;
ALTER TABLE tender_lots ADD COLUMN IF NOT EXISTS development_costs   NUMERIC;
ALTER TABLE tender_lots ADD COLUMN IF NOT EXISTS gush                TEXT;
ALTER TABLE tender_lots ADD COLUMN IF NOT EXISTS helka               TEXT;
ALTER TABLE tender_lots ADD COLUMN IF NOT EXISTS winner_name         TEXT;
ALTER TABLE tender_lots ADD COLUMN IF NOT EXISTS winning_amount      NUMERIC;
ALTER TABLE tender_lots ADD COLUMN IF NOT EXISTS data_source         TEXT DEFAULT 'pdf';
