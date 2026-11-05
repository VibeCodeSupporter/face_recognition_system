"""Per-frame liveness, quality, and embedding gates for live recognition."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace

import numpy as np

from config import settings
from face.antispoof import AntiSpoofResult
from face.detector import FaceDetection
from face.embedding import has_reliable_landmarks
from face.pipeline import FaceEmbedding, FacePipeline
from face.quality_check import FaceQualityChecker, FaceQualityResult


@dataclass(frozen=True)
class RecognitionFrameResult:
    quality: FaceQualityResult | None
    antispoof: AntiSpoofResult | None
    embedding: FaceEmbedding | None


class RecognitionFlow:
    """Aggregate FAS per track and create one embedding from an eligible frame."""

    def __init__(self, pipeline: FacePipeline) -> None:
        self.pipeline = pipeline
        self.quality_checker = FaceQualityChecker()
        self.fas_history: deque[AntiSpoofResult] = deque(
            maxlen=settings.RECOGNITION_FAS_WINDOW
        )
        self.track_id: int | None = None
        self.pose_limits = (
            settings.FACE_RECOGNITION_MAX_YAW_DEGREES,
            settings.FACE_RECOGNITION_MAX_PITCH_DEGREES,
            settings.FACE_RECOGNITION_MAX_ROLL_DEGREES,
        )

    def reset(self) -> None:
        self.fas_history.clear()
        self.quality_checker.reset()
        self.track_id = None

    def process(
        self,
        frame_bgr: np.ndarray,
        detection: FaceDetection,
        *,
        frame_number: int,
        analysis_interval_frames: int,
    ) -> RecognitionFrameResult:
        if detection.track_id is not None and detection.track_id != self.track_id:
            self.reset()
            self.track_id = detection.track_id

        raw_fas = self.pipeline.anti_spoof.predict(frame_bgr, detection)
        self.fas_history.append(raw_fas)
        if len(self.fas_history) < self.fas_history.maxlen:
            return RecognitionFrameResult(None, None, None)

        mean_score = float(
            np.mean([result.logit_difference for result in self.fas_history])
        )
        fas_result = replace(
            raw_fas,
            is_real=mean_score >= raw_fas.logit_threshold,
            real_probability=float(
                np.mean([result.real_probability for result in self.fas_history])
            ),
            spoof_probability=float(
                np.mean([result.spoof_probability for result in self.fas_history])
            ),
            logit_difference=mean_score,
        )
        if not fas_result.is_real:
            self.quality_checker.reset()
            return RecognitionFrameResult(None, fas_result, None)

        quality = self.quality_checker.evaluate(
            frame_bgr, detection, pose_limits=self.pose_limits
        )
        if (
            not quality.passed
            or not quality.stable
            or frame_number % analysis_interval_frames != 0
            or not has_reliable_landmarks(detection.landmarks)
        ):
            return RecognitionFrameResult(quality, fas_result, None)

        embedding = self.pipeline.embed_detection(frame_bgr, detection)
        return RecognitionFrameResult(quality, fas_result, embedding)
