-- Run first in the Supabase SQL Editor.
-- A Supabase project already has a PostgreSQL database; no CREATE DATABASE is needed.
BEGIN;

CREATE OR REPLACE FUNCTION public.faceaccess_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.faceaccess_valid_embedding(
    embedding jsonb,
    dimensions integer
)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
STRICT
SET search_path = ''
AS $$
BEGIN
    IF dimensions <= 0 OR jsonb_typeof(embedding) <> 'array' THEN
        RETURN false;
    END IF;
    IF jsonb_array_length(embedding) <> dimensions THEN
        RETURN false;
    END IF;
    RETURN NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(embedding) AS element(value)
        WHERE jsonb_typeof(element.value) <> 'number'
    );
END;
$$;

COMMIT;

SELECT current_database() AS database_name, 'Setup ready' AS result;
