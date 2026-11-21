"""Registration-specific frame gates, kept out of the Qt presentation layer."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
import time

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
    timings_ms: dict[str, float] = field(default_factory=dict)


def _timed_call(function, *args, **kwargs):
    started = perf_counter()
    value = function(*args, **kwargs)
    return value, (perf_counter() - started) * 1000.0


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
        # Prepare the two model inputs concurrently. Model inference remains
        # ordered: embedding inference is gated on a real FAS verdict.
        self._input_executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="registration-input"
        )

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
        self, frame: np.ndarray, detection: FaceDetection, *, frame_number: int | None = None
    ) -> tuple[RegistrationFrameStatus, AntiSpoofResult | None, FaceEmbedding | None]:
        if detection.track_id is not None and detection.track_id != self.track_id:
            # A short detector/tracker interruption can assign a new ID to the
            # same person. Keep the frontal calibration for the current pose.
            # Once this pose has produced an embedding, keep its one-shot gate
            # until the UI advances the required pose.
            if not self.sample_captured:
                self.reset(clear_neutral_pose=False)
            self.track_id = detection.track_id
        if self.sample_captured and self.accepted_status is not None:
            return replace(self.accepted_status, timings_ms={}), None, None

        timings: dict[str, float] = {}
        started = perf_counter()
        pose = self.quality_checker.estimate_pose(
            detection.landmarks, frame.shape[1], frame.shape[0]
        )
        pose_ok, guidance = self.quality_checker.matches_capture_pose(
            self.required_pose,
            pose,
            self.neutral_pose if self.required_pose != "front" else None,
        )
        timings["pose_ms"] = (perf_counter() - started) * 1000.0
        yaw, pitch, roll = pose if pose is not None else (None, None, None)
        if not pose_ok:
            return RegistrationFrameStatus(
                "pose", False, guidance, yaw, pitch, roll,
                timings_ms=dict(timings),
            ), None, None

        started = perf_counter()
        quality = self.quality_checker.evaluate(
            frame, detection, registration=True, frame_id=frame_number
        )
        timings["quality_ms"] = (perf_counter() - started) * 1000.0
        if not quality.passed:
            return RegistrationFrameStatus(
                "quality", True, guidance, yaw, pitch, roll, quality=quality,
                timings_ms=dict(timings),
            ), None, None

        fas_future = self._input_executor.submit(
            _timed_call, self.pipeline.anti_spoof.prepare_inputs,
            frame, detection, frame_id=frame_number,
        )
        aligned_future = self._input_executor.submit(
            _timed_call, self.pipeline.align_detection,
            frame, detection, frame_id=frame_number,
        )
        fas_inputs, timings["fas_prepare_ms"] = fas_future.result()
        try:
            aligned_rgb, timings["alignment_ms"] = aligned_future.result()
            alignment_error = None
        except Exception as error:
            # Liveness still gets evaluated; alignment is needed only if the
            # face passes FAS and can proceed to embedding inference.
            aligned_rgb = None
            alignment_error = error

        started = perf_counter()
        fas_result = self.pipeline.anti_spoof.predict_prepared(
            fas_inputs, detection
        )
        timings["fas_infer_ms"] = (perf_counter() - started) * 1000.0
        if not fas_result.is_real:
            return RegistrationFrameStatus(
                "fas", True, guidance, yaw, pitch, roll,
                fas_real=False, timings_ms=dict(timings),
            ), fas_result, None

        if alignment_error is not None:
            raise alignment_error
        assert aligned_rgb is not None
        started = perf_counter()
        vector = self.pipeline.embed_aligned(aligned_rgb)
        timings["embedding_ms"] = (perf_counter() - started) * 1000.0
        embedding = FaceEmbedding(
            vector=vector,
            aligned_rgb=aligned_rgb,
            track_id=detection.track_id,
            model_name=self.pipeline.model_name,
            created_at=time.monotonic(),
        )
        status = RegistrationFrameStatus(
            "accepted", True, guidance, yaw, pitch, roll,
            quality=quality, fas_real=True, timings_ms=dict(timings),
        )
        self.sample_captured = True
        self.accepted_status = status
        return status, fas_result, embedding

    def close(self) -> None:
        self._input_executor.shutdown(wait=False, cancel_futures=True)
