"""Select an installed detector backend without coupling callers to a model."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from config.settings import (
    FACE_DETECTOR_CONFIDENCE,
    FACE_DETECTOR_IOU,
    FACE_DETECTOR_MODEL_PATH,
    FACE_DETECTOR_NAME,
)
from face.detector import FaceDetector
from face.detectors.yunet import YuNetFaceDetector


DetectorBuilder = Callable[[Path], FaceDetector]


def _build_yunet(model_path: Path) -> FaceDetector:
    return YuNetFaceDetector(
        model_path,
        confidence_threshold=FACE_DETECTOR_CONFIDENCE,
        iou_threshold=FACE_DETECTOR_IOU,
    )


# Add a backend here; the camera worker and UI keep using FaceDetector.detect().
DETECTOR_BUILDERS: dict[str, DetectorBuilder] = {
    "yunet": _build_yunet,
}


def create_face_detector(
    name: str | None = None, model_path: str | Path | None = None
) -> FaceDetector:
    detector_name = name or FACE_DETECTOR_NAME
    builder = DETECTOR_BUILDERS.get(detector_name)
    if builder is None:
        available = ", ".join(sorted(DETECTOR_BUILDERS))
        raise ValueError(
            f"Unknown face detector '{detector_name}'. Available: {available}"
        )
    path = (
        Path(model_path).expanduser()
        if model_path is not None
        else FACE_DETECTOR_MODEL_PATH
    )
    if path is None:
        raise ValueError(
            "FACE_DETECTOR_MODEL must point to a local ONNX file in .env"
        )
    return builder(path)
