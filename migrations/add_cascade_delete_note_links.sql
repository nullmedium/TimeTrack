-- Migration to add CASCADE delete to note_link foreign keys
-- This ensures that when a note is deleted, all links to/from it are also deleted

-- For PostgreSQL
-- Drop existing foreign key constraints
ALTER TABLE note_link DROP CONSTRAINT IF EXISTS note_link_source_note_id_fkey;
ALTER TABLE note_link DROP CONSTRAINT IF EXISTS note_link_target_note_id_fkey;

-- Add new foreign key constraints with CASCADE
ALTER TABLE note_link 
    ADD CONSTRAINT note_link_source_note_id_fkey 
    FOREIGN KEY (source_note_id) 
    REFERENCES note(id) 
    ON DELETE CASCADE;

ALTER TABLE note_link 
    ADD CONSTRAINT note_link_target_note_id_fkey 
    FOREIGN KEY (target_note_id) 
    REFERENCES note(id) 
    ON DELETE CASCADE;