"""Model-independent face anti-spoofing interface and MiniFAS ONNX adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Protocol, runtime_checkable

import cv2
import numpy as np
import onnxruntime as ort

from face.detector import FaceDetection


@dataclass(frozen=True)
class AntiSpoofResult:
    is_real: bool
    real_probability: float
    spoof_probability: float
    logit_difference: float
    track_id: int | None
    created_at: float


@runtime_checkable
class FaceAntiSpoofDetector(Protocol):
    def predict(
        self, frame_bgr: np.ndarray, detection: FaceDetection
    ) -> AntiSpoofResult: ...


class MiniFASOnnxDetector:
    """MiniFAS two-class ONNX model using the benchmark preprocessing."""

    INPUT_SIZE = 128
    BBOX_EXPANSION = 1.5
    REAL_THRESHOLD = 0.5

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Face anti-spoof ONNX file not found: {self.model_path}"
            )
        self.session = ort.InferenceSession(
            str(self.model_path), providers=["CPUExecutionProvider"]
        )
        inputs = self.session.get_inputs()
        outputs = self.session.get_outputs()
        if len(inputs) != 1 or len(outputs) != 1:
            raise ValueError("MiniFAS ONNX must have one input and one output")
        self.input = inputs[0]
        self.output = outputs[0]
        shape = self.input.shape
        if len(shape) != 4 or shape[1:] != [3, 128, 128]:
            raise ValueError(
                f"Expected MiniFAS NCHW input [batch,3,128,128], got {shape}"
            )
        self.debug_dir = Path(__file__).resolve().parents[1] / "data" / "fas_inputs"
        self.debug_dir.mkdir(parents=True, exist_ok=True)

    def predict(
        self, frame_bgr: np.ndarray, detection: FaceDetection
    ) -> AntiSpoofResult:
        expanded_crop = crop_face_for_fas(
            frame_bgr, detection.bbox, self.BBOX_EXPANSION
        )
        model_image_bgr, tensor = preprocess_fas(expanded_crop, self.INPUT_SIZE)
        self._save_debug_images(expanded_crop, model_image_bgr)
        logits = np.asarray(
            self.session.run(
                [self.output.name], {self.input.name: tensor}
            )[0],
            dtype=np.float32,
        ).reshape(-1)
        if logits.size != 2 or not np.isfinite(logits).all():
            raise ValueError(f"MiniFAS should return two finite logits, got {logits}")

        shifted = logits - float(np.max(logits))
        probabilities = np.exp(shifted)
        probabilities /= probabilities.sum()
        real_probability = float(probabilities[0])
        spoof_probability = float(probabilities[1])
        return AntiSpoofResult(
            is_real=real_probability >= self.REAL_THRESHOLD,
            real_probability=real_probability,
            spoof_probability=spoof_probability,
            logit_difference=float(logits[0] - logits[1]),
            track_id=detection.track_id,
            created_at=time.monotonic(),
        )

    def _save_debug_images(
        self, expanded_crop_bgr: np.ndarray, model_image_bgr: np.ndarray
    ) -> None:
        """Keep the latest crop and exact 128x128 image sent to MiniFAS."""
        crop_path = self.debug_dir / "latest_crop.png"
        input_path = self.debug_dir / "latest_input_128.png"
        if not cv2.imwrite(str(crop_path), expanded_crop_bgr):
            raise OSError(f"Could not save FAS crop image: {crop_path}")
        if not cv2.imwrite(str(input_path), model_image_bgr):
            raise OSError(f"Could not save FAS input image: {input_path}")


def crop_face_for_fas(
    frame_bgr: np.ndarray,
    bbox: tuple[float, float, float, float],
    expansion: float = 1.5,
) -> np.ndarray:
    """Make a square expanded crop with the benchmark's reflected edge padding."""
    frame = np.asarray(frame_bgr)
    if frame.ndim != 3 or frame.shape[2] != 3 or not frame.size:
        raise ValueError("FAS crop input must be a non-empty BGR HxWx3 frame")
    x1, y1, x2, y2 = bbox
    box_width, box_height = x2 - x1, y2 - y1
    if box_width <= 0 or box_height <= 0 or expansion <= 0:
        raise ValueError("Invalid face bounding box or expansion factor")

    expanded_size = max(box_width, box_height) * expansion
    side = max(1, int(expanded_size))
    center_x, center_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    left = int(center_x - expanded_size / 2)
    top = int(center_y - expanded_size / 2)
    right, bottom = left + side, top + side
    height, width = frame.shape[:2]
    crop = frame[max(0, top):min(height, bottom), max(0, left):min(width, right)]
    if crop.size == 0:
        raise ValueError("Expanded face crop falls outside the camera frame")
    padding = (
        max(0, -left),
        max(0, right - width),
        max(0, -top),
        max(0, bottom - height),
    )
    pad_left, pad_right, pad_top, pad_bottom = padding
    crop = cv2.copyMakeBorder(
        crop,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_REFLECT_101,
    )
    if crop.shape[:2] != (side, side):
        raise ValueError(
            f"Expanded crop should be {side}x{side}, got {crop.shape[1]}x{crop.shape[0]}"
        )
    return crop


def preprocess_fas(
    image_bgr: np.ndarray, size: int = 128
) -> tuple[np.ndarray, np.ndarray]:
    """Match infer_image.py: BGR, letterbox, [0,1], then NCHW batch."""
    height, width = image_bgr.shape[:2]
    scale = size / max(height, width)
    new_width, new_height = int(width * scale), int(height * scale)
    interpolation = cv2.INTER_LANCZOS4 if scale > 1.0 else cv2.INTER_AREA
    resized = cv2.resize(image_bgr, (new_width, new_height), interpolation=interpolation)
    pad_width, pad_height = size - new_width, size - new_height
    model_image = cv2.copyMakeBorder(
        resized,
        pad_height // 2,
        pad_height - pad_height // 2,
        pad_width // 2,
        pad_width - pad_width // 2,
        cv2.BORDER_REFLECT_101,
    )
    tensor = model_image.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    return model_image, np.ascontiguousarray(tensor)
