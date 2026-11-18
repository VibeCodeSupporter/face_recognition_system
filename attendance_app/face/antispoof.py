"""Silent-Face ONNX anti-spoofing adapter and upstream-compatible crops."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Protocol, runtime_checkable

import cv2
import numpy as np
from face.detector import FaceDetection
from face.debug_images import save_module_input
from face.onnx_runtime import create_inference_session


@dataclass(frozen=True)
class AntiSpoofResult:
    is_real: bool
    real_probability: float
    spoof_probability: float
    real_threshold: float
    track_id: int | None
    created_at: float


@runtime_checkable
class FaceAntiSpoofDetector(Protocol):
    def prepare_inputs(
        self, frame_bgr: np.ndarray, detection: FaceDetection,
        *, frame_id: int | None = None,
    ) -> list[tuple[tuple, np.ndarray]]: ...

    def predict_prepared(
        self, prepared_inputs: list[tuple[tuple, np.ndarray]],
        detection: FaceDetection,
    ) -> AntiSpoofResult: ...

    def predict(
        self, frame_bgr: np.ndarray, detection: FaceDetection,
        *, frame_id: int | None = None,
    ) -> AntiSpoofResult: ...


class SilentFaceOnnxDetector:
    """Fuse Silent-Face 2.7/4.0 ONNX models using repository preprocessing."""

    INPUT_SIZE = 80

    def __init__(self, model_paths: list[str | Path], real_threshold: float = 0.5) -> None:
        if not model_paths:
            raise ValueError("At least one Silent-Face ONNX model is required")
        self.real_threshold = float(real_threshold)
        self.models = []
        for model_path in model_paths:
            path = Path(model_path).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Silent-Face ONNX not found: {path}")
            scale = _scale_from_filename(path.name)
            session = create_inference_session(path)
            inputs, outputs = session.get_inputs(), session.get_outputs()
            if len(inputs) != 1 or len(outputs) != 1:
                raise ValueError(f"Silent-Face ONNX must have one input/output: {path}")
            shape = inputs[0].shape
            if len(shape) != 4 or shape[1:] != [3, 80, 80]:
                raise ValueError(f"Expected Silent-Face NCHW [batch,3,80,80], got {shape}: {path}")
            self.models.append((path, scale, session, inputs[0].name, outputs[0].name))

    def predict(
        self, frame_bgr: np.ndarray, detection: FaceDetection,
        *, frame_id: int | None = None,
    ) -> AntiSpoofResult:
        prepared_inputs = self.prepare_inputs(
            frame_bgr, detection, frame_id=frame_id
        )
        return self.predict_prepared(prepared_inputs, detection)

    def prepare_inputs(
        self, frame_bgr: np.ndarray, detection: FaceDetection,
        *, frame_id: int | None = None,
    ) -> list[tuple[tuple, np.ndarray]]:
        """Crop/resize both Silent-Face inputs without running either model."""
        frame = np.asarray(frame_bgr)
        bbox = _bbox_xywh(detection.bbox)
        prepared_inputs = []
        for path, scale, session, input_name, output_name in self.models:
            crop = crop_silentface(frame, bbox, scale, self.INPUT_SIZE, self.INPUT_SIZE)
            if frame_id is not None:
                variant = f"{_scale_label(scale)}_input_80"
                save_module_input("silentface", frame_id, crop, variant=variant)
            # Silent-Face ToTensor keeps OpenCV BGR order and float pixel values in [0,255].
            tensor = np.ascontiguousarray(crop.transpose(2, 0, 1)[None], dtype=np.float32)
            prepared_inputs.append(((path, scale, session, input_name, output_name), tensor))
        return prepared_inputs

    def predict_prepared(
        self, prepared_inputs: list[tuple[tuple, np.ndarray]],
        detection: FaceDetection,
    ) -> AntiSpoofResult:
        """Run the FAS models on already prepared 80x80 inputs."""
        summed_probabilities = np.zeros(3, dtype=np.float64)
        for model, tensor in prepared_inputs:
            path, _scale, session, input_name, output_name = model
            logits = np.asarray(session.run([output_name], {input_name: tensor})[0], dtype=np.float32).reshape(-1)
            if logits.size != 3 or not np.isfinite(logits).all():
                raise ValueError(f"Silent-Face should return 3 finite logits, got {logits}: {path}")
            shifted = logits - float(logits.max())
            probabilities = np.exp(shifted)
            summed_probabilities += probabilities / probabilities.sum()
        # Upstream test.py sums each model's softmax output; class 1 is REAL.
        real_probability = float(summed_probabilities[1] / len(self.models))
        spoof_probability = float((summed_probabilities[0] + summed_probabilities[2]) / len(self.models))
        is_real = int(np.argmax(summed_probabilities)) == 1 and real_probability >= self.real_threshold
        return AntiSpoofResult(
            is_real, real_probability, spoof_probability, self.real_threshold,
            detection.track_id, time.monotonic(),
        )


def _scale_from_filename(filename: str) -> float:
    stem = Path(filename).stem
    if stem.startswith("2.7_"):
        return 2.7
    if stem.startswith(("4.0_", "4_")):
        return 4.0
    raise ValueError(f"Cannot determine Silent-Face crop scale from model filename: {filename}")


def _scale_label(scale: float) -> str:
    return str(scale).replace(".", "_")


def _bbox_xywh(bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    left, top = int(np.floor(x1)), int(np.floor(y1))
    right, bottom = int(np.ceil(x2)), int(np.ceil(y2))
    return left, top, right - left, bottom - top


def crop_silentface(
    frame_bgr: np.ndarray, bbox: tuple[float, float, float, float],
    scale: float, out_width: int = 80, out_height: int = 80,
) -> np.ndarray:
    """Replicate upstream CropImage._get_new_box and cv2.resize exactly."""
    frame = np.asarray(frame_bgr)
    if frame.ndim != 3 or frame.shape[2] != 3 or not frame.size:
        raise ValueError("Silent-Face crop input must be a non-empty BGR frame")
    x, y, box_w, box_h = bbox
    if box_w <= 0 or box_h <= 0 or scale <= 0:
        raise ValueError("Invalid Silent-Face bbox or scale")
    src_h, src_w = frame.shape[:2]
    scale = min((src_h - 1) / box_h, (src_w - 1) / box_w, scale)
    new_w, new_h = box_w * scale, box_h * scale
    cx, cy = x + box_w / 2, y + box_h / 2
    left, top = int(cx - new_w / 2), int(cy - new_h / 2)
    right, bottom = int(cx + new_w / 2), int(cy + new_h / 2)
    if left < 0:
        right -= left
        left = 0
    if top < 0:
        bottom -= top
        top = 0
    if right > src_w - 1:
        left -= right - src_w + 1
        right = src_w - 1
    if bottom > src_h - 1:
        top -= bottom - src_h + 1
        bottom = src_h - 1
    left, top = max(0, left), max(0, top)
    crop = frame[top:bottom + 1, left:right + 1]
    if crop.size == 0:
        raise ValueError("Silent-Face crop is empty")
    return cv2.resize(crop, (out_width, out_height))
