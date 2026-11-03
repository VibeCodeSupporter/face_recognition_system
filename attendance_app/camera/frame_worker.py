"""Camera capture and asynchronous ONNX face detection."""

import cv2
import numpy as np
from dataclasses import dataclass, replace
from collections import deque
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
from face.antispoof import AntiSpoofResult
from face.pipeline import FacePipeline
from face.quality_check import FaceQualityChecker, FaceQualityResult
from face.tracking.bytetrack import ByteTrackFaceTracker

@dataclass(frozen=True)
class RegistrationFrameStatus:
    """Pose gate and any later registration checks performed on this frame."""

    phase: str
    pose_ok: bool
    pose_guidance: str
    yaw: float | None
    pitch: float | None
    roll: float | None
    quality: FaceQualityResult | None = None
    fas_real: bool | None = None


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
        self.quality_checker = FaceQualityChecker()
        self.analysis_interval_frames = max(1, int(analysis_interval_frames))
        self.registration_mode = registration_mode
        self.required_pose = required_pose
        self._state_lock = Lock()
        self._pose_history: deque[bool] = deque(maxlen=4)

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
        last_embedding_track: int | None = None
        last_embedding_error_frame = -90
        active_pose: str | None = None
        pose_values: deque[tuple[float, float, float]] = deque(maxlen=3)
        fas_history: deque[AntiSpoofResult] = deque(maxlen=3)
        active_fas_track: int | None = None
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
                            if (
                                detection.track_id is not None
                                and detection.track_id != active_fas_track
                            ):
                                active_fas_track = detection.track_id
                                fas_history.clear()
                                pose_values.clear()
                                self._pose_history.clear()
                            # FAS always sees the untouched camera frame.
                            fas_result = None
                            if face_pipeline is not None:
                                try:
                                    raw_fas_result = face_pipeline.anti_spoof.predict(
                                        frame_bgr, detection
                                    )
                                    fas_history.append(raw_fas_result)
                                    if len(fas_history) >= 3:
                                        average_score = float(np.mean(
                                            [item.logit_difference for item in fas_history]
                                        ))
                                        fas_result = replace(
                                            raw_fas_result,
                                            is_real=average_score >= raw_fas_result.logit_threshold,
                                            real_probability=float(np.mean(
                                                [item.real_probability for item in fas_history]
                                            )),
                                            spoof_probability=float(np.mean(
                                                [item.spoof_probability for item in fas_history]
                                            )),
                                            logit_difference=average_score,
                                        )
                                        self.antispoof_result.emit(fas_result)
                                except Exception as error:
                                    if frame_number - last_embedding_error_frame >= 30:
                                        self.antispoof_error.emit(
                                            f"FAS failed on camera frame: {error}"
                                        )
                                        last_embedding_error_frame = frame_number

                            pose = self.quality_checker.estimate_pose(
                                detection.landmarks,
                                frame_bgr.shape[1],
                                frame_bgr.shape[0],
                            )
                            required_pose = self._get_required_pose()
                            if required_pose != active_pose:
                                active_pose = required_pose
                                self._pose_history.clear()
                                pose_values.clear()
                                self.quality_checker.reset()
                                last_embedding_track = None
                            if pose is not None:
                                pose_values.append(pose)
                            smoothed_pose = (
                                tuple(float(value) for value in np.median(
                                    np.asarray(pose_values, dtype=np.float32), axis=0
                                ))
                                if pose_values
                                else None
                            )
                            pose_ok, pose_guidance = (
                                self.quality_checker.matches_capture_pose(
                                    required_pose, smoothed_pose
                                )
                            )
                            yaw, pitch, roll = (
                                smoothed_pose if smoothed_pose is not None else (None, None, None)
                            )
                            frame_status = RegistrationFrameStatus(
                                phase="pose",
                                pose_ok=pose_ok,
                                pose_guidance=pose_guidance,
                                yaw=yaw,
                                pitch=pitch,
                                roll=roll,
                                fas_real=fas_result.is_real if fas_result is not None else None,
                            )
                            self._pose_history.append(pose_ok)
                            pose_confirmed = (
                                len(self._pose_history) == 4
                                and sum(self._pose_history) >= 3
                                and self._pose_history[-1]
                            )
                            if fas_result is None or not fas_result.is_real:
                                frame_status = RegistrationFrameStatus(
                                    phase="fas",
                                    pose_ok=pose_ok,
                                    pose_guidance=pose_guidance,
                                    yaw=yaw,
                                    pitch=pitch,
                                    roll=roll,
                                    fas_real=fas_result.is_real if fas_result is not None else None,
                                )
                                self.quality_checker.reset()
                                last_embedding_track = detection.track_id
                            elif not pose_ok:
                                self.quality_checker.reset()
                                last_embedding_track = None
                            else:
                                if not pose_confirmed:
                                    self.quality_checker.reset()
                                should_check_quality = pose_confirmed and (
                                    frame_number % self.analysis_interval_frames == 0
                                )
                                if should_check_quality and face_pipeline is not None:
                                    try:
                                        frame_status = RegistrationFrameStatus(
                                            phase="quality",
                                            pose_ok=True,
                                            pose_guidance=pose_guidance,
                                            yaw=yaw,
                                            pitch=pitch,
                                            roll=roll,
                                            fas_real=True,
                                        )
                                        checked_quality = self.quality_checker.evaluate(
                                            frame_bgr, detection
                                        )
                                        frame_status = RegistrationFrameStatus(
                                            phase="quality",
                                            pose_ok=True,
                                            pose_guidance=pose_guidance,
                                            yaw=yaw,
                                            pitch=pitch,
                                            roll=roll,
                                            quality=checked_quality,
                                            fas_real=True,
                                        )
                                        if (
                                            checked_quality.passed
                                            and checked_quality.stable
                                        ):
                                            pending_embedding = face_pipeline.embed_detection(
                                                frame_bgr, detection
                                            )
                                        last_embedding_track = detection.track_id
                                    except Exception as error:
                                        if frame_number - last_embedding_error_frame >= 30:
                                            self.antispoof_error.emit(
                                                f"Quality/embedding failed: {error}"
                                            )
                                            last_embedding_error_frame = frame_number
                            quality_result = frame_status
                            # Registration has an explicit staged pipeline above.
                        else:
                            detection = detections[0]
                            fas_result = None
                            if face_pipeline is not None:
                                try:
                                    # FAS must inspect the original camera pixels.
                                    fas_result = face_pipeline.anti_spoof.predict(
                                        frame_bgr, detection
                                    )
                                    self.antispoof_result.emit(fas_result)
                                except Exception as error:
                                    if frame_number - last_embedding_error_frame >= 90:
                                        self.antispoof_error.emit(
                                            f"FAS failed on camera frame: {error}"
                                        )
                                        last_embedding_error_frame = frame_number

                            if fas_result is None or not fas_result.is_real:
                                quality_result = None
                                self.quality_checker.reset()
                                last_embedding_track = None
                            else:
                                quality_result = self.quality_checker.evaluate(
                                    frame_bgr, detection
                                )
                                track_id = detection.track_id
                                if (
                                    face_pipeline is not None
                                    and quality_result.passed
                                    and quality_result.stable
                                    and frame_number % self.analysis_interval_frames == 0
                                ):
                                    try:
                                        pending_embedding = face_pipeline.embed_detection(
                                            frame_bgr, detection
                                        )
                                        last_embedding_track = track_id
                                    except Exception as error:
                                        if frame_number - last_embedding_error_frame >= 90:
                                            self.antispoof_error.emit(
                                                f"Embedding failed: {error}"
                                            )
                                            last_embedding_error_frame = frame_number
                    else:
                        if self.registration_mode:
                            self._pose_history.clear()
                            pose_values.clear()
                            fas_history.clear()
                            active_fas_track = None
                        self.quality_checker.reset()
                        last_embedding_track = None
                except Exception as error:
                    detector = None
                    if self.registration_mode:
                        self._pose_history.clear()
                        pose_values.clear()
                        fas_history.clear()
                        active_fas_track = None
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
            if pending_embedding is not None:
                self.embedding_ready.emit(pending_embedding)
            self.msleep(5)

        self.camera.close()

    def stop(self) -> None:
        self._running = False
