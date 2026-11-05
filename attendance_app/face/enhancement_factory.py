"""Factory for interchangeable face image enhancement adapters."""

from face.enhancement import FaceEnhancer, Ying2017FaceEnhancer


def create_face_enhancer(name: str) -> FaceEnhancer:
    normalized_name = name.strip().lower()
    if normalized_name in {"ying", "ying_2017", "ying_2017_caip"}:
        return Ying2017FaceEnhancer()
    raise ValueError(f"Unsupported face enhancement algorithm: {name}")
