"""Factory for interchangeable face embedding backends."""

from face.embedding import FaceEmbedder, GhostFaceNetONNXEmbedder


def create_face_embedder(name: str, model_path: str) -> FaceEmbedder:
    normalized_name = name.strip().lower()
    if normalized_name == "ghostfacenet_onnx":
        return GhostFaceNetONNXEmbedder(model_path)
    raise ValueError(f"Unsupported face embedder: {name}")
