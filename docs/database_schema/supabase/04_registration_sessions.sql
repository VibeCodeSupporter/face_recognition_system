-- Requires 01_users.sql and 02_devices.sql.
BEGIN;

CREATE TABLE public.registration_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    device_id uuid NOT NULL REFERENCES public.devices(id) ON DELETE RESTRICT,
    status varchar(20) NOT NULL DEFAULT 'pending',
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CONSTRAINT registration_sessions_status_valid CHECK (
        status IN ('pending', 'completed', 'cancelled', 'expired', 'failed')
    ),
    CONSTRAINT registration_sessions_expiry_valid CHECK (expires_at > created_at),
    CONSTRAINT registration_sessions_completion_valid CHECK (
        (status = 'completed') = (completed_at IS NOT NULL)
    )
);

CREATE INDEX registration_sessions_user_created_idx
    ON public.registration_sessions (user_id, created_at DESC);
CREATE INDEX registration_sessions_device_pending_idx
    ON public.registration_sessions (device_id, expires_at) WHERE status = 'pending';

ALTER TABLE public.registration_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.registration_sessions FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.registration_sessions TO service_role;

COMMIT;
