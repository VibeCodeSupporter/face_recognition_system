-- OPTIONAL: creates a test user, device and enrollment session.
-- Run after 00..05. Test codes and UUIDs are intentionally fixed for the examples.
BEGIN;

INSERT INTO public.users (id, user_code, full_name, email, department, role)
VALUES (
    '00000000-0000-4000-8000-000000000001', 'TEST001', 'Test User',
    'test@example.com', 'IT', 'Staff'
)
ON CONFLICT (user_code) DO NOTHING;

INSERT INTO public.devices (id, device_code, name, location, api_key_hash)
VALUES (
    '10000000-0000-4000-8000-000000000001', 'TESTDEV001', 'Test Door', 'Test Room',
    encode(sha256(convert_to('local-demo-only-token', 'UTF8')), 'hex')
)
ON CONFLICT (device_code) DO NOTHING;

INSERT INTO public.registration_sessions (id, user_id, device_id)
SELECT '20000000-0000-4000-8000-000000000001', u.id, d.id
FROM public.users u CROSS JOIN public.devices d
WHERE u.user_code = 'TEST001' AND d.device_code = 'TESTDEV001'
ON CONFLICT (id) DO NOTHING;

COMMIT;

SELECT id, user_code, full_name FROM public.users WHERE user_code = 'TEST001';
SELECT id, device_code, name FROM public.devices WHERE device_code = 'TESTDEV001';
