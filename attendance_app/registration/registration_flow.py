"""Registration-specific frame gates, kept out of the Qt presentation layer."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import time

import numpy as np

from config import settings
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
    pose_count: int = 0
    fas_count: int = 0
    fas_confirmations: int = 0


class RegistrationFlow:
    """Evaluate pose stability, rolling FAS, image quality, then embedding."""

    POSE_WINDOW = settings.REGISTRATION_POSE_WINDOW
    POSE_REQUIRED = settings.REGISTRATION_POSE_REQUIRED
    FAS_WINDOW = settings.REGISTRATION_FAS_WINDOW
    FAS_CONFIRMATIONS = settings.REGISTRATION_FAS_CONFIRMATIONS
    FAS_MAX_AGE_SECONDS = settings.REGISTRATION_FAS_MAX_AGE_SECONDS

    def __init__(self, pipeline: FacePipeline, required_pose: str) -> None:
        self.pipeline = pipeline
        self.required_pose = required_pose
        self.quality_checker = FaceQualityChecker()
        self.pose_history: deque[bool] = deque(maxlen=self.POSE_WINDOW)
        self.pose_values: deque[tuple[float, float, float]] = deque(maxlen=3)
        self.fas_history: deque[AntiSpoofResult] = deque(maxlen=self.FAS_WINDOW)
        self.fas_real_streak = 0
        self.track_id: int | None = None
        self.neutral_pose: tuple[float, float] | None = None
        self.sample_captured = False
        self.accepted_status: RegistrationFrameStatus | None = None
        self._guidance_candidate = ""
        self._guidance_count = 0
        self._stable_guidance = ""

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
        self.pose_history.clear()
        self.pose_values.clear()
        self.reset_candidate()
        self.track_id = None
        if clear_neutral_pose:
            self.neutral_pose = None
        self.sample_captured = False
        self.accepted_status = None
        self._guidance_candidate = ""
        self._guidance_count = 0
        self._stable_guidance = ""

    def reset_candidate(self) -> None:
        self.fas_history.clear()
        self.fas_real_streak = 0
        self.quality_checker.reset()

    def _smooth_guidance(self, guidance: str) -> str:
        if guidance == self._guidance_candidate:
            self._guidance_count += 1
        else:
            self._guidance_candidate = guidance
            self._guidance_count = 1
        if self._guidance_count >= 3:
            self._stable_guidance = guidance
        return self._stable_guidance or guidance

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
        if pose is not None:
            self.pose_values.append(pose)
        smoothed = (
            tuple(float(value) for value in np.median(
                np.asarray(self.pose_values, dtype=np.float32), axis=0
            ))
            if self.pose_values else None
        )
        pose_ok, guidance = self.quality_checker.matches_capture_pose(
            self.required_pose,
            smoothed,
            self.neutral_pose if self.required_pose != "front" else None,
        )
        yaw, pitch, roll = smoothed if smoothed is not None else (None, None, None)
        self.pose_history.append(pose_ok)
        pose_confirmed = (
            len(self.pose_history) == self.POSE_WINDOW
            and sum(self.pose_history) >= self.POSE_REQUIRED
            and self.pose_history[-1]
        )
        if not pose_confirmed:
            self.reset_candidate()
            guidance = self._smooth_guidance(guidance)
            return RegistrationFrameStatus(
                "pose", pose_ok, guidance, yaw, pitch, roll,
                pose_count=sum(self.pose_history),
            ), None, None

        if (
            self.fas_history
            and time.monotonic() - self.fas_history[-1].created_at
            > self.FAS_MAX_AGE_SECONDS
        ):
            self.fas_history.clear()
            self.fas_real_streak = 0
        raw_fas = self.pipeline.anti_spoof.predict(frame, detection)
        self.fas_history.append(raw_fas)
        if len(self.fas_history) < self.FAS_WINDOW:
            return RegistrationFrameStatus(
                "fas", True, guidance, yaw, pitch, roll,
                fas_real=None, fas_count=len(self.fas_history),
            ), None, None

        mean_score = float(np.mean([item.logit_difference for item in self.fas_history]))
        fas_result = replace(
            raw_fas,
            is_real=mean_score >= raw_fas.logit_threshold,
            real_probability=float(np.mean([item.real_probability for item in self.fas_history])),
            spoof_probability=float(np.mean([item.spoof_probability for item in self.fas_history])),
            logit_difference=mean_score,
        )
        if not fas_result.is_real:
            self.fas_real_streak = 0
            self.quality_checker.reset()
            return RegistrationFrameStatus(
                "fas", True, guidance, yaw, pitch, roll,
                fas_real=False, fas_count=len(self.fas_history),
            ), fas_result, None

        self.fas_real_streak += 1
        if self.fas_real_streak < self.FAS_CONFIRMATIONS:
            return RegistrationFrameStatus(
                "fas", True, guidance, yaw, pitch, roll,
                fas_real=None, fas_count=len(self.fas_history),
                fas_confirmations=self.fas_real_streak,
            ), fas_result, None

        quality = self.quality_checker.evaluate(
            frame, detection, track_stability=False
        )
        if not quality.passed:
            quality = replace(
                quality, guidance=self._smooth_guidance(quality.guidance)
            )
            return RegistrationFrameStatus(
                "quality", True, guidance, yaw, pitch, roll,
                quality=quality, fas_real=True,
                fas_count=len(self.fas_history),
            ), fas_result, None

        embedding = self.pipeline.embed_detection(frame, detection)
        status = RegistrationFrameStatus(
            "accepted", True, guidance, yaw, pitch, roll,
            quality=quality, fas_real=True,
            pose_count=sum(self.pose_history), fas_count=len(self.fas_history),
        )
        self.sample_captured = True
        self.accepted_status = status
        return status, fas_result, embedding
