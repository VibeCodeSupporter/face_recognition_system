"""Application-level bridge from embeddings to local gallery matches."""

from __future__ import annotations

import logging
from time import perf_counter

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from face.pipeline import FaceEmbedding
from recognition.recognition_service import RecognitionService

logger = logging.getLogger(__name__)


class RecognitionController(QObject):
    """Run the lightweight SQLite-backed search on its owning Qt thread."""

    result_ready = pyqtSignal(object, object)
    error = pyqtSignal(str)

    def __init__(self, service: RecognitionService, parent=None) -> None:
        super().__init__(parent)
        self.service = service

    @pyqtSlot(object)
    def identify(self, embedding: FaceEmbedding) -> None:
        started = perf_counter()
        try:
            match = self.service.identify(embedding.vector)
        except Exception as error:
            logger.exception(
                "Gallery search failed after %.2f ms",
                (perf_counter() - started) * 1000.0,
            )
            self.error.emit(f"Local vector search failed: {error}")
            return
        logger.info(
            "Gallery search completed in %.2f ms (match=%s)",
            (perf_counter() - started) * 1000.0,
            match is not None,
        )
        self.result_ready.emit(embedding, match)
