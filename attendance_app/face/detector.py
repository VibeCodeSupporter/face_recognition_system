"""Model-independent face detector contracts and result types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class FaceDetection:
    """One face box and optional (x, y, visibility) five-point landmarks."""

    bbox: tuple[float, float, float, float]
    confidence: float
    landmarks: tuple[tuple[float, float, float], ...] = ()
    track_id: int | None = None

    def translated(self, offset_x: float, offset_y: float) -> "FaceDetection":
        """Translate a detection from an ROI crop back into full-frame pixels."""
        x1, y1, x2, y2 = self.bbox
        points = tuple(
            (x + offset_x, y + offset_y, visibility)
            for x, y, visibility in self.landmarks
        )
        return FaceDetection(
            bbox=(x1 + offset_x, y1 + offset_y, x2 + offset_x, y2 + offset_y),
            confidence=self.confidence,
            landmarks=points,
            track_id=self.track_id,
        )


@runtime_checkable
class FaceDetector(Protocol):
    """Adapter contract for interchangeable detector backends."""

    def detect(self, frame_bgr: np.ndarray) -> list[FaceDetection]:
        """Detect faces in a BGR frame and return boxes in frame coordinates."""
