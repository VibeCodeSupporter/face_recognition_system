-- ====================================================================
-- Face Recognition Access Control System - Cloud Database Schema
-- Compatible with PostgreSQL 15+ (Supports pgvector extension if enabled)
-- ====================================================================

-- 1. Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- (Optional: Uncomment if using pgvector for central vector similarity search)
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. USERS TABLE: Quản lý thông tin định danh nhân sự/người dùng
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_code VARCHAR(50) UNIQUE NOT NULL,      -- Mã nhân viên / mã định danh
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE,
    phone VARCHAR(20),
    department VARCHAR(100),                    -- Phòng ban
    role VARCHAR(50) DEFAULT 'Staff',           -- Vai trò (Admin, Manager, Staff, Guest)
    status VARCHAR(20) DEFAULT 'active',        -- 'active', 'inactive', 'suspended'
    face_status VARCHAR(20) DEFAULT 'pending',  -- 'enrolled', 'pending', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. DEVICES TABLE: Quản lý các thiết bị kiểm soát cửa tại biên (Edge Device)
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_code VARCHAR(50) UNIQUE NOT NULL,    -- DEV001, DEV002...
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200) NOT NULL,             -- Sảnh A, Cổng kho C...
    ip_address VARCHAR(45),
    mac_address VARCHAR(17),
    api_key VARCHAR(128) NOT NULL,              -- Token xác thực riêng cho mỗi thiết bị
    firmware_version VARCHAR(30) DEFAULT 'v1.0.0',
    status VARCHAR(20) DEFAULT 'online',        -- 'online', 'offline', 'warning'
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_heartbeat_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. FACES TABLE: Lưu trữ thông tin ảnh khuôn mặt gốc và trạng thái
CREATE TABLE IF NOT EXISTS faces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,            -- Đường dẫn ảnh lưu trữ (S3 / Local storage)
    quality_score FLOAT DEFAULT 0.0,            -- Điểm chất lượng ảnh (0 - 100)
    is_primary BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    enrolled_device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. FACE EMBEDDINGS TABLE: Lưu trữ vector đặc trưng khuôn mặt (512 chiều)
CREATE TABLE IF NOT EXISTS face_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    face_id UUID NOT NULL REFERENCES faces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model_name VARCHAR(100) DEFAULT 'ArcFace-ResNet50', -- Model AI trích xuất vector
    model_version VARCHAR(20) DEFAULT '1.0',
    dimension INT DEFAULT 512,
    -- Nếu có pgvector: embedding VECTOR(512),
    embedding_data JSONB NOT NULL,              -- Mảng float[512] lưu dưới dạng JSONB
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. REGISTRATION SESSIONS TABLE: Quản lý phiên đăng ký khuôn mặt được tạo từ Web Portal
CREATE TABLE IF NOT EXISTS registration_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_code VARCHAR(64) UNIQUE NOT NULL,   -- Mã định danh phiên (UUID hoặc Token)
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'pending',       -- 'pending', 'in_progress', 'completed', 'expired', 'failed'
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_by VARCHAR(100) DEFAULT 'System Admin',
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. ACCESS LOGS TABLE: Tiếp nhận nhật ký ra vào được đồng bộ từ Device
CREATE TABLE IF NOT EXISTS access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_uuid VARCHAR(64) UNIQUE NOT NULL,       -- UUID sinh từ Device để chống trùng lặp khi sync lại
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    unrecognized_label VARCHAR(100),            -- Ví dụ: 'Người lạ #042' nếu không nhận diện được
    result VARCHAR(20) NOT NULL,                -- 'granted' hoặc 'denied'
    confidence FLOAT,                           -- Độ tin cậy nhận diện (%)
    snapshot_url VARCHAR(500),                  -- Ảnh chụp thời điểm quét mặt
    access_time TIMESTAMP WITH TIME ZONE NOT NULL, -- Thời điểm thực tế tại Device
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- Thời điểm Cloud nhận được
);

-- 8. SYSTEM CONFIGURATIONS TABLE: Cấu hình hệ thống Cloud & Device
CREATE TABLE IF NOT EXISTS system_configs (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(500) NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- SEED DATA (Dữ liệu mẫu ban đầu đồng bộ với Web Portal)
-- ====================================================================

-- Users
INSERT INTO users (id, user_code, full_name, email, department, role, status, face_status) VALUES
('00000000-0000-0000-0000-000000000001', 'USR001', 'Nguyễn Văn An', 'an.nguyen@company.vn', 'Kỹ thuật', 'Engineer', 'active', 'enrolled'),
('00000000-0000-0000-0000-000000000002', 'USR002', 'Trần Thị Bình', 'binh.tran@company.vn', 'Nhân sự', 'HR Manager', 'active', 'enrolled'),
('00000000-0000-0000-0000-000000000003', 'USR003', 'Lê Hoàng Cường', 'cuong.le@company.vn', 'IT', 'Admin', 'active', 'enrolled'),
('00000000-0000-0000-0000-000000000004', 'USR004', 'Phạm Thị Dung', 'dung.pham@company.vn', 'Tài chính', 'Accountant', 'inactive', 'pending'),
('00000000-0000-0000-0000-000000000005', 'USR005', 'Hoàng Minh Em', 'em.hoang@company.vn', 'Kinh doanh', 'Sales', 'active', 'enrolled'),
('00000000-0000-0000-0000-000000000006', 'USR006', 'Ngô Thị Phương', 'phuong.ngo@company.vn', 'Marketing', 'Designer', 'active', 'failed'),
('00000000-0000-0000-0000-000000000007', 'USR007', 'Vũ Đình Quân', 'quan.vu@company.vn', 'Kỹ thuật', 'Engineer', 'active', 'enrolled')
ON CONFLICT (user_code) DO NOTHING;

-- Devices
INSERT INTO devices (id, device_code, name, location, ip_address, api_key, firmware_version, status, last_sync_at) VALUES
('10000000-0000-0000-0000-000000000001', 'DEV001', 'Cổng Chính A', 'Tầng 1 - Sảnh chính', '192.168.1.101', 'key_secret_gate_a_2026', 'v2.4.1', 'online', CURRENT_TIMESTAMP),
('10000000-0000-0000-0000-000000000002', 'DEV002', 'Cổng Phụ B', 'Tầng 1 - Cửa hông', '192.168.1.102', 'key_secret_gate_b_2026', 'v2.4.1', 'online', CURRENT_TIMESTAMP),
('10000000-0000-0000-0000-000000000003', 'DEV003', 'Cổng Kho C', 'Tầng B1 - Kho hàng', '192.168.1.103', 'key_secret_storage_c_2026', 'v2.3.8', 'warning', CURRENT_TIMESTAMP - INTERVAL '2 hours'),
('10000000-0000-0000-0000-000000000004', 'DEV004', 'Cổng Server Room', 'Tầng 3 - Phòng máy chủ', '192.168.1.104', 'key_secret_server_rm_2026', 'v2.4.1', 'online', CURRENT_TIMESTAMP)
ON CONFLICT (device_code) DO NOTHING;

-- System Configs
INSERT INTO system_configs (key, value, description, category) VALUES
('FACE_RECOG_THRESHOLD', '80', 'Ngưỡng nhận diện khuôn mặt (%) để mở cửa', 'recognition'),
('DOOR_OPEN_DURATION_SEC', '3', 'Thời gian giữ chốt cửa mở (giây)', 'hardware'),
('LIVENESS_DETECTION_ENABLED', 'true', 'Bật kiểm tra chống giả mạo bằng ảnh/video (Anti-spoofing)', 'recognition'),
('SYNC_INTERVAL_SEC', '60', 'Chu kỳ đồng bộ tự động giữa Device và Cloud (giây)', 'sync'),
('DUPLICATE_FACE_THRESHOLD', '85', 'Ngưỡng kiểm tra trùng lặp khuôn mặt khi đăng ký (%)', 'registration')
ON CONFLICT (key) DO NOTHING;

-- INDEXES FOR FAST QUERY
CREATE INDEX IF NOT EXISTS idx_access_logs_device_time ON access_logs (device_id, access_time DESC);
CREATE INDEX IF NOT EXISTS idx_access_logs_user_time ON access_logs (user_id, access_time DESC);
CREATE INDEX IF NOT EXISTS idx_users_status ON users (status);
CREATE INDEX IF NOT EXISTS idx_reg_sessions_status ON registration_sessions (status);
