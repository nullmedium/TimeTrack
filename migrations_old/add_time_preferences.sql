-- Add time formatting and rounding preferences to user_preferences table
-- These columns support user-specific time display and rounding settings

-- Add time formatting preference (24h vs 12h)
ALTER TABLE user_preferences 
    ADD COLUMN IF NOT EXISTS time_format_24h BOOLEAN DEFAULT TRUE;

-- Add time rounding preference (0, 5, 10, 15, 30, 60 minutes)
ALTER TABLE user_preferences 
    ADD COLUMN IF NOT EXISTS time_rounding_minutes INTEGER DEFAULT 0;

-- Add rounding direction preference (false=round down, true=round to nearest)
ALTER TABLE user_preferences 
    ADD COLUMN IF NOT EXISTS round_to_nearest BOOLEAN DEFAULT FALSE;

-- Update existing date_format column default if needed
-- (The column should already exist, but let's ensure the default is correct)
UPDATE user_preferences 
SET date_format = 'ISO' 
WHERE date_format = 'YYYY-MM-DD' OR date_format IS NULL;