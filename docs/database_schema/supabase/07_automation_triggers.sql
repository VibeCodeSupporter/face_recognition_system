-- ==============================================================================
-- 07_automation_triggers.sql
-- BỔ SUNG DATABASE TRIGGERS CHO FACE ACCESS SYSTEM
-- 1. Ép giới hạn tối đa 10 phiên đang chờ cho 1 thiết bị
-- 2. Bắn tín hiệu pg_notify khi có phiên mới
-- 3. Tự động cập nhật thiết bị Online khi có Access Log
-- 4. Tự động gán completed_at và thông báo khi phiên hoàn tất
-- ==============================================================================

BEGIN;

-- 1. TRIGGER: KIỂM TRA RÀNG BUỘC KHI TẠO PHIÊN ĐĂNG KÝ
-- - Chặn tạo phiên nếu người dùng đã có Face Embedding
-- - Chặn tạo phiên trùng lặp nếu người dùng đang có phiên pending
-- - Ép giới hạn tối đa 10 phiên đang chờ cho 1 thiết bị
CREATE OR REPLACE FUNCTION public.check_registration_session_constraints()
RETURNS trigger AS $$
DECLARE
    pending_count integer;
    has_face boolean;
BEGIN
    -- 1. Chặn nếu người dùng đã có face embedding trong hệ thống
    SELECT EXISTS (
        SELECT 1 FROM public.face_embeddings WHERE user_id = NEW.user_id
    ) INTO has_face;

    IF has_face THEN
        RAISE EXCEPTION 'USER_ALREADY_REGISTERED: Nguoi dung % da co du lieu khuon mat trong he thong.', NEW.user_id
            USING ERRCODE = 'check_violation';
    END IF;

    -- 2. Chặn nếu người dùng đang có một phiên pending khác
    IF EXISTS (
        SELECT 1 FROM public.registration_sessions
        WHERE user_id = NEW.user_id AND status = 'pending' AND id != NEW.id
    ) THEN
        RAISE EXCEPTION 'USER_HAS_PENDING_SESSION: Nguoi dung % hien da co phien dang ky dang cho.', NEW.user_id
            USING ERRCODE = 'check_violation';
    END IF;

    -- 3. Kiểm tra giới hạn 10 phiên trên thiết bị
    SELECT count(*) INTO pending_count
    FROM public.registration_sessions
    WHERE device_id = NEW.device_id AND status = 'pending';

    IF pending_count >= 10 THEN
        RAISE EXCEPTION 'DEVICE_QUEUE_FULL: Thiet bi % da co 10 phien cho xu ly.', NEW.device_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_max_pending_sessions ON public.registration_sessions;
DROP TRIGGER IF EXISTS trg_check_registration_session_constraints ON public.registration_sessions;
CREATE TRIGGER trg_check_registration_session_constraints
BEFORE INSERT ON public.registration_sessions
FOR EACH ROW EXECUTE FUNCTION public.check_registration_session_constraints();


-- 2. TRIGGER: PHÁT SỰ KIỆN KHI CÓ PHIÊN MỚI ĐƯỢC TẠO
CREATE OR REPLACE FUNCTION public.notify_device_new_session()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify(
        'device_channel_' || NEW.device_id::text,
        json_build_object(
            'event', 'NEW_REGISTRATION_SESSION',
            'session_id', NEW.id,
            'user_id', NEW.user_id,
            'created_at', NEW.created_at,
            'expires_at', NEW.expires_at
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_device_new_session ON public.registration_sessions;
CREATE TRIGGER trg_notify_device_new_session
AFTER INSERT ON public.registration_sessions
FOR EACH ROW
WHEN (NEW.status = 'pending')
EXECUTE FUNCTION public.notify_device_new_session();


-- 3. TRIGGER: TỰ ĐỘNG CẬP NHẬT THIẾT BỊ ONLINE KHI CÓ LOG MỚI
CREATE OR REPLACE FUNCTION public.update_device_on_access_log()
RETURNS trigger AS $$
BEGIN
    UPDATE public.devices
    SET 
        status = 'online',
        last_seen_at = GREATEST(COALESCE(last_seen_at, NEW.access_time), NEW.access_time)
    WHERE id = NEW.device_id;

    PERFORM pg_notify(
        'portal_access_logs',
        json_build_object(
            'event', 'NEW_ACCESS_LOG',
            'log_id', NEW.id,
            'user_id', NEW.user_id,
            'device_id', NEW.device_id,
            'result', NEW.result,
            'confidence', NEW.confidence,
            'access_time', NEW.access_time
        )::text
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_device_on_access_log ON public.access_logs;
CREATE TRIGGER trg_update_device_on_access_log
AFTER INSERT ON public.access_logs
FOR EACH ROW EXECUTE FUNCTION public.update_device_on_access_log();


-- 4. TRIGGER: TỰ ĐỘNG GÁN COMPLETED_AT VÀ BÁO CHO FRONTEND KHI PHIÊN XONG
CREATE OR REPLACE FUNCTION public.handle_session_status_update()
RETURNS trigger AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status = 'pending' THEN
        IF NEW.completed_at IS NULL THEN
            NEW.completed_at = clock_timestamp();
        END IF;
    END IF;

    PERFORM pg_notify(
        'portal_session_events',
        json_build_object(
            'event', 'SESSION_COMPLETED',
            'session_id', NEW.id,
            'status', NEW.status,
            'completed_at', NEW.completed_at
        )::text
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_handle_session_status_update ON public.registration_sessions;
CREATE TRIGGER trg_handle_session_status_update
BEFORE UPDATE OF status ON public.registration_sessions
FOR EACH ROW EXECUTE FUNCTION public.handle_session_status_update();

COMMIT;

