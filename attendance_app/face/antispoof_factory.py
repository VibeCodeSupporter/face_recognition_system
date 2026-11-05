"""Factory for interchangeable ONNX anti-spoofing models."""

from face.antispoof import FaceAntiSpoofDetector, MiniFASOnnxDetector


def create_antispoof_detector(
    name: str, model_path: str, logit_threshold: float = 0.0
) -> FaceAntiSpoofDetector:
    normalized_name = name.strip().lower()
    if normalized_name == "mini_fas_onnx":
        return MiniFASOnnxDetector(model_path, logit_threshold)
    raise ValueError(f"Unsupported face anti-spoof model: {name}")
