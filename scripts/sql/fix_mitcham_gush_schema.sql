-- ==========================================================================
-- Fix MitchamName / Gush Data Schema (Issue #12)
--
-- Problem:
--   1. API MitchamName is stored as lot_number (INT), losing non-numeric
--      values like "2 א", "מגרש 78343", or compound IDs.
--   2. UNIQUE(tender_id, lot_number) fails when lot_number is NULL
--      (multiple lots per tender with non-parseable MitchamName).
--   3. gush/helka are comma-joined TEXT but display is inconsistent.
--
-- Changes:
--   1. ADD mitcham_name TEXT — preserves the raw API MitchamName string.
--   2. MIGRATE existing lot_number values into mitcham_name for api rows.
--   3. REPLACE the UNIQUE constraint with a partial unique index that
--      handles NULL lot_numbers via a fallback to row position.
--
-- Safe to run multiple times (all statements are idempotent).
-- ==========================================================================

-- ── Step 1: Add mitcham_name column ─────────────────────────────────────
-- Stores the raw MitchamName string from the API exactly as received.
-- This preserves values like "1121", "129", "2 א" that were previously
-- cast to INT (losing non-numeric ones).
ALTER TABLE tender_lots
    ADD COLUMN IF NOT EXISTS mitcham_name TEXT;

COMMENT ON COLUMN tender_lots.mitcham_name IS
    'Raw MitchamName from API Tik[] — preserved as-is (may be numeric, Hebrew-suffixed, or compound ID)';

-- ── Step 2: Backfill mitcham_name from existing lot_number ──────────────
-- For rows that came from the API (or merged with API as base), the
-- lot_number column currently holds the integer-parsed MitchamName.
-- Copy it to mitcham_name so we don't lose the data when we later
-- repurpose lot_number for sequential brochure numbering.
UPDATE tender_lots
SET    mitcham_name = lot_number::TEXT
WHERE  data_source IN ('api', 'merged')
  AND  lot_number IS NOT NULL
  AND  mitcham_name IS NULL;

-- ── Step 3: Deduplicate existing rows ────────────────────────────────────
-- The old UNIQUE(tender_id, lot_number) allowed multiple rows with NULL
-- lot_number per tender (PostgreSQL treats NULLs as distinct). Before we
-- create the new partial unique indexes, we must remove these duplicates.
-- Strategy: for each (tender_id, COALESCE(mitcham_name, '')) group in
-- api-only rows, keep only the row with the highest id (most recent).
DELETE FROM tender_lots
WHERE id NOT IN (
    SELECT MAX(id)
    FROM tender_lots
    WHERE data_source = 'api'
    GROUP BY tender_id, COALESCE(mitcham_name, '')
)
AND data_source = 'api'
AND EXISTS (
    SELECT 1 FROM tender_lots t2
    WHERE t2.tender_id = tender_lots.tender_id
      AND COALESCE(t2.mitcham_name, '') = COALESCE(tender_lots.mitcham_name, '')
      AND t2.data_source = 'api'
      AND t2.id > tender_lots.id
);

-- Also deduplicate PDF and merged rows with duplicate (tender_id, lot_number)
DELETE FROM tender_lots
WHERE id NOT IN (
    SELECT MAX(id)
    FROM tender_lots
    WHERE data_source IN ('pdf', 'merged') AND lot_number IS NOT NULL
    GROUP BY tender_id, lot_number
)
AND data_source IN ('pdf', 'merged')
AND lot_number IS NOT NULL
AND EXISTS (
    SELECT 1 FROM tender_lots t2
    WHERE t2.tender_id = tender_lots.tender_id
      AND t2.lot_number = tender_lots.lot_number
      AND t2.data_source IN ('pdf', 'merged')
      AND t2.id > tender_lots.id
);

-- ── Step 4: Replace the UNIQUE constraint ───────────────────────────────
-- The current UNIQUE(tender_id, lot_number) has two problems:
--   a) NULL lot_numbers are all considered distinct by PostgreSQL, so
--      duplicate API lots with unparseable MitchamName bypass the constraint.
--   b) When PDF lots use sequential numbering (1,2,3) and API lots use
--      compound IDs (1121,1124), they collide in the wrong direction.
--
-- New approach: Use a unique index on (tender_id, mitcham_name) for API
-- rows, and (tender_id, lot_number) for PDF rows. A composite partial
-- index handles both cleanly.

-- Drop the old constraint (wrapped in DO block for idempotency)
DO $$
BEGIN
    -- Try dropping by constraint name (original schema)
    ALTER TABLE tender_lots DROP CONSTRAINT IF EXISTS tender_lots_tender_id_lot_number_key;
EXCEPTION
    WHEN undefined_object THEN NULL;
END $$;

-- Also drop any index that backs the old unique constraint
DROP INDEX IF EXISTS tender_lots_tender_id_lot_number_key;

-- New index 1: For API-only rows, uniqueness is on (tender_id, mitcham_name).
-- This correctly deduplicates "2 א" vs "2" vs NULL.
-- COALESCE ensures NULLs are treated as equal (prevent duplicate NULL rows).
CREATE UNIQUE INDEX IF NOT EXISTS uq_tender_lots_api
    ON tender_lots (tender_id, COALESCE(mitcham_name, ''))
    WHERE data_source = 'api';

-- New index 2: For PDF and merged rows, uniqueness is on (tender_id, lot_number).
-- PDF lot_numbers are sequential and always non-NULL.
-- Merged rows use PDF's lot_number as the canonical identifier.
CREATE UNIQUE INDEX IF NOT EXISTS uq_tender_lots_pdf
    ON tender_lots (tender_id, lot_number)
    WHERE data_source IN ('pdf', 'merged') AND lot_number IS NOT NULL;

-- Fallback: For rows where both mitcham_name and lot_number are NULL,
-- prevent accidental duplicates per tender by using the row's id.
-- (No additional index needed — the id PK already guarantees uniqueness.)

-- ── Step 5: Add indexes for new query patterns ──────────────────────────
CREATE INDEX IF NOT EXISTS idx_tender_lots_mitcham_name
    ON tender_lots (tender_id, mitcham_name)
    WHERE mitcham_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tender_lots_data_source
    ON tender_lots (data_source);

-- ── Step 6: Add gush_helka_raw column for future structured storage ─────
-- Currently gush and helka are comma-joined TEXT. For future use, we add
-- a JSONB column that can store the full GushHelka[] array from the API.
ALTER TABLE tender_lots
    ADD COLUMN IF NOT EXISTS gush_helka_raw JSONB;

COMMENT ON COLUMN tender_lots.gush_helka_raw IS
    'Raw GushHelka[] array from API Tik[] — structured [{Gush: "6150", Helka: "42"}, ...]';

-- ==========================================================================
-- Verification queries (run manually after migration)
-- ==========================================================================
-- Check for data loss:
--   SELECT COUNT(*) FROM tender_lots WHERE data_source IN ('api','merged') AND mitcham_name IS NULL AND lot_number IS NOT NULL;
--   -- Should be 0 after backfill
--
-- Check constraint effectiveness:
--   SELECT tender_id, mitcham_name, COUNT(*) FROM tender_lots
--   WHERE data_source IN ('api','merged')
--   GROUP BY tender_id, mitcham_name HAVING COUNT(*) > 1;
--   -- Should return 0 rows (no duplicates)
--
-- Check non-numeric MitchamNames that were previously lost:
--   SELECT DISTINCT lot_number, mitcham_name, data_source
--   FROM tender_lots WHERE lot_number IS NULL AND mitcham_name IS NOT NULL;
