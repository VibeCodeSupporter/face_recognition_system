"""Camera capture and asynchronous ONNX face detection."""

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from camera.camera_manager import CameraManager
from common.face_region import crop_face_roi
from config.settings import (
    CAMERA_INDEX,
    FACE_ANTISPOOF_MODEL_PATH,
    FACE_ANTISPOOF_NAME,
    FACE_EMBEDDER_NAME,
    FACE_EMBEDDING_MODEL_PATH,
)
from face.detector_factory import create_face_detector
from face.detector import FaceDetection
from face.embedding_factory import create_face_embedder
from face.antispoof_factory import create_antispoof_detector
from face.pipeline import FacePipeline
from face.quality_check import FaceQualityChecker, FaceQualityResult
from face.tracking.bytetrack import ByteTrackFaceTracker


class FrameWorker(QThread):
    frame_ready = pyqtSignal(QImage, object, object)
    camera_error = pyqtSignal(str)
    detector_ready = pyqtSignal()
    detector_error = pyqtSignal(str)
    embedding_ready = pyqtSignal(object)
    embedding_error = pyqtSignal(str)
    antispoof_result = pyqtSignal(object)
    antispoof_error = pyqtSignal(str)

    def __init__(self, camera_index: int = CAMERA_INDEX, parent=None) -> None:
        super().__init__(parent)
        self.camera = CameraManager(camera_index)
        self._running = False
        self.quality_checker = FaceQualityChecker()

    def run(self) -> None:
        if not self.camera.open():
            self.camera_error.emit(f"Không mở được camera (index {self.camera.camera_index}).")
            self.camera.close()
            return

        try:
            detector = create_face_detector()
        except Exception as error:
            detector = None
            face_tracker = None
            self.detector_error.emit(f"Không khởi tạo được ONNX face detector: {error}")
        else:
            try:
                face_tracker = ByteTrackFaceTracker()
            except Exception:
                # Keep camera detection usable if the optional tracking adapter fails.
                face_tracker = None
            self.detector_ready.emit()

        face_embedder = None
        if FACE_EMBEDDING_MODEL_PATH is None:
            self.embedding_error.emit(
                "Chưa cấu hình FACE_EMBEDDING_MODEL trong .env."
            )
        else:
            try:
                face_embedder = create_face_embedder(
                    FACE_EMBEDDER_NAME, str(FACE_EMBEDDING_MODEL_PATH)
                )
            except Exception as error:
                self.embedding_error.emit(f"Không khởi tạo được face embedder: {error}")

        anti_spoof_detector = None
        if FACE_ANTISPOOF_MODEL_PATH is None:
            self.antispoof_error.emit(
                "Chưa cấu hình FACE_ANTISPOOF_MODEL trong .env."
            )
        else:
            try:
                anti_spoof_detector = create_antispoof_detector(
                    FACE_ANTISPOOF_NAME, str(FACE_ANTISPOOF_MODEL_PATH)
                )
            except Exception as error:
                self.antispoof_error.emit(
                    f"Không khởi tạo được FAS model: {error}"
                )

        face_pipeline = (
            FacePipeline(face_embedder, anti_spoof_detector, FACE_EMBEDDER_NAME)
            if face_embedder is not None and anti_spoof_detector is not None
            else None
        )

        self._running = True
        frame_number = 0
        last_embedding_track: int | None = None
        last_embedding_error_frame = -90
        while self._running:
            ok, frame_bgr = self.camera.read()
            if not ok:
                self.camera_error.emit("Camera đang mở nhưng không đọc được frame.")
                break
            frame_number += 1

            detections: list[FaceDetection] = []
            quality_result: FaceQualityResult | None = None
            if detector is not None:
                roi, offset_x, offset_y = crop_face_roi(frame_bgr)
                try:
                    roi_detections = detector.detect(roi)
                    if face_tracker is not None:
                        roi_detections = face_tracker.update(roi_detections)
                    detections = [
                        detection.translated(offset_x, offset_y)
                        for detection in roi_detections
                    ]
                    if len(detections) == 1:
                        quality_result = self.quality_checker.evaluate(
                            frame_bgr, detections[0]
                        )
                        track_id = detections[0].track_id
                        track_changed = (
                            track_id is not None and track_id != last_embedding_track
                        )
                        if (
                            face_pipeline is not None
                            and quality_result.passed
                            and quality_result.stable
                            and (track_changed or frame_number % 10 == 0)
                        ):
                            last_embedding_track = track_id
                            try:
                                analysis = face_pipeline.analyze_detection(
                                    frame_bgr, detections[0]
                                )
                                self.antispoof_result.emit(analysis.anti_spoof)
                                if analysis.embedding is not None:
                                    self.embedding_ready.emit(analysis.embedding)
                                last_embedding_track = track_id
                            except Exception as error:
                                if frame_number - last_embedding_error_frame >= 90:
                                    self.antispoof_error.emit(
                                        f"Lỗi trong pipeline FAS/embedding: {error}"
                                    )
                                    last_embedding_error_frame = frame_number
                    else:
                        self.quality_checker.reset()
                        last_embedding_track = None
                except Exception as error:
                    detector = None
                    self.quality_checker.reset()
                    self.detector_error.emit(f"Lỗi ONNX face detector: {error}")
            else:
                self.quality_checker.reset()

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb.shape
            image = QImage(
                rgb.data, width, height, channels * width, QImage.Format.Format_RGB888
            ).copy()
            self.frame_ready.emit(image, detections, quality_result)
            self.msleep(5)

        self.camera.close()

    def stop(self) -> None:
        self._running = False

