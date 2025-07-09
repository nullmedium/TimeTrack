-- Remove unused columns from user_preferences table
-- These columns were defined in the model but never used in the application

ALTER TABLE user_preferences 
    DROP COLUMN IF EXISTS email_daily_summary,
    DROP COLUMN IF EXISTS email_notifications,
    DROP COLUMN IF EXISTS email_weekly_summary,
    DROP COLUMN IF EXISTS default_project_id;