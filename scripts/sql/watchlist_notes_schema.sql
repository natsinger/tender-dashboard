-- Migration: add per-tender personal notes column to user_watchlist.
-- Run once against the Supabase PostgreSQL database.
-- Safe to re-run: IF NOT EXISTS prevents duplicate-column errors.

ALTER TABLE user_watchlist ADD COLUMN IF NOT EXISTS notes text;
