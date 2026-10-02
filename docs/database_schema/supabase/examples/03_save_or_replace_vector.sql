-- OPTIONAL: direct SQL test of INSERT/UPSERT; run examples/02 first.
-- This 4-number vector is DUMMY DATA, not a real face embedding.
-- For real enrollment, use the actual model/version/dimension/vector from your AI.
-- The backend must validate the enrollment session and target device separately.
BEGIN;

DO $$
DECLARE
    target_user_id uuid;
BEGIN
    SELECT id INTO STRICT target_user_id
    FROM public.users WHERE user_code = 'TEST001' AND status = 'active';

    INSERT INTO public.face_embeddings (
        user_id, image_url, model_name, model_version, dimension, embedding_data
    )
    VALUES (target_user_id, NULL, 'demo-model', 'demo-v1', 4, '[0.12, -0.34, 0.56, 0.78]'::jsonb)
    ON CONFLICT (user_id) DO UPDATE SET
        image_url = EXCLUDED.image_url,
        model_name = EXCLUDED.model_name,
        model_version = EXCLUDED.model_version,
        dimension = EXCLUDED.dimension,
        embedding_data = EXCLUDED.embedding_data;
END;
$$;

COMMIT;

SELECT user_id, model_name, dimension, embedding_data, updated_at
FROM public.face_embeddings
WHERE user_id = (SELECT id FROM public.users WHERE user_code = 'TEST001');
