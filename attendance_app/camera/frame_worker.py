"""Camera capture and asynchronous ONNX face detection."""

import cv2
import time
from threading import Lock
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from camera.camera_manager import CameraManager
from common.face_region import crop_face_roi
from config.settings import (
    CAMERA_INDEX,
    FACE_ANTISPOOF_MODEL_PATH,
    FACE_ANTISPOOF_LOGIT_THRESHOLD,
    FACE_ANTISPOOF_NAME,
    FACE_EMBEDDER_NAME,
    FACE_EMBEDDING_MODEL_PATH,
)
from face.detector_factory import create_face_detector
from face.detector import FaceDetection
from face.embedding_factory import create_face_embedder
from face.antispoof_factory import create_antispoof_detector
from face.pipeline import FacePipeline
from face.quality_check import FaceQualityResult
from face.tracking.bytetrack import ByteTrackFaceTracker
from registration.registration_flow import RegistrationFlow, RegistrationFrameStatus
from recognition.recognition_flow import RecognitionFlow


class FrameWorker(QThread):
    frame_ready = pyqtSignal(QImage, object, object)
    camera_error = pyqtSignal(str)
    detector_ready = pyqtSignal()
    detector_error = pyqtSignal(str)
    embedding_ready = pyqtSignal(object)
    embedding_error = pyqtSignal(str)
    antispoof_result = pyqtSignal(object)
    antispoof_error = pyqtSignal(str)

    def __init__(
        self,
        camera_index: int = CAMERA_INDEX,
        parent=None,
        analysis_interval_frames: int = 10,
        registration_mode: bool = False,
        required_pose: str = "front",
    ) -> None:
        super().__init__(parent)
        self.camera = CameraManager(camera_index)
        self._running = False
        self.analysis_interval_frames = max(1, int(analysis_interval_frames))
        self.registration_mode = registration_mode
        self.required_pose = required_pose
        self._state_lock = Lock()

    def set_required_pose(self, pose_key: str) -> None:
        with self._state_lock:
            self.required_pose = pose_key

    def _get_required_pose(self) -> str:
        with self._state_lock:
            return self.required_pose

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
                    FACE_ANTISPOOF_NAME,
                    str(FACE_ANTISPOOF_MODEL_PATH),
                    FACE_ANTISPOOF_LOGIT_THRESHOLD,
                )
            except Exception as error:
                self.antispoof_error.emit(
                    f"Không khởi tạo được FAS model: {error}"
                )

        face_pipeline = (
            FacePipeline(
                face_embedder,
                anti_spoof_detector,
                FACE_EMBEDDER_NAME,
            )
            if face_embedder is not None and anti_spoof_detector is not None
            else None
        )

        self._running = True
        frame_number = 0
        last_embedding_error_frame = -90
        registration_flow = (
            RegistrationFlow(face_pipeline, self._get_required_pose())
            if self.registration_mode and face_pipeline is not None
            else None
        )
        recognition_flow = (
            RecognitionFlow(face_pipeline)
            if not self.registration_mode and face_pipeline is not None
            else None
        )
        last_preview_at = 0.0
        while self._running:
            ok, frame_bgr = self.camera.read()
            if not ok:
                self.camera_error.emit("Camera đang mở nhưng không đọc được frame.")
                break
            frame_number += 1
            pending_embedding = None

            detections: list[FaceDetection] = []
            quality_result: FaceQualityResult | RegistrationFrameStatus | None = None
            if detector is not None:
                try:
                    roi, offset_x, offset_y = crop_face_roi(frame_bgr)
                    roi_detections = detector.detect(roi)
                    if face_tracker is not None:
                        roi_detections = face_tracker.update(roi_detections)
                    detections = [
                        detection.translated(offset_x, offset_y)
                        for detection in roi_detections
                    ]
                    if len(detections) == 1:
                        if self.registration_mode:
                            detection = detections[0]
                            required_pose = self._get_required_pose()
                            if registration_flow is not None:
                                registration_flow.set_required_pose(required_pose)
                                try:
                                    frame_status, fas_result, pending_embedding = registration_flow.process(
                                        frame_bgr, detection
                                    )
                                    if fas_result is not None:
                                        self.antispoof_result.emit(fas_result)
                                except Exception as error:
                                    registration_flow.reset_candidate()
                                    frame_status = RegistrationFrameStatus(
                                        "error", False, "Lỗi xử lý khuôn mặt, đang thử lại.",
                                        None, None, None,
                                    )
                                    if frame_number - last_embedding_error_frame >= 30:
                                        self.antispoof_error.emit(f"Registration pipeline failed: {error}")
                                        last_embedding_error_frame = frame_number
                            else:
                                frame_status = RegistrationFrameStatus(
                                    "error", False, "Thiếu model FAS hoặc embedding.",
                                    None, None, None,
                                )
                            quality_result = frame_status
                        else:
                            if recognition_flow is not None:
                                try:
                                    frame_result = recognition_flow.process(
                                        frame_bgr,
                                        detections[0],
                                        frame_number=frame_number,
                                        analysis_interval_frames=self.analysis_interval_frames,
                                    )
                                    quality_result = frame_result.quality
                                    pending_embedding = frame_result.embedding
                                    if frame_result.antispoof is not None:
                                        self.antispoof_result.emit(frame_result.antispoof)
                                except Exception as error:
                                    recognition_flow.reset()
                                    if frame_number - last_embedding_error_frame >= 30:
                                        self.antispoof_error.emit(
                                            f"Recognition pipeline failed: {error}"
                                        )
                                        last_embedding_error_frame = frame_number
                    else:
                        if registration_flow is not None:
                            registration_flow.reset()
                        if recognition_flow is not None:
                            recognition_flow.reset()
                except Exception as error:
                    detector = None
                    if registration_flow is not None:
                        registration_flow.reset()
                    if recognition_flow is not None:
                        recognition_flow.reset()
                    self.detector_error.emit(f"Lỗi ONNX face detector: {error}")
            elif recognition_flow is not None:
                recognition_flow.reset()

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb.shape
            image = QImage(
                rgb.data, width, height, channels * width, QImage.Format.Format_RGB888
            ).copy()
            now = time.monotonic()
            if now - last_preview_at >= 1.0 / 15.0:
                self.frame_ready.emit(image, detections, quality_result)
                last_preview_at = now
            if pending_embedding is not None:
                self.embedding_ready.emit(pending_embedding)
            self.msleep(5)

        self.camera.close()

    def stop(self) -> None:
        self._running = False
