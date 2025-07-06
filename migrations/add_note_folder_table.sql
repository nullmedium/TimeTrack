-- Create note_folder table for tracking folders independently of notes
CREATE TABLE IF NOT EXISTS note_folder (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    path VARCHAR(500) NOT NULL,
    parent_path VARCHAR(500),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER NOT NULL REFERENCES "user"(id),
    company_id INTEGER NOT NULL REFERENCES company(id),
    CONSTRAINT uq_folder_path_company UNIQUE (path, company_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_note_folder_company ON note_folder(company_id);
CREATE INDEX IF NOT EXISTS idx_note_folder_parent_path ON note_folder(parent_path);
CREATE INDEX IF NOT EXISTS idx_note_folder_created_by ON note_folder(created_by_id);