-- ==========================================================================
-- lot_count column migration
-- Run this in Supabase SQL Editor ONCE to add the lot_count column.
-- lot_count stores the number of Tik[] entries from the API detail response
-- (i.e. how many lots/מתחמים are in this tender).
-- ==========================================================================

ALTER TABLE tenders ADD COLUMN IF NOT EXISTS lot_count INTEGER;

CREATE INDEX IF NOT EXISTS idx_tenders_lot_count ON tenders(lot_count);
