-- Requires 00_setup.sql and 01_users.sql.
-- This table stores the face vector after enrollment.
BEGIN;

CREATE TABLE public.face_embeddings (
    user_id uuid PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    image_url text,
    model_name varchar(100) NOT NULL,
    model_version varchar(30) NOT NULL,
    dimension integer NOT NULL,
    embedding_data jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT face_embeddings_model_not_blank CHECK (btrim(model_name) <> ''),
    CONSTRAINT face_embeddings_version_not_blank CHECK (btrim(model_version) <> ''),
    CONSTRAINT face_embeddings_dimension_positive CHECK (dimension > 0),
    CONSTRAINT face_embeddings_vector_valid CHECK (
        public.faceaccess_valid_embedding(embedding_data, dimension)
    )
);

COMMENT ON COLUMN public.face_embeddings.embedding_data IS 'Numeric JSON array, exactly dimension elements. One current template per user.';
COMMENT ON COLUMN public.face_embeddings.image_url IS 'Optional private image storage object path.';

CREATE TRIGGER face_embeddings_set_updated_at
BEFORE UPDATE ON public.face_embeddings
FOR EACH ROW EXECUTE FUNCTION public.faceaccess_set_updated_at();

ALTER TABLE public.face_embeddings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.face_embeddings FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.face_embeddings TO service_role;

COMMIT;
