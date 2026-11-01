"""Local offline face matching against the enrolled FAISS gallery."""

from __future__ import annotations

import numpy as np

from storage.vector_store import FaceMatch, VectorStore


class RecognitionService:
    def __init__(self, vector_store: VectorStore) -> None:
        self.vector_store = vector_store

    def identify(self, vector: np.ndarray) -> FaceMatch | None:
        return self.vector_store.search(vector)
