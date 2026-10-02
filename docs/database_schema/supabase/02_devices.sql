-- Creates only the devices table. No other table is required.
BEGIN;

CREATE TABLE public.devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_code varchar(50) NOT NULL UNIQUE,
    name varchar(100) NOT NULL,
    location varchar(200),
    api_key_hash varchar(128) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'offline',
    settings jsonb NOT NULL DEFAULT '{"threshold":80,"doorDuration":3,"liveness":true}'::jsonb,
    last_seen_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT devices_code_not_blank CHECK (btrim(device_code) <> ''),
    CONSTRAINT devices_name_not_blank CHECK (btrim(name) <> ''),
    CONSTRAINT devices_api_key_hash_not_blank CHECK (btrim(api_key_hash) <> ''),
    CONSTRAINT devices_status_valid CHECK (status IN ('online', 'offline', 'warning')),
    CONSTRAINT devices_settings_object CHECK (jsonb_typeof(settings) = 'object')
);

COMMENT ON COLUMN public.devices.api_key_hash IS 'Device token hash. Generate and validate the token in the backend.';

ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.devices FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.devices TO service_role;

COMMIT;
