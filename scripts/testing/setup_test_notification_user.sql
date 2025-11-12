-- SQL script to set up notification preferences for test user
-- User ID: HKjKayLYGphLDv5pNVncw2i1g1g1

-- First, check if the user exists
SELECT id, email, display_name FROM users WHERE id = 'HKjKayLYGphLDv5pNVncw2i1g1g1';

-- Check if notification preferences already exist
SELECT * FROM notification_preferences WHERE user_id = 'HKjKayLYGphLDv5pNVncw2i1g1g1';

-- Check FCM tokens for the user
SELECT id, device_type, fcm_token, is_active, created_at 
FROM user_fcm_tokens 
WHERE user_id = 'HKjKayLYGphLDv5pNVncw2i1g1g1';

-- Create or update notification preferences (all enabled for testing)
INSERT INTO notification_preferences (
    id,
    user_id,
    meal_reminders_enabled,
    water_reminders_enabled,
    sleep_reminders_enabled,
    progress_notifications_enabled,
    reengagement_notifications_enabled,
    breakfast_time_minutes,
    lunch_time_minutes,
    dinner_time_minutes,
    water_reminder_interval_hours,
    sleep_reminder_time_minutes,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid()::text,
    'HKjKayLYGphLDv5pNVncw2i1g1g1',
    true,  -- meal_reminders_enabled
    true,  -- water_reminders_enabled
    true,  -- sleep_reminders_enabled
    true,  -- progress_notifications_enabled
    true,  -- reengagement_notifications_enabled
    480,   -- breakfast_time_minutes (8:00 AM)
    720,   -- lunch_time_minutes (12:00 PM)
    1080,  -- dinner_time_minutes (6:00 PM)
    2,     -- water_reminder_interval_hours
    1320,  -- sleep_reminder_time_minutes (10:00 PM)
    NOW(),
    NOW()
)
ON CONFLICT (user_id) 
DO UPDATE SET
    meal_reminders_enabled = true,
    water_reminders_enabled = true,
    sleep_reminders_enabled = true,
    progress_notifications_enabled = true,
    reengagement_notifications_enabled = true,
    updated_at = NOW();

-- Verify the update
SELECT * FROM notification_preferences WHERE user_id = 'HKjKayLYGphLDv5pNVncw2i1g1g1';

