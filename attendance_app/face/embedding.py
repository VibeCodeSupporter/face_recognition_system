"""Model-independent face embedding interfaces and ONNX implementations."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import cv2
import numpy as np
from face.onnx_runtime import create_inference_session

_ALIGN_DEBUG_SAVE_CALLS = 0


@runtime_checkable
class FaceEmbedder(Protocol):
    """Create an L2-normalized identity vector from an aligned RGB face."""

    @property
    def embedding_size(self) -> int: ...

    def embed(self, aligned_rgb: np.ndarray) -> np.ndarray: ...


class GhostFaceNetONNXEmbedder:
    """GhostFaceNet ONNX adapter for the benchmark's 112x112 RGB model."""

    INPUT_SIZE = (112, 112)
    EXPECTED_EMBEDDING_SIZE = 512

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Face embedding ONNX file not found: {self.model_path}"
            )
        self.session = create_inference_session(self.model_path)
        inputs = self.session.get_inputs()
        outputs = self.session.get_outputs()
        if len(inputs) != 1 or len(outputs) != 1:
            raise ValueError("GhostFaceNet ONNX must have one input and one output")
        self.input = inputs[0]
        self.output = outputs[0]
        input_shape = self.input.shape
        if len(input_shape) != 4 or input_shape[1:] != [112, 112, 3]:
            raise ValueError(
                "Expected GhostFaceNet NHWC input [batch,112,112,3], "
                f"got {input_shape}"
            )
        output_shape = self.output.shape
        if len(output_shape) != 2 or output_shape[-1] not in (
            self.EXPECTED_EMBEDDING_SIZE,
            "512",
            None,
            "None",
        ):
            raise ValueError(
                f"Expected a 512-dimensional embedding output, got {output_shape}"
            )

    @property
    def embedding_size(self) -> int:
        return self.EXPECTED_EMBEDDING_SIZE

    def embed(self, aligned_rgb: np.ndarray) -> np.ndarray:
        image = np.asarray(aligned_rgb)
        if image.shape != (112, 112, 3):
            raise ValueError(f"Expected aligned RGB image (112,112,3), got {image.shape}")
        # Matches benchmark/GhostFaceNets preprocessing exactly.
        tensor = (image.astype(np.float32) - 127.5) * 0.0078125
        tensor = np.ascontiguousarray(tensor[None, ...])
        vector = np.asarray(
            self.session.run([self.output.name], {self.input.name: tensor})[0],
            dtype=np.float32,
        ).reshape(-1)
        if vector.size != self.embedding_size or not np.isfinite(vector).all():
            raise ValueError("GhostFaceNet returned an invalid embedding vector")
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-12:
            raise ValueError("GhostFaceNet returned a zero-length embedding")
        return vector / norm


def align_and_embed(
    embedder: FaceEmbedder,
    frame_bgr: np.ndarray,
    landmarks: tuple[tuple[float, float, float], ...],
) -> tuple[np.ndarray, np.ndarray]:
    """Align one detected face to ArcFace 112x112 geometry, then embed it."""
    aligned_rgb = align_face_rgb(frame_bgr, landmarks)
    return aligned_rgb, embedder.embed(aligned_rgb)


def align_face_rgb(
    frame_bgr: np.ndarray,
    landmarks: tuple[tuple[float, float, float], ...],
) -> np.ndarray:
    """Align a face, save the latest debug image, and return RGB pixels."""
    from face.alignment import align_face

    if not has_reliable_landmarks(landmarks):
        raise ValueError("Five reliable face landmarks are required for alignment")
    aligned_bgr = align_face(
        frame_bgr, [(point[0], point[1]) for point in landmarks], (112, 112)
    )
    aligned_rgb = cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB)
    global _ALIGN_DEBUG_SAVE_CALLS
    _ALIGN_DEBUG_SAVE_CALLS += 1
    if _ALIGN_DEBUG_SAVE_CALLS == 1 or _ALIGN_DEBUG_SAVE_CALLS % 30 == 0:
        debug_dir = Path(__file__).resolve().parents[1] / "data" / "aligned_inputs"
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_path = debug_dir / "latest_aligned_112.png"
        aligned_bgr = cv2.cvtColor(aligned_rgb, cv2.COLOR_RGB2BGR)
        if not cv2.imwrite(str(debug_path), aligned_bgr):
            raise OSError(f"Could not save aligned face image: {debug_path}")
    return aligned_rgb


def has_reliable_landmarks(
    landmarks: tuple[tuple[float, float, float], ...],
    minimum_visibility: float = 0.2,
) -> bool:
    """Return whether all five finite alignment points meet the visibility floor."""
    return len(landmarks) == 5 and all(
        np.isfinite(point).all() and point[2] >= minimum_visibility
        for point in landmarks
    )
