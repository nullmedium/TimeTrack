-- SQLite migration for cascade delete on note_link
-- SQLite doesn't support ALTER TABLE for foreign keys, so we need to recreate the table

-- Create new table with CASCADE delete
CREATE TABLE note_link_new (
    id INTEGER PRIMARY KEY,
    source_note_id INTEGER NOT NULL,
    target_note_id INTEGER NOT NULL,
    link_type VARCHAR(50) DEFAULT 'related',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER NOT NULL,
    FOREIGN KEY (source_note_id) REFERENCES note(id) ON DELETE CASCADE,
    FOREIGN KEY (target_note_id) REFERENCES note(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES user(id),
    UNIQUE(source_note_id, target_note_id)
);

-- Copy data from old table
INSERT INTO note_link_new SELECT * FROM note_link;

-- Drop old table
DROP TABLE note_link;

-- Rename new table
ALTER TABLE note_link_new RENAME TO note_link;