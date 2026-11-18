"""Factory for interchangeable ONNX anti-spoofing models."""

from pathlib import Path

from face.antispoof import FaceAntiSpoofDetector, SilentFaceOnnxDetector


def create_antispoof_detector(
    name: str, model_paths: list[str | Path], real_threshold: float = 0.5
) -> FaceAntiSpoofDetector:
    normalized_name = name.strip().lower()
    if normalized_name == "silentface_onnx":
        return SilentFaceOnnxDetector(model_paths, real_threshold)
    raise ValueError(f"Unsupported face anti-spoof model: {name}")
