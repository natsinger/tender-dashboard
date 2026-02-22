-- ==========================================================================
-- Building Rights Schema + Plan Number Column
-- Run this in Supabase SQL Editor ONCE to set up the new tables/columns.
-- ==========================================================================

-- 1. Add plan_number column to existing tenders table
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS plan_number TEXT;
CREATE INDEX IF NOT EXISTS idx_tenders_plan_number ON tenders(plan_number);

-- 2. Create building_rights table
CREATE TABLE IF NOT EXISTS building_rights (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_number             TEXT NOT NULL,
    plan_status             TEXT,                    -- "מצב מוצע" / "מצב מאושר"
    row_index               INT NOT NULL,            -- position in table
    designation             TEXT,                    -- יעוד
    use_type                TEXT,                    -- שימוש
    area_condition          TEXT,                    -- תאי שטח
    plot_size_absolute      NUMERIC,                 -- גודל מגרש מוחלט (מ"ר)
    plot_size_minimum       NUMERIC,                 -- גודל מגרש מזערי (מ"ר)
    building_area_above     NUMERIC,                 -- שטחי בניה מעל הכניסה (עיקרי)
    building_area_above_service NUMERIC,             -- שטחי בניה מעל הכניסה (שירות)
    building_area_below     NUMERIC,                 -- שטחי בניה מתחת לכניסה (עיקרי)
    building_area_below_service NUMERIC,             -- שטחי בניה מתחת לכניסה (שירות)
    building_area_total     NUMERIC,                 -- סה"כ שטחי בניה
    coverage_pct            NUMERIC,                 -- תכסית (%)
    housing_units           INT,                     -- מספר יח"ד
    building_height         NUMERIC,                 -- גובה מבנה (מטר)
    floors_above            INT,                     -- קומות מעל הכניסה
    floors_below            INT,                     -- קומות מתחת לכניסה
    setback_rear            NUMERIC,                 -- קו בנין אחורי (מטר)
    setback_front           NUMERIC,                 -- קו בנין קדמי (מטר)
    setback_side            NUMERIC,                 -- קו בנין צידי (מטר)
    balcony_area            NUMERIC,                 -- שטח מרפסות נוסף
    extra_data              JSONB DEFAULT '{}',      -- catch-all for unexpected columns
    extracted_at            TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plan_number, plan_status, row_index)
);

CREATE INDEX IF NOT EXISTS idx_building_rights_plan ON building_rights(plan_number);

-- 3. Grant access to the anon/service_role keys used by the app
GRANT SELECT, INSERT, UPDATE ON building_rights TO anon;
GRANT SELECT, INSERT, UPDATE ON building_rights TO service_role;
GRANT USAGE ON SEQUENCE building_rights_id_seq TO anon;
GRANT USAGE ON SEQUENCE building_rights_id_seq TO service_role;

-- 4. Add brochure analysis and extraction pipeline columns to tenders
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS brochure_summary TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS lots_data JSONB DEFAULT '{}';
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS extraction_status TEXT DEFAULT 'none';
-- extraction_status values: 'none' | 'brochure_extracted' | 'queued' | 'complete' | 'failed'
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS extraction_error TEXT;

CREATE INDEX IF NOT EXISTS idx_tenders_extraction_status ON tenders(extraction_status);
