-- Add is_closed column to items table
ALTER TABLE items ADD COLUMN IF NOT EXISTS is_closed BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_items_is_closed ON items(is_closed);
