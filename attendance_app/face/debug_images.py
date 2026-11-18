"""Bounded storage for exact image inputs sent to face pipeline modules."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from config import settings


MAX_DEBUG_IMAGES = 50


def save_module_input(
    module: str,
    frame_id: int,
    image: np.ndarray,
    *,
    variant: str = "input",
) -> Path | None:
    """Save one module input and retain at most 50 images for that module."""
    if not settings.FRAME_DEBUG_SAVE_IMAGES:
        return None
    module_dir = settings.APP_ROOT / "data" / "pipeline_debug" / module
    module_dir.mkdir(parents=True, exist_ok=True)
    if module == "camera":
        # Remove unbounded JPEGs produced by the earlier debug implementation.
        legacy_dir = settings.APP_ROOT / "data" / "pipeline_debug"
        for legacy_path in legacy_dir.glob("frame_*.jpg"):
            try:
                legacy_path.unlink()
            except OSError:
                pass
    safe_variant = "".join(c if c.isalnum() or c in "._-" else "_" for c in variant)
    image_path = module_dir / f"frame_{frame_id:08d}_{safe_variant}.png"
    if not cv2.imwrite(str(image_path), np.asarray(image)):
        return None
    images = sorted(module_dir.glob("*.png"), key=lambda path: path.stat().st_mtime_ns)
    for stale_path in images[:-MAX_DEBUG_IMAGES]:
        try:
            stale_path.unlink()
        except OSError:
            pass
    return image_path
