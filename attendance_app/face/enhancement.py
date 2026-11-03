"""Face-region enhancement adapters used after detection."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import cv2
import numpy as np

from face.detector import FaceDetection
from face.antispoof import crop_face_for_fas
from face.ying import Ying_2017_CAIP


@runtime_checkable
class FaceEnhancer(Protocol):
    """Enhance a detected face region while returning a full BGR frame."""

    def enhance_detection(
        self, frame_bgr: np.ndarray, detection: FaceDetection
    ) -> np.ndarray: ...


class Ying2017FaceEnhancer:
    """Apply Ying 2017 enhancement to an expanded face crop and paste it back."""

    CROP_EXPANSION = 1.5

    def __init__(self, debug_dir: str | Path | None = None) -> None:
        self.debug_dir = (
            Path(debug_dir)
            if debug_dir is not None
            else Path(__file__).resolve().parents[1] / "data" / "ying_inputs"
        )
        self._calls = 0

    def enhance_detection(
        self, frame_bgr: np.ndarray, detection: FaceDetection
    ) -> np.ndarray:
        crop = crop_face_for_fas(
            frame_bgr, detection.bbox, expansion=self.CROP_EXPANSION
        )
        enhanced_crop = Ying_2017_CAIP(crop)
        self._calls += 1
        if self._calls % 10 == 1:
            self._save_debug_images(crop, enhanced_crop)

        x1, y1, x2, y2 = detection.bbox
        side = max(1, int(max(x2 - x1, y2 - y1) * self.CROP_EXPANSION))
        left = int((x1 + x2) / 2.0 - max(x2 - x1, y2 - y1) * self.CROP_EXPANSION / 2)
        top = int((y1 + y2) / 2.0 - max(x2 - x1, y2 - y1) * self.CROP_EXPANSION / 2)

        frame_height, frame_width = frame_bgr.shape[:2]
        paste_left, paste_top = max(0, left), max(0, top)
        paste_right, paste_bottom = min(frame_width, left + side), min(frame_height, top + side)
        crop_left, crop_top = paste_left - left, paste_top - top
        crop_right = crop_left + paste_right - paste_left
        crop_bottom = crop_top + paste_bottom - paste_top

        enhanced_frame = frame_bgr.copy()
        enhanced_frame[paste_top:paste_bottom, paste_left:paste_right] = enhanced_crop[
            crop_top:crop_bottom, crop_left:crop_right
        ]
        return enhanced_frame

    def _save_debug_images(
        self, original_crop: np.ndarray, enhanced_crop: np.ndarray
    ) -> None:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        original_path = self.debug_dir / "latest_crop_before.png"
        enhanced_path = self.debug_dir / "latest_crop_after.png"
        if not cv2.imwrite(str(original_path), original_crop):
            raise OSError(f"Could not save original Ying input: {original_path}")
        if not cv2.imwrite(str(enhanced_path), enhanced_crop):
            raise OSError(f"Could not save enhanced Ying input: {enhanced_path}")
