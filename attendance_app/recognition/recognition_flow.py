"""Per-frame liveness, quality, and embedding gates for live recognition."""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np

from config import settings
from face.antispoof import AntiSpoofResult
from face.detector import FaceDetection
from face.pipeline import (
    AlignmentError,
    EmbeddingError,
    FaceEmbedding,
    FacePipeline,
)
from face.quality_check import FaceQualityChecker, FaceQualityResult


@dataclass(frozen=True)
class RecognitionFrameResult:
    frame_id: int
    timestamp: float
    face_count: int
    outcome: str
    pose_status: str
    quality_status: str
    fas_status: str
    quality: FaceQualityResult | None
    antispoof: AntiSpoofResult | None
    embedding: FaceEmbedding | None
    error: str | None = None


class RecognitionFlow:
    """Run the ordered per-frame recognition gates with early exit."""

    def __init__(self, pipeline: FacePipeline) -> None:
        self.pipeline = pipeline
        self.quality_checker = FaceQualityChecker()

    def process(
        self,
        frame_bgr: np.ndarray,
        detection: FaceDetection,
        *,
        frame_number: int,
        timestamp: float,
    ) -> RecognitionFrameResult:
        pose = self.quality_checker.estimate_pose(
            detection.landmarks, frame_bgr.shape[1], frame_bgr.shape[0]
        )
        pose_limits = (
            settings.FACE_RECOGNITION_MAX_YAW_DEGREES,
            settings.FACE_RECOGNITION_MAX_PITCH_DEGREES,
            settings.FACE_RECOGNITION_MAX_ROLL_DEGREES,
        )
        if pose is None or any(
            abs(value) > limit for value, limit in zip(pose, pose_limits)
        ):
            return RecognitionFrameResult(
                frame_number, timestamp, 1, "POSE_FAIL", "FAIL",
                "NOT_EVALUATED", "NOT_EVALUATED", None, None, None,
            )

        quality = self.quality_checker.evaluate(
            frame_bgr, detection
        )
        if not quality.passed:
            return RecognitionFrameResult(
                frame_number, timestamp, 1, "QUALITY_FAIL", "PASS", "FAIL",
                "NOT_EVALUATED", quality, None, None,
            )

        fas_result = self.pipeline.anti_spoof.predict(frame_bgr, detection)
        if not fas_result.is_real:
            return RecognitionFrameResult(
                frame_number, timestamp, 1, "FAS_FAIL", "PASS", "PASS",
                "FAIL", quality, fas_result, None,
            )

        try:
            aligned_rgb = self.pipeline.align_detection(frame_bgr, detection)
        except AlignmentError as error:
            return RecognitionFrameResult(
                frame_number, timestamp, 1, "ALIGNMENT_FAIL", "PASS", "PASS",
                "PASS", quality, fas_result, None, str(error),
            )
        try:
            vector = self.pipeline.embed_aligned(aligned_rgb)
        except EmbeddingError as error:
            return RecognitionFrameResult(
                frame_number, timestamp, 1, "EMBEDDING_ERROR", "PASS", "PASS",
                "PASS", quality, fas_result, None, str(error),
            )
        embedding = FaceEmbedding(
            vector=vector,
            aligned_rgb=aligned_rgb,
            track_id=detection.track_id,
            model_name=self.pipeline.model_name,
            created_at=time.monotonic(),
        )
        return RecognitionFrameResult(
            frame_number, timestamp, 1, "ALL_PASS", "PASS", "PASS", "PASS",
            quality, fas_result, embedding,
        )
