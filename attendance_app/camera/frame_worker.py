"""Camera capture and asynchronous ONNX face detection."""

import cv2
import logging
import time
from collections import Counter
from threading import Lock
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from camera.camera_manager import CameraManager
from common.face_region import crop_face_roi
from config import settings
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

logger = logging.getLogger(__name__)


class FrameWorker(QThread):
    frame_ready = pyqtSignal(QImage, object, object)
    camera_error = pyqtSignal(str)
    detector_ready = pyqtSignal()
    detector_error = pyqtSignal(str)
    embedding_ready = pyqtSignal(object)
    embedding_error = pyqtSignal(str)
    pipeline_error = pyqtSignal(str)
    antispoof_result = pyqtSignal(object)
    antispoof_error = pyqtSignal(str)
    guidance_result = pyqtSignal(object)

    def __init__(
        self,
        camera_index: int = CAMERA_INDEX,
        parent=None,
        registration_mode: bool = False,
        required_pose: str = "front",
    ) -> None:
        super().__init__(parent)
        self.camera = CameraManager(camera_index)
        self._running = False
        self.registration_mode = registration_mode
        self.required_pose = required_pose
        self._state_lock = Lock()
        self._recognition_gate_lock = Lock()
        self._recognition_in_flight = False
        self._recognition_cooldown_until = 0.0

    def complete_recognition(self, success: bool, cooldown_seconds: float) -> None:
        """Release the worker gate and start a pause after a successful match."""
        with self._recognition_gate_lock:
            self._recognition_in_flight = False
            if success:
                self._recognition_cooldown_until = (
                    time.monotonic() + max(0.0, cooldown_seconds)
                )

    def _recognition_gate_status(self) -> str | None:
        with self._recognition_gate_lock:
            if time.monotonic() < self._recognition_cooldown_until:
                return "SUCCESS_COOLDOWN"
            if self._recognition_in_flight:
                return "MATCH_PENDING"
        return None

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
        stats_started_at = time.monotonic()
        stats_camera_frames = stats_worker_frames = stats_dropped_frames = 0
        stats_detect_calls = stats_recognition_calls = stats_embeddings = 0
        stats_gate_skips = Counter()
        stats_outcomes = Counter()
        previous_frame_id = None
        while self._running:
            ok, frame_bgr, frame_id, captured_at = self.camera.read()
            if not ok:
                self.camera_error.emit("Camera đang mở nhưng không đọc được frame.")
                break
            sequence_delta = (
                1 if previous_frame_id is None
                else max(1, frame_id - previous_frame_id)
            )
            previous_frame_id = frame_id
            stats_camera_frames += sequence_delta
            stats_worker_frames += 1
            stats_dropped_frames += max(0, sequence_delta - 1)
            pending_embedding = None
            frame_outcome = "NO_FACE"

            detections: list[FaceDetection] = []
            quality_result: FaceQualityResult | RegistrationFrameStatus | None = None
            recognition_gate_status = (
                self._recognition_gate_status()
                if not self.registration_mode else None
            )
            if recognition_gate_status:
                frame_outcome = recognition_gate_status
                stats_gate_skips[recognition_gate_status] += 1
            elif detector is not None:
                try:
                    roi, offset_x, offset_y = crop_face_roi(frame_bgr)
                    stats_detect_calls += 1
                    roi_detections = detector.detect(roi)
                    if face_tracker is not None:
                        roi_detections = face_tracker.update(roi_detections)
                    detections = [
                        detection.translated(offset_x, offset_y)
                        for detection in roi_detections
                    ]
                    if len(detections) == 1:
                        frame_outcome = "ERROR"
                        if self.registration_mode:
                            detection = detections[0]
                            required_pose = self._get_required_pose()
                            if registration_flow is not None:
                                registration_flow.set_required_pose(required_pose)
                                try:
                                    frame_status, fas_result, pending_embedding = registration_flow.process(
                                        frame_bgr, detection
                                    )
                                    frame_outcome = {
                                        "pose": "POSE_FAIL",
                                        "quality": "QUALITY_FAIL",
                                        "fas": "FAS_FAIL",
                                        "accepted": "ALL_PASS",
                                        "error": "ERROR",
                                    }.get(frame_status.phase, "ERROR")
                                    if fas_result is not None:
                                        self.antispoof_result.emit(fas_result)
                                except Exception as error:
                                    frame_outcome = "ERROR"
                                    frame_status = RegistrationFrameStatus(
                                        "error", False, "Lỗi xử lý khuôn mặt, đang thử lại.",
                                        None, None, None,
                                    )
                                    if frame_id - last_embedding_error_frame >= 30:
                                        self.antispoof_error.emit(f"Registration pipeline failed: {error}")
                                        last_embedding_error_frame = frame_id
                            else:
                                frame_status = RegistrationFrameStatus(
                                    "error", False, "Thiếu model FAS hoặc embedding.",
                                    None, None, None,
                                )
                            quality_result = frame_status
                        else:
                            if recognition_flow is not None:
                                stats_recognition_calls += 1
                                try:
                                    frame_result = recognition_flow.process(
                                        frame_bgr,
                                        detections[0],
                                        frame_number=frame_id,
                                        timestamp=captured_at,
                                    )
                                    frame_outcome = frame_result.outcome
                                    quality_result = frame_result.quality
                                    pending_embedding = frame_result.embedding
                                    if frame_result.error:
                                        self.pipeline_error.emit(
                                            f"{frame_result.outcome}: {frame_result.error}"
                                        )
                                    if frame_result.antispoof is not None:
                                        self.antispoof_result.emit(frame_result.antispoof)
                                except Exception as error:
                                    frame_outcome = "ERROR"
                                    if frame_id - last_embedding_error_frame >= 30:
                                        self.antispoof_error.emit(
                                            f"Recognition pipeline failed: {error}"
                                        )
                                        last_embedding_error_frame = frame_id
                    else:
                        frame_outcome = "MULTIPLE_FACES" if len(detections) > 1 else "NO_FACE"
                        if registration_flow is not None:
                            registration_flow.reset()
                except Exception as error:
                    detector = None
                    frame_outcome = "ERROR"
                    if registration_flow is not None:
                        registration_flow.reset()
                    self.detector_error.emit(f"Lỗi ONNX face detector: {error}")
            elif detector is None:
                frame_outcome = "ERROR"

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb.shape
            image = QImage(
                rgb.data, width, height, channels * width, QImage.Format.Format_RGB888
            ).copy()
            now = time.monotonic()
            stats_outcomes[frame_outcome] += 1
            track_id = detections[0].track_id if len(detections) == 1 else None
            guidance_message = None
            if isinstance(quality_result, RegistrationFrameStatus):
                if quality_result.phase == "pose":
                    guidance_message = quality_result.pose_guidance
                elif quality_result.phase == "quality" and quality_result.quality:
                    guidance_message = quality_result.quality.guidance
                elif quality_result.phase == "fas":
                    guidance_message = "Không xác nhận được khuôn mặt thật; vui lòng thử lại."
                elif quality_result.phase == "error":
                    guidance_message = quality_result.pose_guidance
            elif isinstance(quality_result, FaceQualityResult):
                guidance_message = quality_result.guidance
            self.guidance_result.emit(
                (frame_id, now, frame_outcome, track_id, guidance_message)
            )
            if now - last_preview_at >= 1.0 / 15.0:
                self.frame_ready.emit(image, detections, quality_result)
                last_preview_at = now
            if pending_embedding is not None:
                if not self.registration_mode:
                    with self._recognition_gate_lock:
                        self._recognition_in_flight = True
                stats_embeddings += 1
                self.embedding_ready.emit(pending_embedding)
            stats_elapsed = now - stats_started_at
            if stats_elapsed >= settings.FRAME_WORKER_STATS_INTERVAL_SECONDS:
                logger.info(
                    "Frame stats %.2fs: camera=%.1f fps worker=%.1f fps "
                    "dropped=%.1f fps detect=%.1f/s recognition=%.1f/s "
                    "embeddings=%.1f/s gate_skips=%s outcomes=%s",
                    stats_elapsed,
                    stats_camera_frames / stats_elapsed,
                    stats_worker_frames / stats_elapsed,
                    stats_dropped_frames / stats_elapsed,
                    stats_detect_calls / stats_elapsed,
                    stats_recognition_calls / stats_elapsed,
                    stats_embeddings / stats_elapsed,
                    dict(stats_gate_skips),
                    dict(stats_outcomes),
                )
                stats_started_at = now
                stats_camera_frames = stats_worker_frames = stats_dropped_frames = 0
                stats_detect_calls = stats_recognition_calls = stats_embeddings = 0
                stats_gate_skips.clear()
                stats_outcomes.clear()
            self.msleep(5)

        self.camera.close()

    def stop(self) -> None:
        self._running = False
