"""Face enhancement, anti-spoof, and embedding orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np

from face.detector import FaceDetection
from face.embedding import FaceEmbedder, align_face_rgb
from face.antispoof import AntiSpoofResult, FaceAntiSpoofDetector


class AlignmentError(RuntimeError):
    """The face landmarks could not produce a usable aligned crop."""


class EmbeddingError(RuntimeError):
    """The embedding model failed to process an aligned face."""


@dataclass(frozen=True)
class FaceEmbedding:
    """One aligned face and its normalized identity feature vector."""

    vector: np.ndarray
    aligned_rgb: np.ndarray
    track_id: int | None
    model_name: str
    created_at: float


class FacePipeline:
    """Run FAS and embedding on caller-selected pixels after face detection."""

    def __init__(
        self,
        embedder: FaceEmbedder,
        anti_spoof: FaceAntiSpoofDetector,
        model_name: str,
    ) -> None:
        self.embedder = embedder
        self.anti_spoof = anti_spoof
        self.model_name = model_name

    def embed_detection(
        self, frame_bgr: np.ndarray, detection: FaceDetection
    ) -> FaceEmbedding:
        aligned_rgb = self.align_detection(frame_bgr, detection)
        vector = self.embed_aligned(aligned_rgb)
        return FaceEmbedding(
            vector=vector,
            aligned_rgb=aligned_rgb,
            track_id=detection.track_id,
            model_name=self.model_name,
            created_at=time.monotonic(),
        )

    @staticmethod
    def align_detection(
        frame_bgr: np.ndarray, detection: FaceDetection
    ) -> np.ndarray:
        try:
            return align_face_rgb(frame_bgr, detection.landmarks)
        except Exception as error:
            raise AlignmentError(str(error)) from error

    def embed_aligned(self, aligned_rgb: np.ndarray) -> np.ndarray:
        try:
            return self.embedder.embed(aligned_rgb)
        except Exception as error:
            raise EmbeddingError(str(error)) from error
