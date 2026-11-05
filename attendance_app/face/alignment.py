"""Five-landmark similarity alignment for EdgeFace's 112x112 input."""

from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

# ArcFace/EdgeFace 112x112 reference points in this order:
# left eye, right eye, nose, left mouth corner, right mouth corner.
REFERENCE_LANDMARKS_112 = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


def _as_five_points(landmarks: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
    """Accept 5x2 points or MTCNN's flat [x0..x4, y0..y4] output."""
    points = np.asarray(landmarks, dtype=np.float32)
    if points.shape == (10,):
        points = np.column_stack((points[:5], points[5:]))
    elif points.shape == (1, 10):
        points = points.reshape(10)
        points = np.column_stack((points[:5], points[5:]))

    if points.shape != (5, 2):
        raise ValueError(
            "landmarks must be shaped (5, 2) or be MTCNN's 10-value format; "
            f"got {points.shape}"
        )
    if not np.isfinite(points).all():
        raise ValueError("landmarks must contain only finite coordinates")
    return points


def align_face(
    image: np.ndarray,
    landmarks: Sequence[Sequence[float]] | np.ndarray,
    output_size: tuple[int, int] = (112, 112),
) -> np.ndarray:
    """Align one face from five landmarks and return a normalized-size crop.

    This is the geometric warp only; it does not detect faces and has no MTCNN
    or Torch dependency. ``image`` can be BGR or RGB, and its channel order is
    preserved. Coordinates must refer to this image (including any ROI crop).
    ``output_size`` is ``(width, height)``; EdgeFace uses its default 112x112.
    """
    frame = np.asarray(image)
    if frame.ndim not in (2, 3) or frame.shape[0] == 0 or frame.shape[1] == 0:
        raise ValueError("image must be a non-empty HxW or HxWxC array")

    width, height = output_size
    if width <= 0 or height <= 0:
        raise ValueError("output_size dimensions must be positive")

    source = _as_five_points(landmarks)
    target = REFERENCE_LANDMARKS_112.copy()
    target[:, 0] *= width / 112.0
    target[:, 1] *= height / 112.0

    # Fit an orientation-preserving similarity transform: uniform scale,
    # rotation, and translation. This uses only NumPy and the five landmarks.
    x, y = source[:, 0], source[:, 1]
    design = np.empty((10, 4), dtype=np.float32)
    design[:5] = np.column_stack((x, -y, np.ones(5), np.zeros(5)))
    design[5:] = np.column_stack((y, x, np.zeros(5), np.ones(5)))
    observations = np.concatenate((target[:, 0], target[:, 1]))
    a, b, translate_x, translate_y = np.linalg.lstsq(
        design, observations, rcond=None
    )[0]
    transform = np.array(
        [[a, -b, translate_x], [b, a, translate_y]], dtype=np.float32
    )
    if not np.isfinite(transform).all() or (a * a + b * b) < 1e-8:
        raise ValueError("could not estimate a valid face alignment transform")

    return cv2.warpAffine(
        frame,
        transform,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
