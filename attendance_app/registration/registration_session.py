"""In-memory enrollment progress and pose sequence."""

from __future__ import annotations

from pathlib import Path

from registration.registration_service import EnrollmentSample
from registration.registration_service import RegistrationService


class RegistrationSession:
    POSES = (
        ("front", "Nhìn thẳng", "Nhìn vào camera, giữ đầu tự nhiên."),
        ("left", "Quay sang trái", "Quay mặt nhẹ sang trái rồi giữ yên."),
        ("right", "Quay sang phải", "Quay mặt nhẹ sang phải rồi giữ yên."),
        ("down", "Cúi nhẹ", "Cúi mặt nhẹ xuống rồi giữ yên."),
        ("up", "Ngửa nhẹ", "Ngửa mặt nhẹ lên rồi giữ yên."),
    )

    def __init__(self, service: RegistrationService) -> None:
        self.service = service
        self.samples: list[EnrollmentSample] = []
        self.employee_id = ""
        self.name = ""
        self.saved_path: Path | None = None

    def begin(self, employee_id: str, name: str) -> None:
        self.reset()
        self.employee_id = employee_id.strip()
        self.name = name.strip()

    @property
    def current_pose(self) -> str | None:
        if len(self.samples) >= len(self.POSES):
            return None
        return self.POSES[len(self.samples)][0]

    @property
    def complete(self) -> bool:
        return len(self.samples) == len(self.POSES)

    def accept(self, embedding) -> tuple[str, Path | None]:
        pose = self.current_pose
        if pose is None:
            raise ValueError("All enrollment poses have already been captured")
        self.samples.append(
            EnrollmentSample(pose, embedding.vector.copy(), embedding.aligned_rgb.copy())
        )
        if self.complete:
            try:
                self.saved_path = self.service.register(
                    self.employee_id, self.name, self.samples
                )
            except Exception:
                self.samples.pop()
                raise
        return pose, self.saved_path

    def reset(self) -> None:
        self.samples.clear()
        self.employee_id = ""
        self.name = ""
        self.saved_path = None
