-- Read-only. Run after 00..05 to inspect the created tables.
SELECT tablename, rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('users', 'devices', 'face_embeddings', 'registration_sessions', 'access_logs')
ORDER BY tablename;

SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('users', 'devices', 'face_embeddings', 'registration_sessions', 'access_logs')
ORDER BY table_name, ordinal_position;

SELECT conrelid::regclass AS table_name, conname AS constraint_name,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid IN (
    'public.users'::regclass, 'public.devices'::regclass,
    'public.face_embeddings'::regclass, 'public.registration_sessions'::regclass,
    'public.access_logs'::regclass
)
ORDER BY conrelid::regclass::text, conname;
