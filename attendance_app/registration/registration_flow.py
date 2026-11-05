"""Registration-specific frame gates, kept out of the Qt presentation layer."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from face.antispoof import AntiSpoofResult
from face.detector import FaceDetection
from face.pipeline import FaceEmbedding, FacePipeline
from face.quality_check import FaceQualityChecker, FaceQualityResult


@dataclass(frozen=True)
class RegistrationFrameStatus:
    phase: str
    pose_ok: bool
    pose_guidance: str
    yaw: float | None
    pitch: float | None
    roll: float | None
    quality: FaceQualityResult | None = None
    fas_real: bool | None = None


class RegistrationFlow:
    """Gate each registration frame by pose, quality, and liveness."""

    def __init__(self, pipeline: FacePipeline, required_pose: str) -> None:
        self.pipeline = pipeline
        self.required_pose = required_pose
        self.quality_checker = FaceQualityChecker()
        self.track_id: int | None = None
        self.neutral_pose: tuple[float, float] | None = None
        self.sample_captured = False
        self.accepted_status: RegistrationFrameStatus | None = None

    def set_required_pose(self, pose: str) -> None:
        if pose != self.required_pose:
            neutral_pose = self.neutral_pose
            if (
                self.required_pose == "front"
                and self.accepted_status is not None
                and self.accepted_status.yaw is not None
                and self.accepted_status.pitch is not None
            ):
                neutral_pose = (
                    self.accepted_status.yaw,
                    self.accepted_status.pitch,
                )
            track_id = self.track_id
            self.required_pose = pose
            self.reset(clear_neutral_pose=True)
            self.track_id = track_id
            self.neutral_pose = neutral_pose

    def reset(self, *, clear_neutral_pose: bool = True) -> None:
        self.track_id = None
        if clear_neutral_pose:
            self.neutral_pose = None
        self.sample_captured = False
        self.accepted_status = None

    def process(
        self, frame: np.ndarray, detection: FaceDetection
    ) -> tuple[RegistrationFrameStatus, AntiSpoofResult | None, FaceEmbedding | None]:
        if detection.track_id is not None and detection.track_id != self.track_id:
            self.reset()
            self.track_id = detection.track_id
        if self.sample_captured and self.accepted_status is not None:
            return self.accepted_status, None, None

        pose = self.quality_checker.estimate_pose(
            detection.landmarks, frame.shape[1], frame.shape[0]
        )
        pose_ok, guidance = self.quality_checker.matches_capture_pose(
            self.required_pose,
            pose,
            self.neutral_pose if self.required_pose != "front" else None,
        )
        yaw, pitch, roll = pose if pose is not None else (None, None, None)
        if not pose_ok:
            return RegistrationFrameStatus(
                "pose", False, guidance, yaw, pitch, roll,
            ), None, None

        quality = self.quality_checker.evaluate(
            frame, detection, registration=True
        )
        if not quality.passed:
            return RegistrationFrameStatus(
                "quality", True, guidance, yaw, pitch, roll, quality=quality,
            ), None, None

        fas_result = self.pipeline.anti_spoof.predict(frame, detection)
        if not fas_result.is_real:
            return RegistrationFrameStatus(
                "fas", True, guidance, yaw, pitch, roll,
                fas_real=False,
            ), fas_result, None

        embedding = self.pipeline.embed_detection(frame, detection)
        status = RegistrationFrameStatus(
            "accepted", True, guidance, yaw, pitch, roll,
            quality=quality, fas_real=True,
        )
        self.sample_captured = True
        self.accepted_status = status
        return status, fas_result, embedding
