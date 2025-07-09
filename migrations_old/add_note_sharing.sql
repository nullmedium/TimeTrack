-- Add note_share table for public note sharing functionality
CREATE TABLE IF NOT EXISTS note_share (
    id SERIAL PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
    token VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP,
    password_hash VARCHAR(255),
    view_count INTEGER DEFAULT 0,
    max_views INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER NOT NULL REFERENCES "user"(id),
    last_accessed_at TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_note_share_token ON note_share(token);
CREATE INDEX IF NOT EXISTS idx_note_share_note_id ON note_share(note_id);
CREATE INDEX IF NOT EXISTS idx_note_share_created_by ON note_share(created_by_id);

-- Add comment
COMMENT ON TABLE note_share IS 'Public sharing links for notes with optional password protection and view limits';