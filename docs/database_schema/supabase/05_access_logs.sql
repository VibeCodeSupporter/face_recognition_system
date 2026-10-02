-- Requires 01_users.sql and 02_devices.sql.
BEGIN;

CREATE TABLE public.access_logs (
    id uuid PRIMARY KEY,
    user_id uuid REFERENCES public.users(id) ON DELETE RESTRICT,
    device_id uuid NOT NULL REFERENCES public.devices(id) ON DELETE RESTRICT,
    result varchar(20) NOT NULL,
    confidence real,
    access_time timestamptz NOT NULL,
    synced_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT access_logs_result_valid CHECK (result IN ('granted', 'denied')),
    CONSTRAINT access_logs_confidence_valid CHECK (confidence BETWEEN 0 AND 100)
);

COMMENT ON COLUMN public.access_logs.id IS 'Generate UUID once on edge; reuse it on every upload retry. No cloud default on purpose.';
COMMENT ON COLUMN public.access_logs.user_id IS 'NULL means an unrecognized person.';

CREATE INDEX access_logs_device_time_idx ON public.access_logs (device_id, access_time DESC);
CREATE INDEX access_logs_user_time_idx ON public.access_logs (user_id, access_time DESC);

ALTER TABLE public.access_logs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.access_logs FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.access_logs TO service_role;

COMMIT;
