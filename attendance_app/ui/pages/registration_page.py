"""Guided five-pose offline face enrollment page."""

from __future__ import annotations

import time
from collections import deque

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from camera.frame_worker import FrameWorker, RegistrationFrameStatus
from face.quality_check import FaceQualityChecker
from registration.registration_service import EnrollmentSample, RegistrationService
from ui.widgets.camera_view import CameraView


class RegistrationPage(QWidget):
    back_requested = pyqtSignal()

    POSES = (
        ("front", "Nhìn thẳng", "Nhìn vào camera, giữ đầu tự nhiên."),
        ("left", "Quay sang trái", "Quay mặt nhẹ sang trái rồi giữ yên."),
        ("right", "Quay sang phải", "Quay mặt nhẹ sang phải rồi giữ yên."),
        ("down", "Cúi nhẹ", "Cúi mặt nhẹ xuống rồi giữ yên."),
        ("up", "Ngửa nhẹ", "Ngửa mặt nhẹ lên rồi giữ yên."),
    )
    # Pose estimates are approximate; accept a 3-of-4 frame majority while
    # requiring the latest frame to remain in the requested direction.
    POSE_STABLE_FRAMES = 4
    POSE_MATCHES_REQUIRED = 3

    def __init__(
        self, registration_service: RegistrationService, parent=None
    ) -> None:
        super().__init__(parent)
        self.registration_service = registration_service
        self.worker: FrameWorker | None = None
        self.latest_quality = None
        self.latest_embedding = None
        self.latest_antispoof = None
        self.latest_fas_real: bool | None = None
        self.latest_pose: tuple[float | None, float | None, float | None] | None = None
        self.current_track_id: int | None = None
        self.current_face_count = 0
        self.samples: list[EnrollmentSample] = []
        self.enrollment_started = False
        self.step_started_at = time.monotonic()
        self.capture_confirmation_until = 0.0
        self._pose_history: deque[bool] = deque(maxlen=self.POSE_STABLE_FRAMES)
        self._build_ui()
        self._refresh_step()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        heading = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel("Register a face")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Enroll five pose embeddings to the device's local gallery")
        subtitle.setObjectName("mutedText")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        heading.addLayout(title_block)
        heading.addStretch()
        self.back_button = QPushButton("Back to recognition")
        self.back_button.setObjectName("primaryButton")
        self.back_button.clicked.connect(self._back_to_recognition)
        heading.addWidget(self.back_button)
        layout.addLayout(heading)

        identity_form = QFormLayout()
        self.employee_id = QLineEdit()
        self.employee_id.setPlaceholderText("e.g. E001")
        self.employee_name = QLineEdit()
        self.employee_name.setPlaceholderText("Employee name")
        self.employee_id.returnPressed.connect(self._check_employee_id)
        self.employee_name.returnPressed.connect(self._start_enrollment)
        identity_form.addRow("Employee ID", self.employee_id)
        identity_form.addRow("Name", self.employee_name)
        layout.addLayout(identity_form)

        self.camera_view = CameraView()
        layout.addWidget(self.camera_view, 1)

        self.step_label = QLabel()
        self.step_label.setObjectName("faceGuidance")
        self.step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.step_label)
        self.instruction = QLabel()
        self.instruction.setObjectName("mutedText")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.instruction)
        self.progress = QProgressBar()
        self.progress.setRange(0, len(self.POSES))
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.guidance = QLabel("Đưa một khuôn mặt vào vùng giữa.")
        self.guidance.setObjectName("faceGuidance")
        self.guidance.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.guidance)
        self.quality_details = QLabel("")
        self.quality_details.setObjectName("mutedText")
        self.quality_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.quality_details)
        self.embedding_status = QLabel("Đang chờ embedding ổn định.")
        self.embedding_status.setObjectName("mutedText")
        self.embedding_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.embedding_status)
        self.fas_status = QLabel("FAS: waiting for model")
        self.fas_status.setObjectName("mutedText")
        self.fas_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.fas_status)

        actions = QHBoxLayout()
        actions.addStretch()
        self.start_button = QPushButton("Bắt đầu đăng ký")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self._start_enrollment)
        actions.addWidget(self.start_button)
        self.reset_button = QPushButton("Reset enrollment")
        self.reset_button.clicked.connect(self._reset_enrollment)
        actions.addWidget(self.reset_button)
        layout.addLayout(actions)

    def start_camera(self) -> None:
        if not self.enrollment_started:
            self.camera_view.setText("Nhập ID và tên rồi nhấn Enter để bắt đầu đăng ký.")
            return
        self._start_camera_worker()

    def _start_camera_worker(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self.latest_quality = None
        self.latest_embedding = None
        self.latest_antispoof = None
        self.latest_pose = None
        self.current_track_id = None
        self.step_started_at = time.monotonic()
        required_pose = self.POSES[len(self.samples)][0]
        self.worker = FrameWorker(
            analysis_interval_frames=3,
            registration_mode=True,
            required_pose=required_pose,
        )
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.camera_error.connect(self._camera_error)
        self.worker.detector_error.connect(self._detector_error)
        self.worker.embedding_ready.connect(self._on_embedding)
        self.worker.embedding_error.connect(self._on_embedding_error)
        self.worker.antispoof_result.connect(self._on_antispoof_result)
        self.worker.antispoof_error.connect(self._on_antispoof_error)
        self.worker.start()

    def stop_camera(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)

    def _refresh_step(self, captured_pose: str | None = None) -> None:
        self._pose_history.clear()
        self.latest_embedding = None
        self.latest_antispoof = None
        self.latest_fas_real = None
        self.latest_quality = None
        self.latest_pose = None
        self.progress.setValue(len(self.samples))
        if len(self.samples) >= len(self.POSES):
            self.step_label.setText("Đã thu đủ 5 tư thế")
            self.instruction.setText("Đang lưu embedding vào local gallery…")
            return
        _, label, instruction = self.POSES[len(self.samples)]
        if self.worker is not None:
            self.worker.set_required_pose(self.POSES[len(self.samples)][0])
        self.step_label.setText(
            f"Tư thế {len(self.samples) + 1}/{len(self.POSES)} · {label}"
        )
        self.instruction.setText(instruction)
        if captured_pose:
            self.capture_confirmation_until = time.monotonic() + 0.75
            self.embedding_status.setText(
                f"OK · Đã lưu mẫu {captured_pose}; chuyển sang tư thế {label}."
            )
        else:
            self.embedding_status.setText("Chờ ảnh đạt chất lượng, đúng tư thế và ổn định để tự chụp.")

    def _employee_id_exists(self, employee_id: str) -> bool | None:
        try:
            return self.registration_service.employee_id_exists(employee_id)
        except Exception as error:
            QMessageBox.critical(self, "Employee lookup failed", str(error))
            return None

    def _check_employee_id(self) -> None:
        employee_id = self.employee_id.text().strip()
        if not employee_id:
            self.guidance.setText("Enter an employee ID first.")
            self.employee_id.setFocus()
            return
        exists = self._employee_id_exists(employee_id)
        if exists is None:
            return
        if exists:
            QMessageBox.warning(
                self, "Employee ID already registered",
                f"Employee ID {employee_id} already exists. Enter a different ID.",
            )
            self.employee_id.setFocus()
            self.employee_id.selectAll()
            return
        self.employee_name.setFocus()

    def _start_enrollment(self) -> None:
        if self.enrollment_started:
            return
        employee_id = self.employee_id.text().strip()
        if employee_id:
            exists = self._employee_id_exists(employee_id)
            if exists is None:
                return
            if exists:
                QMessageBox.warning(
                    self, "Employee ID already registered",
                    f"Employee ID {employee_id} already exists. Enter a different ID.",
                )
                self.employee_id.setFocus()
                self.employee_id.selectAll()
                return
        if not self.employee_id.text().strip() or not self.employee_name.text().strip():
            self.guidance.setText("Nhập mã nhân viên và tên, sau đó nhấn Enter hoặc Bắt đầu đăng ký.")
            if not self.employee_id.text().strip():
                self.employee_id.setFocus()
            else:
                self.employee_name.setFocus()
            return
        self.enrollment_started = True
        self.employee_id.setEnabled(False)
        self.employee_name.setEnabled(False)
        self.start_button.setEnabled(False)
        self.step_started_at = time.monotonic()
        self._refresh_step()
        self.guidance.setText("Đang khởi tạo camera và model…")
        self.camera_view.setText("Đang khởi tạo camera và model…")
        self._start_camera_worker()

    def _on_frame(self, image, detections, quality_result) -> None:
        self.camera_view.set_frame(image)
        self.camera_view.set_detections(detections)
        status = quality_result if isinstance(quality_result, RegistrationFrameStatus) else None
        if status is None:
            self.latest_quality = quality_result
        else:
            # A previous embedding must never satisfy the current sample after
            # a new pipeline attempt starts. The worker emits a fresh embedding
            # after this frame_ready signal when all gates pass.
            if status.phase in {"pose", "fas", "quality"}:
                self.latest_embedding = None
            if status.quality is not None:
                self.latest_quality = status.quality
        if status is not None:
            self.latest_pose = (status.yaw, status.pitch, status.roll)
            self.latest_fas_real = status.fas_real
        self.current_face_count = len(detections)
        self.current_track_id = detections[0].track_id if len(detections) == 1 else None
        if not detections:
            self._pose_history.clear()
            self.latest_antispoof = None
            self.latest_fas_real = None
            self.latest_embedding = None
            self.latest_quality = None
            self.latest_pose = None
            self.fas_status.setText("FAS: waiting for one face")
            self.guidance.setText("Đưa một khuôn mặt vào vùng giữa.")
            self.quality_details.clear()
        elif len(detections) > 1:
            self._pose_history.clear()
            self.latest_antispoof = None
            self.latest_fas_real = None
            self.latest_embedding = None
            self.latest_quality = None
            self.latest_pose = None
            self.fas_status.setText("FAS: paused · multiple faces in zone")
            self.guidance.setText("Chỉ để một người trong vùng nhận diện.")
            self.quality_details.clear()
        elif quality_result is not None:
            pose_ok = status.pose_ok if status is not None else True
            pose_guidance = (
                status.pose_guidance
                if status is not None
                else quality_result.guidance
            )
            self._pose_history.append(pose_ok)
            if not self._pose_is_confirmed():
                self.latest_embedding = None
            if not self.employee_id.text().strip() or not self.employee_name.text().strip():
                self.guidance.setText("Nhập mã nhân viên và tên để bắt đầu đăng ký.")
            elif not pose_ok:
                self.latest_embedding = None
                self.latest_quality = None
                self.guidance.setText(pose_guidance)
            elif not self._pose_is_confirmed():
                self.guidance.setText(
                    self._pose_confirmation_guidance(
                        status.yaw if status else quality_result.yaw,
                        status.pitch if status else quality_result.pitch,
                    )
                )
            elif status is not None and status.quality is None:
                if (
                    status.phase == "fas"
                    and status.fas_real is False
                ):
                    self.guidance.setText("FAS báo spoof; vui lòng dùng khuôn mặt thật.")
                elif status.phase == "fas" and status.fas_real is None:
                    self.guidance.setText("Đang xác nhận FAS trên vài frame; giữ nguyên tư thế.")
                elif status.phase == "pose":
                    self.guidance.setText("Góc đã đạt; đang chờ lượt xử lý kế tiếp.")
                else:
                    self.guidance.setText("Góc đạt; FAS đã kiểm tra, đang chờ quality.")
            elif not self.latest_quality.passed or not self.latest_quality.stable:
                self.guidance.setText(
                    self.latest_quality.guidance
                    if not self.latest_quality.passed
                    else "Đúng góc rồi; giữ yên để ổn định ảnh trước khi tự chụp."
                )
            else:
                self.guidance.setText("Đang xác nhận ảnh, giữ nguyên tư thế…")
            pose_details = (
                f"Pose: yaw {status.yaw:+.0f}°, pitch {status.pitch:+.0f}°"
                if status is not None and status.yaw is not None and status.pitch is not None
                else ""
            )
            quality_details = (
                self.latest_quality.details if self.latest_quality is not None else ""
            )
            self.quality_details.setText(" · ".join(part for part in (pose_details, quality_details) if part))
        else:
            self._pose_history.clear()
            self.latest_embedding = None
            self.guidance.setText("Đang kiểm tra FAS trên ảnh gốc.")
            self.quality_details.clear()
        self._maybe_auto_capture()

    def _on_embedding(self, result) -> None:
        self.latest_embedding = result
        if len(self.samples) < len(self.POSES):
            self.embedding_status.setText(
                f"Đã tạo embedding · {result.vector.size} chiều; đang chờ đủ điều kiện tự capture."
            )
        self._maybe_auto_capture()

    def _on_embedding_error(self, message: str) -> None:
        self.embedding_status.setText(f"Embedding chưa sẵn sàng: {message}")
        self.guidance.setText("Chưa tạo được embedding; vui lòng giữ nguyên tư thế để thử lại.")
        self._maybe_auto_capture()

    def _on_antispoof_result(self, result) -> None:
        self.latest_antispoof = result
        self.latest_fas_real = result.is_real
        verdict = "Real" if result.is_real else "Possible spoof"
        self.fas_status.setText(
            f"FAS: {verdict} · score {result.logit_difference:+.2f} "
            f"(threshold {result.logit_threshold:+.2f})"
        )
        if not result.is_real:
            self.latest_embedding = None
            self.latest_quality = None
        self._maybe_auto_capture()

    def _on_antispoof_error(self, message: str) -> None:
        self.latest_antispoof = None
        self.latest_fas_real = None
        self.latest_embedding = None
        self.latest_quality = None
        self.fas_status.setText(f"Pipeline chưa hoàn tất · {message}")
        self.guidance.setText("Chưa hoàn tất xử lý; vui lòng giữ nguyên tư thế để thử lại.")
        self._maybe_auto_capture()

    def _pose_is_confirmed(self) -> bool:
        return (
            len(self._pose_history) == self.POSE_STABLE_FRAMES
            and self._pose_history[-1]
            and sum(self._pose_history) >= self.POSE_MATCHES_REQUIRED
        )

    def _pose_confirmation_guidance(
        self, yaw: float | None, pitch: float | None
    ) -> str:
        pose_key, label, _ = self.POSES[len(self.samples)]
        if pose_key in {"left", "right"}:
            angle = yaw
            axis = "yaw"
        elif pose_key in {"down", "up"}:
            angle = pitch
            axis = "pitch"
        else:
            return "Đang xác nhận tư thế chính diện…"
        angle_text = f"{angle:+.0f}°" if angle is not None else "?"
        matches = sum(self._pose_history)
        return (
            f"Đã nhận góc {label} ({axis} {angle_text}); giữ yên "
            f"để xác nhận {matches}/{self.POSE_MATCHES_REQUIRED} frame."
        )

    def _maybe_auto_capture(self) -> None:
        if len(self.samples) >= len(self.POSES):
            return
        if time.monotonic() < self.capture_confirmation_until:
            return
        if not self.enrollment_started:
            self.embedding_status.setText("Nhập ID và tên, sau đó nhấn Enter hoặc Bắt đầu đăng ký.")
            return
        embedding_is_current = (
            self.latest_embedding is not None
            and self.latest_embedding.created_at >= self.step_started_at
            and (
                self.current_track_id is None
                or self.latest_embedding.track_id is None
                or self.current_track_id == self.latest_embedding.track_id
            )
        )
        pose_is_ready = (
            self.latest_pose is not None
            and FaceQualityChecker.matches_capture_pose(
                self.POSES[len(self.samples)][0], self.latest_pose
            )[0]
            and self._pose_is_confirmed()
        )
        quality_is_ready = (
            self.latest_quality is not None
            and self.latest_quality.passed
            and self.latest_quality.stable
        )
        if not pose_is_ready:
            if self.current_face_count == 0:
                reason = "Đang chờ một khuôn mặt trong vùng."
            elif self.current_face_count > 1:
                reason = "Chỉ để một khuôn mặt trong vùng."
            elif self.latest_fas_real is False:
                reason = "FAS báo spoof; vui lòng dùng khuôn mặt thật."
            elif self.latest_pose is None:
                reason = "Đã thấy khuôn mặt; chưa xác định được góc, hãy nhìn rõ vào camera."
            else:
                pose_key = self.POSES[len(self.samples)][0]
                angle_ok, angle_guidance = FaceQualityChecker.matches_capture_pose(
                    pose_key, self.latest_pose
                )
                if not angle_ok:
                    reason = angle_guidance
                elif self.latest_fas_real is False:
                    reason = "FAS báo spoof; vui lòng dùng khuôn mặt thật."
                else:
                    reason = self._pose_confirmation_guidance(
                        self.latest_pose[0], self.latest_pose[1]
                    )
            self.embedding_status.setText(f"Đang chờ: {reason}")
            return
        if not quality_is_ready:
            if self.latest_quality is None:
                if self.current_face_count == 0:
                    reason = "Đang chờ một khuôn mặt trong vùng."
                elif self.current_face_count > 1:
                    reason = "Chỉ để một khuôn mặt trong vùng."
                elif self.latest_fas_real is False:
                    reason = "FAS báo spoof; cần một ảnh thật trước khi tiếp tục."
                elif self.latest_fas_real is None:
                    reason = "Đã thấy khuôn mặt; đang kiểm tra FAS trên ảnh gốc."
                else:
                    reason = "FAS báo Real; đang chờ quality hoàn tất."
            elif not self.latest_quality.passed:
                reason = self.latest_quality.guidance
            elif not self.latest_quality.stable:
                reason = "Pose đạt · giữ yên để ổn định chất lượng ảnh."
            else:
                reason = "Đang chờ quality đạt."
            self.embedding_status.setText(f"Đang chờ: {reason}")
            return
        if not embedding_is_current:
            self.embedding_status.setText("Tư thế đạt · đang chờ embedding mới của khuôn mặt này.")
            return
        # FrameWorker only emits an embedding when the paired FAS result is
        # Real, so requiring a second timestamp pairing here can stall capture.

        employee_id = self.employee_id.text().strip()
        employee_name = self.employee_name.text().strip()
        pose_key = self.POSES[len(self.samples)][0]
        self.samples.append(
            EnrollmentSample(
                pose_key,
                self.latest_embedding.vector.copy(),
                self.latest_embedding.aligned_rgb.copy(),
            )
        )
        self.step_started_at = time.monotonic()
        if len(self.samples) == len(self.POSES):
            self.embedding_status.setText(f"OK · Đã lưu mẫu {pose_key}; đang lưu hồ sơ.")
            self._save_enrollment(employee_id, employee_name)
        else:
            self._refresh_step(captured_pose=pose_key)

    def _save_enrollment(self, employee_id: str, name: str) -> None:
        try:
            image_dir = self.registration_service.register(
                employee_id, name, self.samples
            )
        except Exception as error:
            self.samples.pop()
            self.step_started_at = time.monotonic()
            self.latest_embedding = None
            QMessageBox.warning(self, "Registration failed", str(error))
            self._refresh_step()
            self.guidance.setText(
                f"Chưa lưu được hồ sơ: {error}. Hãy kiểm tra ID hoặc đặt lại đăng ký."
            )
            self.embedding_status.setText("Đăng ký chưa hoàn tất; mẫu cuối chưa được lưu.")
            return
        QMessageBox.information(
            self,
            "Registration complete",
            f"{name} ({employee_id}) was saved locally with five embeddings.\n"
            f"Aligned images: {image_dir}",
        )
        self.samples.clear()
        self.employee_id.clear()
        self.employee_name.clear()
        self.enrollment_started = False
        self.employee_id.setEnabled(True)
        self.employee_name.setEnabled(True)
        self.start_button.setEnabled(True)
        self._refresh_step()
        self.back_requested.emit()

    def _reset_enrollment(self) -> None:
        self.stop_camera()
        self.samples.clear()
        self.latest_embedding = None
        self.latest_antispoof = None
        self.latest_fas_real = None
        self.enrollment_started = False
        self.employee_id.setEnabled(True)
        self.employee_name.setEnabled(True)
        self.start_button.setEnabled(True)
        self.step_started_at = time.monotonic()
        self.embedding_status.setText("Đang chờ embedding ổn định.")
        self._refresh_step()
        self.camera_view.setText("Nhập ID và tên rồi nhấn Enter để bắt đầu đăng ký.")

    def _camera_error(self, message: str) -> None:
        self.guidance.setText(message)

    def _back_to_recognition(self) -> None:
        self.stop_camera()
        self.samples.clear()
        self.enrollment_started = False
        self.employee_id.setEnabled(True)
        self.employee_name.setEnabled(True)
        self.start_button.setEnabled(True)
        self.back_requested.emit()

    def _detector_error(self, message: str) -> None:
        self.guidance.setText(f"Face detector unavailable: {message}")

