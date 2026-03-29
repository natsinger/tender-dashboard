-- Migration: tender_outcomes table
-- Tracks post-deadline bidding outcomes for watchlisted tenders.
-- Manual input: did we bid, our offer, position, notes.
-- Run in Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS tender_outcomes (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tender_id     INT NOT NULL UNIQUE,
    did_bid       BOOLEAN DEFAULT FALSE,
    our_offer     NUMERIC,
    our_position  INT,
    outcome_notes TEXT,
    updated_by    TEXT,
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tender_outcomes_tender ON tender_outcomes(tender_id);

-- RLS: allow all for anon (matches existing policy pattern)
ALTER TABLE tender_outcomes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for anon" ON tender_outcomes FOR ALL USING (true);
