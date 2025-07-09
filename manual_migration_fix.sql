-- Manual SQL commands to fix migration revision error
-- Run these commands in your PostgreSQL database if the scripts fail

-- 1. Check current revision (optional)
SELECT * FROM alembic_version;

-- 2. Clear the incorrect revision
DELETE FROM alembic_version;

-- 3. If you want to set a specific revision manually:
-- First, check what revisions you have:
-- ls migrations/versions/*.py
-- Then insert the revision ID from one of those files:
-- INSERT INTO alembic_version (version_num) VALUES ('your_revision_id_here');

-- 4. Or just leave it empty and let Flask-Migrate handle it
-- The next 'flask db stamp head' will set the correct revision