"""
Face Recognition Access Control System - Cloud Backend Service
Framework: FastAPI (Python 3.11)
Features:
- Web Portal REST API (Users, Sessions, Access Logs, Devices, System Config)
- Edge Device Synchronization API (Device Heartbeat, Log Sync, Incremental User & Vector Sync)
- Face Registration & Duplicate Check
"""

import os
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

app = FastAPI(
    title="FaceAccess Cloud Backend API",
    version="1.0.0",
    description="Backend API phục vụ Web Portal và Edge Face Access Device Synchronization"
)

# Enable CORS for Web Portal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# PYDANTIC SCHEMAS (Data Transfer Objects)
# -------------------------------------------------------------
class UserCreate(BaseModel):
    user_code: str
    full_name: str
    email: Optional[EmailStr] = None
    department: Optional[str] = "Kỹ thuật"
    role: Optional[str] = "Staff"

class UserResponse(BaseModel):
    id: str
    user_code: str
    full_name: str
    email: Optional[str]
    department: Optional[str]
    role: str
    status: str
    face_status: str

class DeviceHeartbeat(BaseModel):
    device_code: str
    firmware_version: str
    ip_address: str
    status: str
    uptime: Optional[str] = None

class AccessLogItem(BaseModel):
    log_uuid: str
    device_code: str
    user_id: Optional[str] = None
    unrecognized_label: Optional[str] = None
    result: str  # 'granted' / 'denied'
    confidence: float
    access_time: str

class SyncLogRequest(BaseModel):
    device_code: str
    logs: List[AccessLogItem]

class RegistrationSessionCreate(BaseModel):
    user_id: str
    target_device_id: Optional[str] = None
    expires_in_hours: int = 24

# -------------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------------
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": "FaceAccess Cloud Backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# -------------------------------------------------------------
# WEB PORTAL APIS
# -------------------------------------------------------------
@app.get("/api/v1/users", tags=["Users"])
def get_users(dept: Optional[str] = None, status: Optional[str] = None):
    # Mock data or PostgreSQL Query
    return {
        "total": 7,
        "users": [
            {"id": "USR001", "name": "Nguyễn Văn An", "email": "an.nguyen@company.vn", "dept": "Kỹ thuật", "role": "Engineer", "status": "active", "faceStatus": "enrolled"},
            {"id": "USR002", "name": "Trần Thị Bình", "email": "binh.tran@company.vn", "dept": "Nhân sự", "role": "HR Manager", "status": "active", "faceStatus": "enrolled"},
            {"id": "USR003", "name": "Lê Hoàng Cường", "email": "cuong.le@company.vn", "dept": "IT", "role": "Admin", "status": "active", "faceStatus": "enrolled"}
        ]
    }

@app.post("/api/v1/users", status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(user: UserCreate):
    return {
        "message": "Tạo người dùng thành công",
        "user_code": user.user_code,
        "status": "pending_face_enrollment"
    }

@app.get("/api/v1/devices", tags=["Devices"])
def get_devices():
    return [
        {"id": "DEV001", "name": "Cổng Chính A", "location": "Tầng 1 - Sảnh chính", "ip": "192.168.1.101", "status": "online", "lastSync": "2 phút trước"},
        {"id": "DEV002", "name": "Cổng Phụ B", "location": "Tầng 1 - Cửa hông", "ip": "192.168.1.102", "status": "online", "lastSync": "5 phút trước"},
        {"id": "DEV003", "name": "Cổng Kho C", "location": "Tầng B1 - Kho hàng", "ip": "192.168.1.103", "status": "warning", "lastSync": "2 giờ trước"}
    ]

@app.post("/api/v1/registration/sessions", tags=["Registration"])
def create_registration_session(req: RegistrationSessionCreate):
    session_id = f"SES-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return {
        "session_id": session_id,
        "user_id": req.user_id,
        "status": "active",
        "message": "Phiên đăng ký khuôn mặt đã được tạo. Sẵn sàng nhận dữ liệu từ Device hoặc Web Camera."
    }

# -------------------------------------------------------------
# EDGE DEVICE SYNCHRONIZATION APIS (Device <-> Cloud)
# -------------------------------------------------------------
@app.post("/api/v1/device/heartbeat", tags=["Device Sync"])
def device_heartbeat(data: DeviceHeartbeat, x_device_token: Optional[str] = Header(None)):
    """Device gửi heartbeat định kỳ cập nhật trạng thái online và IP"""
    return {"status": "ok", "ack_time": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/device/sync/logs", tags=["Device Sync"])
def sync_access_logs(payload: SyncLogRequest):
    """Device đẩy offline access logs lên Cloud sau khi có kết nối trở lại"""
    count = len(payload.logs)
    return {
        "status": "success",
        "synced_count": count,
        "message": f"Đã đồng bộ {count} bản ghi nhật ký ra vào từ {payload.device_code}"
    }

@app.get("/api/v1/device/sync/users-diff", tags=["Device Sync"])
def sync_users_diff(device_code: str, since_timestamp: Optional[str] = None):
    """Cloud trả về danh sách user và face vector mới/được sửa đổi để Device cập nhật vào Local Vector DB"""
    return {
        "updated_users": [],
        "deleted_user_ids": [],
        "server_time": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
