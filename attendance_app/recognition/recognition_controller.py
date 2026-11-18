"""Application-level bridge from embeddings to local gallery matches."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from face.pipeline import FaceEmbedding
from recognition.recognition_service import RecognitionService


class RecognitionController(QObject):
    """Run the lightweight SQLite-backed search on its owning Qt thread."""

    result_ready = pyqtSignal(object, object)
    error = pyqtSignal(str)

    def __init__(self, service: RecognitionService, parent=None) -> None:
        super().__init__(parent)
        self.service = service

    @pyqtSlot(object)
    def identify(self, embedding: FaceEmbedding) -> None:
        try:
            match = self.service.identify(embedding.vector)
        except Exception as error:
            self.error.emit(f"Local vector search failed: {error}")
            return
        self.result_ready.emit(embedding, match)
