from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from camera.frame_worker import FrameWorker
from registration.registration_flow import RegistrationFrameStatus
from registration.registration_session import RegistrationSession
from registration.registration_service import RegistrationService
from ui.widgets.camera_view import CameraView


class RegistrationPage(QWidget):
    """Qt presentation for the registration flow; capture gates live elsewhere."""

    back_requested = pyqtSignal()

    def __init__(self, registration_service: RegistrationService, parent=None) -> None:
        super().__init__(parent)
        self.registration_service = registration_service
        self.session = RegistrationSession(registration_service)
        self.worker: FrameWorker | None = None
        self.enrollment_started = False
        self._fas_display_candidate: bool | None = None
        self._fas_display_count = 0
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
        self.progress.setRange(0, len(self.session.POSES))
        layout.addWidget(self.progress)

        self.guidance = QLabel("Đưa một khuôn mặt vào vùng giữa.")
        self.guidance.setObjectName("faceGuidance")
        self.guidance.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.guidance)
        self.quality_details = QLabel("")
        self.quality_details.setObjectName("mutedText")
        self.quality_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.quality_details)
        self.embedding_status = QLabel("Đang chờ enrollment.")
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
        pose = self.session.current_pose
        if pose is None:
            return
        self.worker = FrameWorker(registration_mode=True, required_pose=pose)
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
        self.progress.setValue(len(self.session.samples))
        self._fas_display_candidate = None
        self._fas_display_count = 0
        self.fas_status.setText("FAS: waiting for pose confirmation")
        if self.session.complete:
            self.step_label.setText("Đã thu đủ 5 tư thế")
            self.instruction.setText("Đang lưu embedding vào local gallery…")
            return
        _, label, instruction = self.session.POSES[len(self.session.samples)]
        self.step_label.setText(
            f"Tư thế {len(self.session.samples) + 1}/{len(self.session.POSES)} · {label}"
        )
        self.instruction.setText(instruction)
        self.embedding_status.setText(
            f"Đã ghi mẫu {captured_pose}; chuyển sang {label}." if captured_pose
            else "Đang chờ ảnh đạt chất lượng để tự chụp."
        )

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
        name = self.employee_name.text().strip()
        if not employee_id or not name:
            self.guidance.setText("Nhập mã nhân viên và tên để bắt đầu đăng ký.")
            (self.employee_id if not employee_id else self.employee_name).setFocus()
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
        self.enrollment_started = True
        self.session.begin(employee_id, name)
        self.employee_id.setEnabled(False)
        self.employee_name.setEnabled(False)
        self.start_button.setEnabled(False)
        self.guidance.setText("Đang khởi tạo camera và model…")
        self.camera_view.setText("Đang khởi tạo camera và model…")
        self._start_camera_worker()

    def _on_frame(self, image, detections, result) -> None:
        self.camera_view.set_frame(image)
        self.camera_view.set_detections(detections)
        if not detections:
            self.guidance.setText("Đưa một khuôn mặt vào vùng giữa.")
            self.quality_details.clear()
            self.fas_status.setText("FAS: waiting for one face")
            return
        if len(detections) > 1:
            self.guidance.setText("Chỉ để một người trong vùng nhận diện.")
            self.quality_details.clear()
            self.fas_status.setText("FAS: paused · multiple faces in zone")
            return
        if not isinstance(result, RegistrationFrameStatus):
            self.guidance.setText("Đang phân tích khuôn mặt…")
            return

        if result.phase == "pose":
            guidance = result.pose_guidance
            if result.pose_ok:
                guidance = f"{guidance} Đang xác nhận tư thế ({result.pose_count}/4)."
            self.guidance.setText(guidance)
        elif result.phase == "fas":
            if result.fas_real is False:
                self.guidance.setText("FAS chưa xác nhận khuôn mặt thật; đang thử frame mới.")
            else:
                if result.fas_count < 3:
                    self.guidance.setText(
                        f"Pose đạt; đang lấy mẫu FAS ({result.fas_count}/3)."
                    )
                    self.fas_status.setText(f"FAS: collecting {result.fas_count}/3")
                else:
                    self.guidance.setText(
                        f"Đang xác nhận điểm FAS trung bình ({result.fas_confirmations}/2)."
                    )
                    self.fas_status.setText(
                        f"FAS: confirming mean ({result.fas_confirmations}/2)"
                    )
        elif result.phase == "quality" and result.quality is not None:
            self.guidance.setText(result.quality.guidance)
        elif result.phase == "accepted":
            self.guidance.setText("Ảnh đạt; đang ghi mẫu đăng ký.")
        elif result.phase == "error":
            self.guidance.setText(result.pose_guidance)
        if result.quality is not None:
            self.quality_details.setText(result.quality.details)
        elif result.yaw is not None and result.pitch is not None:
            self.quality_details.setText(
                f"Pose: yaw {result.yaw:+.0f}°, pitch {result.pitch:+.0f}°"
            )

    def _on_embedding(self, result) -> None:
        if self.session.complete:
            return
        try:
            captured_pose, saved_path = self.session.accept(result)
        except Exception as error:
            self.stop_camera()
            QMessageBox.warning(self, "Registration failed", str(error))
            self.guidance.setText(f"Chưa lưu được mẫu cuối: {error}.")
            if self.enrollment_started:
                self._start_camera_worker()
            return
        if self.session.complete:
            self._refresh_step(captured_pose)
            self.stop_camera()
            QMessageBox.information(
                self, "Registration complete",
                f"{self.session.name} ({self.session.employee_id}) was saved locally with five embeddings.\n"
                f"Aligned images: {saved_path}",
            )
            self.session.reset()
            self.employee_id.clear()
            self.employee_name.clear()
            self.enrollment_started = False
            self.employee_id.setEnabled(True)
            self.employee_name.setEnabled(True)
            self.start_button.setEnabled(True)
            self._refresh_step()
            self.back_requested.emit()
            return
        self._refresh_step(captured_pose)
        if self.worker is not None:
            self.worker.set_required_pose(self.session.current_pose)

    def _on_embedding_error(self, message: str) -> None:
        self.embedding_status.setText(f"Embedding unavailable · {message}")

    def _on_antispoof_result(self, result) -> None:
        if result.is_real == self._fas_display_candidate:
            self._fas_display_count += 1
        else:
            self._fas_display_candidate = result.is_real
            self._fas_display_count = 1
        if self._fas_display_count < 2:
            self.fas_status.setText("FAS: confirming result")
            return
        verdict = "Real" if self._fas_display_candidate else "Possible spoof"
        self.fas_status.setText(
            f"FAS: {verdict} · mean score {result.logit_difference:+.2f} "
            f"(threshold {result.logit_threshold:+.2f})"
        )

    def _on_antispoof_error(self, message: str) -> None:
        self.fas_status.setText(f"FAS unavailable · {message}")

    def _reset_enrollment(self) -> None:
        self.stop_camera()
        self.session.reset()
        self.enrollment_started = False
        self.employee_id.setEnabled(True)
        self.employee_name.setEnabled(True)
        self.start_button.setEnabled(True)
        self._refresh_step()
        self.camera_view.setText("Nhập ID và tên rồi nhấn Enter để bắt đầu đăng ký.")

    def _camera_error(self, message: str) -> None:
        self.guidance.setText(message)

    def _back_to_recognition(self) -> None:
        self.stop_camera()
        self.session.reset()
        self.enrollment_started = False
        self.employee_id.setEnabled(True)
        self.employee_name.setEnabled(True)
        self.start_button.setEnabled(True)
        self.back_requested.emit()

    def _detector_error(self, message: str) -> None:
        self.guidance.setText(f"Face detector unavailable: {message}")
