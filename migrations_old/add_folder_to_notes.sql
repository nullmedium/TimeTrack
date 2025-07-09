-- Add folder column to notes table
ALTER TABLE note ADD COLUMN IF NOT EXISTS folder VARCHAR(100);

-- Create an index on folder for faster filtering
CREATE INDEX IF NOT EXISTS idx_note_folder ON note(folder) WHERE folder IS NOT NULL;