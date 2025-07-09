-- Remove all email preference columns from user_preferences table
-- These columns were not being used and are being removed to clean up the schema

ALTER TABLE user_preferences 
    DROP COLUMN IF EXISTS email_daily_summary,
    DROP COLUMN IF EXISTS email_notifications,
    DROP COLUMN IF EXISTS email_weekly_summary;