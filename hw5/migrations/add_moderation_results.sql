-- Create moderation_results table
-- Note: item_id references items.item_id (not items.id) since we use item_id in the application
CREATE TABLE IF NOT EXISTS moderation_results (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    is_violation BOOLEAN,
    probability FLOAT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_moderation_results_item_id ON moderation_results(item_id);
CREATE INDEX IF NOT EXISTS idx_moderation_results_status ON moderation_results(status);
CREATE INDEX IF NOT EXISTS idx_moderation_results_created_at ON moderation_results(created_at);

