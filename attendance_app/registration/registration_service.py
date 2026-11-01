"""Application service for registering an employee's five face poses."""

from __future__ import annotations

import numpy as np
import cv2
import re
import shutil
from pathlib import Path

from config.settings import APP_ROOT
from storage.vector_store import VectorStore


class EnrollmentSample:
    def __init__(self, pose: str, vector: np.ndarray, aligned_rgb: np.ndarray) -> None:
        self.pose = pose
        self.vector = vector
        self.aligned_rgb = aligned_rgb


class RegistrationService:
    def __init__(self, vector_store: VectorStore) -> None:
        self.vector_store = vector_store

    def register(
        self,
        employee_id: str,
        name: str,
        samples: list[EnrollmentSample],
    ) -> Path:
        employee_id = employee_id.strip()
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", employee_id):
            raise ValueError("Employee ID can contain only letters, numbers, _ and -")
        if not name:
            raise ValueError("Employee name is required")
        if len(samples) != 5:
            raise ValueError("Exactly five pose samples are required")

        image_dir = APP_ROOT / "data" / "enrollments" / employee_id
        if image_dir.exists():
            raise FileExistsError(f"Enrollment image folder already exists: {image_dir}")
        image_dir.mkdir(parents=True, exist_ok=False)
        try:
            for sample in samples:
                image = np.asarray(sample.aligned_rgb)
                if image.shape != (112, 112, 3) or image.dtype != np.uint8:
                    raise ValueError("Enrollment images must be aligned RGB 112x112")
                image_path = image_dir / f"{sample.pose}.png"
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                if not cv2.imwrite(str(image_path), image_bgr):
                    raise OSError(f"Could not save enrollment image: {image_path}")

            self.vector_store.add_employee(
                employee_id,
                name,
                [(sample.pose, sample.vector) for sample in samples],
            )
        except Exception:
            shutil.rmtree(image_dir, ignore_errors=True)
            raise
        return image_dir
