-- OPTIONAL: update existing data; run examples/02 first.
BEGIN;

UPDATE public.users
SET department = 'Engineering', phone = '0900000000'
WHERE user_code = 'TEST001';

-- JSON attributes can be added/updated without an ALTER TABLE.
-- Merge with || so existing keys (doorDuration, liveness) are retained.
UPDATE public.devices
SET settings = settings || '{"threshold":85,"displayMessage":"Welcome"}'::jsonb
WHERE device_code = 'TESTDEV001';

COMMIT;
