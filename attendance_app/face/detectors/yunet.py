"""YuNet face detector using OpenCV and a fixed 320x320 input."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from face.detector import FaceDetection
from face.debug_images import save_module_input


class YuNetFaceDetector:
    """Detect faces with YuNet and map its results back to the source image."""

    INPUT_SIZE = 320
    PADDING_VALUE = 114

    def __init__(
        self,
        model_path: str | Path,
        confidence_threshold: float = 0.50,
        iou_threshold: float = 0.50,
        top_k: int = 2048,
    ) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_file():
            raise FileNotFoundError(f"YuNet ONNX file not found: {self.model_path}")

        self.detector = cv2.FaceDetectorYN.create(
            str(self.model_path),
            "",
            (self.INPUT_SIZE, self.INPUT_SIZE),
            confidence_threshold,
            iou_threshold,
            top_k,
        )
        self.detector.setInputSize((self.INPUT_SIZE, self.INPUT_SIZE))

    def detect(
        self, frame_bgr: np.ndarray, *, frame_id: int | None = None
    ) -> list[FaceDetection]:
        """Return face boxes and landmarks in source-image coordinates."""
        frame = np.asarray(frame_bgr)
        if frame.ndim != 3 or frame.shape[2] != 3 or not frame.size:
            raise ValueError("Expected a non-empty BGR HxWx3 image")

        source_height, source_width = frame.shape[:2]
        scale = self.INPUT_SIZE / max(source_height, source_width)
        resized_width = max(1, round(source_width * scale))
        resized_height = max(1, round(source_height * scale))
        resized = cv2.resize(frame, (resized_width, resized_height))

        pad_x = (self.INPUT_SIZE - resized_width) // 2
        pad_y = (self.INPUT_SIZE - resized_height) // 2
        input_image = np.full(
            (self.INPUT_SIZE, self.INPUT_SIZE, 3),
            self.PADDING_VALUE,
            dtype=frame.dtype,
        )
        input_image[
            pad_y : pad_y + resized_height,
            pad_x : pad_x + resized_width,
        ] = resized

        if frame_id is not None:
            save_module_input("yunet", frame_id, input_image, variant="input_320")

        _, faces = self.detector.detect(input_image)
        if faces is None or not len(faces):
            return []

        detections: list[FaceDetection] = []
        for face in faces:
            detection = self._convert_face(
                face,
                scale,
                pad_x,
                pad_y,
                source_width,
                source_height,
            )
            if detection is not None:
                detections.append(detection)
        return detections

    @staticmethod
    def _convert_face(
        face: np.ndarray,
        scale: float,
        pad_x: int,
        pad_y: int,
        source_width: int,
        source_height: int,
    ) -> FaceDetection | None:
        """Map one YuNet row to source coordinates and alignment landmark order."""
        x, y, width, height = map(float, face[:4])
        x1 = float(np.clip((x - pad_x) / scale, 0, source_width - 1))
        y1 = float(np.clip((y - pad_y) / scale, 0, source_height - 1))
        x2 = float(np.clip((x + width - pad_x) / scale, 0, source_width - 1))
        y2 = float(np.clip((y + height - pad_y) / scale, 0, source_height - 1))
        if x2 <= x1 or y2 <= y1:
            return None

        points = np.asarray(face[4:14], dtype=np.float32).reshape(5, 2)
        points[:, 0] = np.clip(
            (points[:, 0] - pad_x) / scale, 0, source_width - 1
        )
        points[:, 1] = np.clip(
            (points[:, 1] - pad_y) / scale, 0, source_height - 1
        )

        # FaceDetectorYN returns right eye, left eye, nose, right mouth,
        # left mouth. The right-side facial landmarks are on the image-left
        # for a frontal face, so YuNet's native order already matches the
        # image-left-to-right order expected by the pose and alignment models.
        landmarks = tuple(
            (float(point_x), float(point_y), 1.0)
            for point_x, point_y in points
        )
        return FaceDetection(
            bbox=(x1, y1, x2, y2),
            confidence=float(face[14]),
            landmarks=landmarks,
        )
