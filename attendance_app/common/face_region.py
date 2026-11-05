"""Shared normalized face-capture region used by the UI and detector."""

from __future__ import annotations

import numpy as np

# (x, y, width, height), normalized relative to the camera frame.
FACE_ROI = (0.22, 0.08, 0.56, 0.84)


def face_roi_bounds(frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
    """Return ROI pixel bounds as (left, top, right, bottom)."""
    x, y, width, height = FACE_ROI
    left = round(x * frame_width)
    top = round(y * frame_height)
    right = round((x + width) * frame_width)
    bottom = round((y + height) * frame_height)
    return left, top, right, bottom


def crop_face_roi(frame: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Crop the shared ROI and return it with its (x, y) frame offset."""
    height, width = frame.shape[:2]
    left, top, right, bottom = face_roi_bounds(width, height)
    return frame[top:bottom, left:right], left, top
