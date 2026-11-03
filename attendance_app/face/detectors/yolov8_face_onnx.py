"""Direct ONNX Runtime adapter for the repository's YOLOv8-face Pose ONNX."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from face.detector import FaceDetection
from face.onnx_runtime import create_inference_session


class YOLOv8FaceONNXDetector:
    """Run YOLOv8-face raw pose heads with ONNX Runtime CPU execution."""

    def __init__(
        self,
        model_path: str | Path,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.5,
        max_detections: int = 128,
    ) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Face detector ONNX file not found: {self.model_path}")
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")
        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0 and 1")

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.max_detections = max_detections
        self.session = create_inference_session(self.model_path)
        inputs = self.session.get_inputs()
        if len(inputs) != 1:
            raise ValueError(f"Expected one ONNX input, found {len(inputs)}")
        self.input = inputs[0]
        shape = self.input.shape
        if len(shape) != 4 or shape[1] not in (3, "3", None, "None"):
            raise ValueError(f"Expected an NCHW, 3-channel ONNX input; got {shape}")
        self.input_height = shape[2] if isinstance(shape[2], int) else 640
        self.input_width = shape[3] if isinstance(shape[3], int) else 640

    def detect(self, frame_bgr: np.ndarray) -> list[FaceDetection]:
        frame = np.asarray(frame_bgr)
        if frame.ndim != 3 or frame.shape[2] != 3 or not frame.size:
            raise ValueError("detector input must be a non-empty BGR HxWx3 image")

        original_height, original_width = frame.shape[:2]
        padded, scale, pad_x, pad_y = _letterbox(
            frame, self.input_height, self.input_width
        )
        tensor = padded[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32)
        tensor /= 255.0
        outputs = self.session.run(
            None, {self.input.name: np.ascontiguousarray(tensor)}
        )
        boxes, scores, points = _decode_heads(
            outputs,
            self.input_height,
            self.input_width,
            self.confidence_threshold,
        )
        keep = _nms_xyxy(
            boxes, scores, self.iou_threshold, self.max_detections
        )
        boxes, scores, points = boxes[keep], scores[keep], points[keep]

        results: list[FaceDetection] = []
        for box, score, landmarks in zip(boxes, scores, points):
            box[[0, 2]] = (box[[0, 2]] - pad_x) / scale
            box[[1, 3]] = (box[[1, 3]] - pad_y) / scale
            box[[0, 2]] = np.clip(box[[0, 2]], 0, original_width - 1)
            box[[1, 3]] = np.clip(box[[1, 3]], 0, original_height - 1)
            x1, y1, x2, y2 = map(float, box)
            if x2 <= x1 or y2 <= y1:
                continue

            landmarks[:, 0] = (landmarks[:, 0] - pad_x) / scale
            landmarks[:, 1] = (landmarks[:, 1] - pad_y) / scale
            landmarks[:, 0] = np.clip(landmarks[:, 0], 0, original_width - 1)
            landmarks[:, 1] = np.clip(landmarks[:, 1], 0, original_height - 1)
            point_tuples = tuple(
                (float(x), float(y), float(visibility))
                for x, y, visibility in landmarks
            )
            results.append(
                FaceDetection(
                    bbox=(x1, y1, x2, y2),
                    confidence=float(score),
                    landmarks=point_tuples,
                )
            )
        return results


def _sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -80.0, 80.0)
    return 1.0 / (1.0 + np.exp(-values))


def _letterbox(
    image: np.ndarray, target_height: int, target_width: int
) -> tuple[np.ndarray, float, int, int]:
    height, width = image.shape[:2]
    scale = min(target_width / width, target_height / height)
    resized_width = int(round(width * scale))
    resized_height = int(round(height * scale))
    resized = cv2.resize(
        image, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR
    )
    dw, dh = target_width - resized_width, target_height - resized_height
    left = int(round(dw / 2 - 0.1))
    right = int(round(dw / 2 + 0.1))
    top = int(round(dh / 2 - 0.1))
    bottom = int(round(dh / 2 + 0.1))
    padded = cv2.copyMakeBorder(
        resized,
        top,
        bottom,
        left,
        right,
        cv2.BORDER_CONSTANT,
        value=(114, 114, 114),
    )
    return padded, scale, left, top


def _decode_heads(
    outputs: list[np.ndarray],
    input_height: int,
    input_width: int,
    confidence_threshold: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decode the repo's [DFL box(64), face score(1), 5x3 landmarks] heads."""
    boxes_all: list[np.ndarray] = []
    scores_all: list[np.ndarray] = []
    points_all: list[np.ndarray] = []
    bins = np.arange(16, dtype=np.float32)[None, :, None, None]

    for output in outputs:
        output = np.asarray(output)
        if output.ndim != 4 or output.shape[0] != 1 or output.shape[1] != 80:
            raise ValueError(
                "Unsupported YOLOv8-face ONNX output. Expected raw head "
                f"[1, 80, H, W], got {output.shape}; use another adapter for "
                "a different ONNX export format."
            )

        _, _, height, width = output.shape
        stride_y, stride_x = input_height / height, input_width / width
        if abs(stride_x - stride_y) > 1e-6:
            raise ValueError(f"Non-square feature stride in output {output.shape}")
        stride = stride_x

        dfl = output[0, :64].reshape(4, 16, height, width)
        dfl = dfl - dfl.max(axis=1, keepdims=True)
        probabilities = np.exp(dfl)
        probabilities /= probabilities.sum(axis=1, keepdims=True) + 1e-9
        distances = (probabilities * bins).sum(axis=1)

        scores = _sigmoid(output[0, 64])
        grid_y, grid_x = np.meshgrid(
            np.arange(height, dtype=np.float32),
            np.arange(width, dtype=np.float32),
            indexing="ij",
        )
        anchor_x, anchor_y = grid_x + 0.5, grid_y + 0.5
        left, top, right, bottom = distances
        boxes = np.stack(
            (
                (anchor_x - left) * stride,
                (anchor_y - top) * stride,
                (anchor_x + right) * stride,
                (anchor_y + bottom) * stride,
            ),
            axis=-1,
        ).reshape(-1, 4)

        raw_points = output[0, 65:80].reshape(5, 3, height, width)
        points_x = (raw_points[:, 0] * 2.0 + grid_x[None]) * stride
        points_y = (raw_points[:, 1] * 2.0 + grid_y[None]) * stride
        visibility = _sigmoid(raw_points[:, 2])
        points = np.stack((points_x, points_y, visibility), axis=-1)
        points = points.transpose(1, 2, 0, 3).reshape(-1, 5, 3)

        keep = scores.reshape(-1) >= confidence_threshold
        if np.any(keep):
            boxes_all.append(boxes[keep])
            scores_all.append(scores.reshape(-1)[keep])
            points_all.append(points[keep])

    if not boxes_all:
        return (
            np.empty((0, 4), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            np.empty((0, 5, 3), dtype=np.float32),
        )
    return np.concatenate(boxes_all), np.concatenate(scores_all), np.concatenate(points_all)


def _nms_xyxy(
    boxes: np.ndarray, scores: np.ndarray, threshold: float, max_detections: int
) -> np.ndarray:
    if not len(boxes):
        return np.empty((0,), dtype=np.int64)
    x1, y1, x2, y2 = boxes.T
    areas = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size and len(keep) < max_detections:
        current = int(order[0])
        keep.append(current)
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(x1[current], x1[rest])
        yy1 = np.maximum(y1[current], y1[rest])
        xx2 = np.minimum(x2[current], x2[rest])
        yy2 = np.minimum(y2[current], y2[rest])
        intersection = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou = intersection / (areas[current] + areas[rest] - intersection + 1e-9)
        order = rest[iou <= threshold]
    return np.asarray(keep, dtype=np.int64)
