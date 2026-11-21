"""Camera capture and asynchronous ONNX face detection."""

import cv2
import csv
import logging
import time
from collections import Counter
from threading import Lock
from time import perf_counter
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from camera.camera_manager import CameraManager
from common.face_region import face_roi_bounds
from config import settings
from config.settings import (
    CAMERA_INDEX,
    FACE_ANTISPOOF_MODEL_PATHS,
    FACE_ANTISPOOF_REAL_THRESHOLD,
    FACE_ANTISPOOF_NAME,
    FACE_EMBEDDER_NAME,
    FACE_EMBEDDING_MODEL_PATH,
)
from face.detector_factory import create_face_detector
from face.detector import FaceDetection
from face.debug_images import save_module_input
from face.embedding_factory import create_face_embedder
from face.antispoof_factory import create_antispoof_detector
from face.pipeline import FacePipeline
from face.quality_check import FaceQualityResult
from face.tracking.bytetrack import ByteTrackFaceTracker
from registration.registration_flow import RegistrationFlow, RegistrationFrameStatus
from recognition.recognition_flow import RecognitionFlow

logger = logging.getLogger(__name__)


class PreviewWorker(QThread):
    """Forward newly captured frames to the UI without waiting for inference."""

    frame_ready = pyqtSignal(QImage)

    def __init__(self, camera: CameraManager, parent=None) -> None:
        super().__init__(parent)
        self.camera = camera
        self._running = True

    def run(self) -> None:
        last_frame_id = -1
        while self._running:
            frame, frame_id, _captured_at = self.camera.latest()
            if frame is not None and frame_id != last_frame_id:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channels = rgb.shape
                self.frame_ready.emit(QImage(
                    rgb.data, width, height, channels * width,
                    QImage.Format.Format_RGB888,
                ).copy())
                last_frame_id = frame_id
            self.msleep(2)

    def stop(self) -> None:
        self._running = False


class FrameWorker(QThread):
    frame_ready = pyqtSignal(object, object, object)
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
        self.preview_worker = PreviewWorker(self.camera)
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

        self.preview_worker.start()

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
        if not FACE_ANTISPOOF_MODEL_PATHS:
            self.antispoof_error.emit(
                "Chưa cấu hình FACE_ANTISPOOF_MODEL trong .env."
            )
        else:
            try:
                anti_spoof_detector = create_antispoof_detector(
                    FACE_ANTISPOOF_NAME,
                    FACE_ANTISPOOF_MODEL_PATHS,
                    FACE_ANTISPOOF_REAL_THRESHOLD,
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
        status_file = None
        status_writer = None
        pose_file = None
        pose_writer = None
        if settings.PIPELINE_CSV_LOG_ENABLED:
            debug_dir = settings.APP_ROOT / "data" / "pipeline_debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            status_path = debug_dir / "frame_status.csv"
            write_header = not status_path.exists() or status_path.stat().st_size == 0
            status_file = status_path.open("a", newline="", encoding="utf-8")
            status_writer = csv.DictWriter(status_file, fieldnames=[
                "frame_id", "captured_monotonic", "outcome", "detect_status", "face_count",
                "track_id", "pose_status", "quality_status", "fas_status",
                "alignment_status", "embedding_status",
                "yaw", "pitch", "roll", "quality_blur", "quality_brightness",
                "real_probability", "spoof_probability", "guidance", "error",
            ])
            if write_header:
                status_writer.writeheader()
            if self.registration_mode:
                pose_path = debug_dir / "pose_debug.csv"
                pose_fields = [
                    "frame_id", "captured_monotonic", "required_pose", "phase",
                    "outcome", "face_count", "track_id", "pose_pass", "guidance",
                    "yaw", "pitch", "roll", "neutral_yaw", "neutral_pitch",
                    "delta_yaw", "delta_pitch", "directed_delta", "cross_axis_delta",
                    "directed_min", "directed_max", "cross_axis_limit",
                    "frame_width", "frame_height", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
                    "right_eye_x", "right_eye_y", "left_eye_x", "left_eye_y",
                    "nose_x", "nose_y", "right_mouth_x", "right_mouth_y",
                    "left_mouth_x", "left_mouth_y",
                ]
                pose_header = not pose_path.exists() or pose_path.stat().st_size == 0
                pose_file = pose_path.open("a", newline="", encoding="utf-8")
                pose_writer = csv.DictWriter(pose_file, fieldnames=pose_fields)
                if pose_header:
                    pose_writer.writeheader()
        stats_started_at = time.monotonic()
        stats_camera_frames = stats_worker_frames = stats_dropped_frames = 0
        stats_detect_calls = stats_recognition_calls = stats_embeddings = 0
        stats_gate_skips = Counter()
        stats_outcomes = Counter()
        timing_totals = Counter()
        timing_counts = Counter()
        timing_maxima: dict[str, float] = {}
        previous_frame_id = None
        while self._running:
            ok, frame_bgr, frame_id, captured_at = self.camera.read()
            if not ok:
                self.camera_error.emit("Camera đang mở nhưng không đọc được frame.")
                break
            processing_started = perf_counter()
            sequence_delta = (
                1 if previous_frame_id is None
                else max(1, frame_id - previous_frame_id)
            )
            previous_frame_id = frame_id
            stats_camera_frames += sequence_delta
            stats_worker_frames += 1
            stats_dropped_frames += max(0, sequence_delta - 1)
            pending_embedding = None
            frame_timings_ms: dict[str, float] = {}
            frame_fas_result = None
            frame_error = ""
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
                    stats_detect_calls += 1
                    stage_started = perf_counter()
                    full_frame_detections = detector.detect(frame_bgr, frame_id=frame_id)
                    frame_timings_ms["detect_ms"] = (perf_counter() - stage_started) * 1000.0
                    frame_height, frame_width = frame_bgr.shape[:2]
                    roi_left, roi_top, roi_right, roi_bottom = face_roi_bounds(
                        frame_width, frame_height
                    )
                    margin_x = round((roi_right - roi_left) * 0.01)
                    margin_y = round((roi_bottom - roi_top) * 0.01)
                    safe_left, safe_top = roi_left + margin_x, roi_top + margin_y
                    safe_right, safe_bottom = roi_right - margin_x, roi_bottom - margin_y
                    stage_started = perf_counter()
                    detections = [
                        detection
                        for detection in full_frame_detections
                        if detection.bbox[0] >= safe_left
                        and detection.bbox[1] >= safe_top
                        and detection.bbox[2] <= safe_right
                        and detection.bbox[3] <= safe_bottom
                    ]
                    frame_timings_ms["roi_filter_ms"] = (perf_counter() - stage_started) * 1000.0
                    if face_tracker is not None:
                        stage_started = perf_counter()
                        detections = face_tracker.update(detections)
                        frame_timings_ms["tracker_ms"] = (perf_counter() - stage_started) * 1000.0
                    if len(detections) == 1:
                        frame_outcome = "ERROR"
                        if self.registration_mode:
                            detection = detections[0]
                            required_pose = self._get_required_pose()
                            if registration_flow is not None:
                                registration_flow.set_required_pose(required_pose)
                                try:
                                    frame_status, fas_result, pending_embedding = registration_flow.process(
                                        frame_bgr, detection, frame_number=frame_id
                                    )
                                    frame_outcome = {
                                        "pose": "POSE_FAIL",
                                        "quality": "QUALITY_FAIL",
                                        "fas": "FAS_FAIL",
                                        "accepted": "ALL_PASS",
                                        "error": "ERROR",
                                    }.get(frame_status.phase, "ERROR")
                                    frame_timings_ms.update(frame_status.timings_ms)
                                    if fas_result is not None:
                                        frame_fas_result = fas_result
                                        self.antispoof_result.emit(fas_result)
                                except Exception as error:
                                    frame_outcome = "ERROR"
                                    frame_error = str(error)
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
                                    frame_timings_ms.update(frame_result.timings_ms)
                                    quality_result = frame_result.quality
                                    pending_embedding = frame_result.embedding
                                    if frame_result.error:
                                        frame_error = frame_result.error
                                        self.pipeline_error.emit(
                                            f"{frame_result.outcome}: {frame_result.error}"
                                        )
                                    if frame_result.antispoof is not None:
                                        frame_fas_result = frame_result.antispoof
                                        self.antispoof_result.emit(frame_result.antispoof)
                                except Exception as error:
                                    frame_outcome = "ERROR"
                                    frame_error = str(error)
                                    if frame_id - last_embedding_error_frame >= 30:
                                        self.antispoof_error.emit(
                                            f"Recognition pipeline failed: {error}"
                                        )
                                        last_embedding_error_frame = frame_id
                    else:
                        frame_outcome = "MULTIPLE_FACES" if len(detections) > 1 else "NO_FACE"
                        if registration_flow is not None:
                            # Keep the registration pose baseline and step when
                            # a face briefly leaves the ROI or detection drops.
                            if not registration_flow.sample_captured:
                                registration_flow.reset(clear_neutral_pose=False)
                except Exception as error:
                    detector = None
                    frame_outcome = "ERROR"
                    frame_error = str(error)
                    if registration_flow is not None:
                        if not registration_flow.sample_captured:
                            registration_flow.reset(clear_neutral_pose=False)
                    self.detector_error.emit(f"Lỗi ONNX face detector: {error}")
            elif detector is None:
                frame_outcome = "ERROR"

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
            if settings.FRAME_DEBUG_SAVE_IMAGES:
                save_module_input("camera", frame_id, frame_bgr, variant="input")
            if status_writer is not None and status_file is not None:
                status_writer.writerow(_frame_status_row(
                    frame_id, captured_at, frame_outcome, detections, quality_result,
                    frame_fas_result, frame_error,
                ))
                status_file.flush()
                if pose_writer is not None and pose_file is not None:
                    pose_writer.writerow(_pose_debug_row(
                        frame_id, captured_at, frame_outcome, detections,
                        quality_result, registration_flow, frame_bgr.shape,
                    ))
                    pose_file.flush()
            self.frame_ready.emit(None, detections, quality_result)
            if pending_embedding is not None:
                if not self.registration_mode:
                    with self._recognition_gate_lock:
                        self._recognition_in_flight = True
                stats_embeddings += 1
                self.embedding_ready.emit(pending_embedding)
            frame_timings_ms["worker_frame_ms"] = (
                perf_counter() - processing_started
            ) * 1000.0
            for name, duration in frame_timings_ms.items():
                timing_totals[name] += duration
                timing_counts[name] += 1
                timing_maxima[name] = max(timing_maxima.get(name, 0.0), duration)
            now = time.monotonic()
            stats_elapsed = now - stats_started_at
            if stats_elapsed >= settings.FRAME_WORKER_STATS_INTERVAL_SECONDS:
                logger.info(
                    "Frame stats %.2fs: camera=%.1f fps worker=%.1f fps "
                    "dropped=%.1f fps detect=%.1f/s recognition=%.1f/s "
                    "embeddings=%.1f/s gate_skips=%s outcomes=%s "
                    "stage_avg_ms=%s stage_max_ms=%s",
                    stats_elapsed,
                    stats_camera_frames / stats_elapsed,
                    stats_worker_frames / stats_elapsed,
                    stats_dropped_frames / stats_elapsed,
                    stats_detect_calls / stats_elapsed,
                    stats_recognition_calls / stats_elapsed,
                    stats_embeddings / stats_elapsed,
                    dict(stats_gate_skips),
                    dict(stats_outcomes),
                    {name: round(total / timing_counts[name], 2) for name, total in timing_totals.items()},
                    {name: round(duration, 2) for name, duration in timing_maxima.items()},
                )
                stats_started_at = now
                stats_camera_frames = stats_worker_frames = stats_dropped_frames = 0
                stats_detect_calls = stats_recognition_calls = stats_embeddings = 0
                stats_gate_skips.clear()
                stats_outcomes.clear()
                timing_totals.clear()
                timing_counts.clear()
                timing_maxima.clear()
            self.msleep(5)

        self.preview_worker.stop()
        self.preview_worker.wait(1000)
        if registration_flow is not None:
            registration_flow.close()
        if status_file is not None:
            status_file.close()
        if pose_file is not None:
            pose_file.close()
        self.camera.close()

    def stop(self) -> None:
        self._running = False


def _pose_debug_row(frame_id, captured_at, outcome, detections, status, flow, frame_shape):
    registration_status = (
        status if isinstance(status, RegistrationFrameStatus) else None
    )
    detection = detections[0] if len(detections) == 1 else None
    neutral_yaw, neutral_pitch = (
        flow.neutral_pose or (None, None)
    ) if flow is not None else (None, None)
    yaw = registration_status.yaw if registration_status else None
    pitch = registration_status.pitch if registration_status else None
    roll = registration_status.roll if registration_status else None
    delta_yaw = yaw - neutral_yaw if yaw is not None and neutral_yaw is not None else None
    delta_pitch = pitch - neutral_pitch if pitch is not None and neutral_pitch is not None else None

    pose_name = flow.required_pose if flow is not None else ""
    directed_delta = None
    cross_axis_delta = None
    directed_min = None
    directed_max = None
    cross_axis_limit = None
    checker = flow.quality_checker if flow is not None else None
    if checker is not None and pose_name in {"left", "right"}:
        directed_delta = delta_yaw * (1.0 if pose_name == "left" else -1.0) if delta_yaw is not None else None
        cross_axis_delta = abs(delta_pitch) if delta_pitch is not None else None
        directed_min = checker.TURN_MIN_ANGLE
        directed_max = checker.TURN_MAX_ANGLE
        cross_axis_limit = checker.CROSS_AXIS_MAX_ANGLE
    elif checker is not None and pose_name in {"up", "down"}:
        directed_delta = delta_pitch * (1.0 if pose_name == "down" else -1.0) if delta_pitch is not None else None
        cross_axis_delta = abs(delta_yaw) if delta_yaw is not None else None
        directed_min = (settings.FACE_POSE_DOWN_MIN_ANGLE if pose_name == "down" else settings.FACE_POSE_UP_MIN_ANGLE)
        directed_max = checker.PITCH_MAX_ANGLE
        cross_axis_limit = checker.CROSS_AXIS_MAX_ANGLE

    row = {
        "frame_id": frame_id,
        "captured_monotonic": f"{captured_at:.6f}" if captured_at is not None else "",
        "required_pose": pose_name,
        "phase": registration_status.phase if registration_status else "",
        "outcome": outcome,
        "face_count": len(detections),
        "track_id": detection.track_id if detection else "",
        "pose_pass": registration_status.pose_ok if registration_status else "",
        "guidance": registration_status.pose_guidance if registration_status else "",
        "yaw": _csv_number(yaw),
        "pitch": _csv_number(pitch),
        "roll": _csv_number(roll),
        "neutral_yaw": _csv_number(neutral_yaw),
        "neutral_pitch": _csv_number(neutral_pitch),
        "delta_yaw": _csv_number(delta_yaw),
        "delta_pitch": _csv_number(delta_pitch),
        "directed_delta": _csv_number(directed_delta),
        "cross_axis_delta": _csv_number(cross_axis_delta),
        "directed_min": _csv_number(directed_min),
        "directed_max": _csv_number(directed_max),
        "cross_axis_limit": _csv_number(cross_axis_limit),
        "frame_width": frame_shape[1],
        "frame_height": frame_shape[0],
    }
    if detection is not None:
        x1, y1, x2, y2 = detection.bbox
        row.update({
            "bbox_x1": _csv_number(x1),
            "bbox_y1": _csv_number(y1),
            "bbox_x2": _csv_number(x2),
            "bbox_y2": _csv_number(y2),
        })
        landmark_names = (
            "right_eye", "left_eye", "nose", "right_mouth", "left_mouth"
        )
        for name, point in zip(landmark_names, detection.landmarks):
            row[f"{name}_x"] = _csv_number(point[0])
            row[f"{name}_y"] = _csv_number(point[1])
    return row

def _frame_status_row(frame_id, captured_at, outcome, detections, status, fas_result, error):
    quality = (
        status.quality if isinstance(status, RegistrationFrameStatus)
        else status if isinstance(status, FaceQualityResult) else None
    )
    if isinstance(status, RegistrationFrameStatus):
        pose_status = (
            "NOT_EVALUATED" if status.phase == "error"
            else "PASS" if status.pose_ok else "FAIL"
        )
        quality_status = (
            "NOT_EVALUATED" if status.phase in ("pose", "error")
            else "PASS" if status.phase in ("fas", "accepted")
            else "FAIL"
        )
        fas_status = (
            "PASS" if status.fas_real else "FAIL" if status.fas_real is False
            else "NOT_EVALUATED"
        )
    else:
        pose_status = "FAIL" if outcome == "POSE_FAIL" else "PASS" if quality else "NOT_EVALUATED"
        quality_status = "FAIL" if outcome == "QUALITY_FAIL" else "PASS" if quality else "NOT_EVALUATED"
        fas_status = "FAIL" if outcome == "FAS_FAIL" else "PASS" if fas_result and fas_result.is_real else "NOT_EVALUATED"
    if outcome == "ERROR":
        detect_status = "ERROR"
    elif len(detections) == 0:
        detect_status = "NO_FACE"
    elif len(detections) == 1:
        detect_status = "ONE_FACE"
    else:
        detect_status = "MULTIPLE_FACES"
    alignment_status = (
        "FAIL" if outcome == "ALIGNMENT_FAIL"
        else "PASS" if outcome in ("ALL_PASS", "EMBEDDING_ERROR")
        else "NOT_EVALUATED"
    )
    embedding_status = (
        "PASS" if outcome == "ALL_PASS"
        else "ERROR" if outcome == "EMBEDDING_ERROR"
        else "NOT_EVALUATED"
    )
    return {
        "frame_id": frame_id,
        "captured_monotonic": f"{captured_at:.6f}" if captured_at is not None else "",
        "outcome": outcome,
        "detect_status": detect_status,
        "face_count": len(detections),
        "track_id": detections[0].track_id if len(detections) == 1 else "",
        "pose_status": pose_status,
        "quality_status": quality_status,
        "fas_status": fas_status,
        "alignment_status": alignment_status,
        "embedding_status": embedding_status,
        "yaw": _csv_number(
            status.yaw if isinstance(status, RegistrationFrameStatus)
            else quality.yaw if quality else None
        ),
        "pitch": _csv_number(
            status.pitch if isinstance(status, RegistrationFrameStatus)
            else quality.pitch if quality else None
        ),
        "roll": _csv_number(
            status.roll if isinstance(status, RegistrationFrameStatus)
            else quality.roll if quality else None
        ),
        "quality_blur": f"{quality.blur_score:.2f}" if quality else "",
        "quality_brightness": f"{quality.brightness:.2f}" if quality else "",
        "real_probability": f"{fas_result.real_probability:.6f}" if fas_result else "",
        "spoof_probability": f"{fas_result.spoof_probability:.6f}" if fas_result else "",
        "guidance": (
            status.pose_guidance if isinstance(status, RegistrationFrameStatus)
            else quality.guidance if quality else ""
        ),
        "error": error,
    }


def _csv_number(value):
    return f"{value:.2f}" if value is not None else ""
