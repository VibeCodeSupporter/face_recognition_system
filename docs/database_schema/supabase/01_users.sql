-- Requires 00_setup.sql. Creates only the users table.
-- If the table already exists, this script stops; use ALTER TABLE to change it.
BEGIN;

CREATE TABLE public.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_code varchar(50) NOT NULL UNIQUE,
    full_name varchar(150) NOT NULL,
    email varchar(150),
    phone varchar(20),
    department varchar(100),
    role varchar(50),
    status varchar(20) NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT users_code_not_blank CHECK (btrim(user_code) <> ''),
    CONSTRAINT users_name_not_blank CHECK (btrim(full_name) <> ''),
    CONSTRAINT users_status_valid CHECK (status IN ('active', 'inactive'))
);

COMMENT ON COLUMN public.users.role IS 'Job title, not a portal authorization role.';

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION public.faceaccess_set_updated_at();

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.users FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.users TO service_role;

COMMIT;
