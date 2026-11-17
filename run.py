import sys
from pathlib import Path

# Thêm thư mục backend vào sys.path để import app chuẩn xác
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    import uvicorn
    from app.config import load_settings
    from app.main import create_app

    settings = load_settings()
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)

