"""Runtime configuration for the device demo."""

import os
from pathlib import Path

from dotenv import load_dotenv

APP_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(APP_ROOT / ".env")

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

FACE_DETECTOR_NAME = os.getenv("FACE_DETECTOR", "yolov8_face_onnx")
_model_path = os.getenv("FACE_DETECTOR_MODEL", "").strip()
FACE_DETECTOR_MODEL_PATH = (
    Path(_model_path).expanduser() if _model_path else None
)
if FACE_DETECTOR_MODEL_PATH is not None and not FACE_DETECTOR_MODEL_PATH.is_absolute():
    FACE_DETECTOR_MODEL_PATH = APP_ROOT / FACE_DETECTOR_MODEL_PATH
FACE_DETECTOR_CONFIDENCE = float(os.getenv("FACE_DETECTOR_CONFIDENCE", "0.50"))
FACE_DETECTOR_IOU = float(os.getenv("FACE_DETECTOR_IOU", "0.50"))
FACE_TRACKER_LOST_BUFFER = int(os.getenv("FACE_TRACKER_LOST_BUFFER", "30"))

FACE_EMBEDDER_NAME = os.getenv("FACE_EMBEDDER", "ghostfacenet_onnx")
_embedding_model_path = os.getenv("FACE_EMBEDDING_MODEL", "").strip()
FACE_EMBEDDING_MODEL_PATH = (
    Path(_embedding_model_path).expanduser() if _embedding_model_path else None
)
if (
    FACE_EMBEDDING_MODEL_PATH is not None
    and not FACE_EMBEDDING_MODEL_PATH.is_absolute()
):
    FACE_EMBEDDING_MODEL_PATH = APP_ROOT / FACE_EMBEDDING_MODEL_PATH
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "1.60"))

FACE_ANTISPOOF_NAME = os.getenv("FACE_ANTISPOOF", "mini_fas_onnx")
FACE_ANTISPOOF_LOGIT_THRESHOLD = float(
    os.getenv("FACE_ANTISPOOF_LOGIT_THRESHOLD", "0.0")
)
_antispoof_model_path = os.getenv("FACE_ANTISPOOF_MODEL", "").strip()
FACE_ANTISPOOF_MODEL_PATH = (
    Path(_antispoof_model_path).expanduser() if _antispoof_model_path else None
)
if (
    FACE_ANTISPOOF_MODEL_PATH is not None
    and not FACE_ANTISPOOF_MODEL_PATH.is_absolute()
):
    FACE_ANTISPOOF_MODEL_PATH = APP_ROOT / FACE_ANTISPOOF_MODEL_PATH
