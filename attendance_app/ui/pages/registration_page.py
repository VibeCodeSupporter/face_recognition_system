"""Guided five-pose offline face enrollment page."""

from __future__ import annotations

import time

import numpy as np
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

from camera.frame_worker import FrameWorker
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

    def __init__(
        self, registration_service: RegistrationService, parent=None
    ) -> None:
        super().__init__(parent)
        self.registration_service = registration_service
        self.worker: FrameWorker | None = None
        self.latest_quality = None
        self.latest_embedding = None
        self.latest_antispoof = None
        self.current_track_id: int | None = None
        self.samples: list[EnrollmentSample] = []
        self.step_started_at = time.monotonic()
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
        self.back_button.clicked.connect(self.back_requested.emit)
        heading.addWidget(self.back_button)
        layout.addLayout(heading)

        identity_form = QFormLayout()
        self.employee_id = QLineEdit()
        self.employee_id.setPlaceholderText("e.g. E001")
        self.employee_name = QLineEdit()
        self.employee_name.setPlaceholderText("Employee name")
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
        self.capture_button = QPushButton("Capture this pose")
        self.capture_button.setObjectName("primaryButton")
        self.capture_button.setEnabled(False)
        self.capture_button.clicked.connect(self._capture_pose)
        actions.addWidget(self.capture_button)
        self.reset_button = QPushButton("Reset enrollment")
        self.reset_button.clicked.connect(self._reset_enrollment)
        actions.addWidget(self.reset_button)
        layout.addLayout(actions)

    def start_camera(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self.latest_quality = None
        self.latest_embedding = None
        self.latest_antispoof = None
        self.current_track_id = None
        self.step_started_at = time.monotonic()
        self.worker = FrameWorker()
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

    def _refresh_step(self) -> None:
        self.progress.setValue(len(self.samples))
        if len(self.samples) >= len(self.POSES):
            self.step_label.setText("Đã thu đủ 5 tư thế")
            self.instruction.setText("Đang lưu embedding vào local gallery…")
            self.capture_button.setEnabled(False)
            return
        _, label, instruction = self.POSES[len(self.samples)]
        self.step_label.setText(
            f"Tư thế {len(self.samples) + 1}/{len(self.POSES)} · {label}"
        )
        self.instruction.setText(instruction)
        self.capture_button.setText(f"Capture {label.lower()}")
        self._update_capture_button()

    def _on_frame(self, image, detections, quality_result) -> None:
        self.camera_view.set_frame(image)
        self.camera_view.set_detections(detections)
        self.latest_quality = quality_result
        self.current_track_id = detections[0].track_id if len(detections) == 1 else None
        if not detections:
            self.latest_antispoof = None
            self.latest_embedding = None
            self.fas_status.setText("FAS: waiting for one face")
            self.guidance.setText("Đưa một khuôn mặt vào vùng giữa.")
            self.quality_details.clear()
        elif len(detections) > 1:
            self.latest_antispoof = None
            self.latest_embedding = None
            self.fas_status.setText("FAS: paused · multiple faces in zone")
            self.guidance.setText("Chỉ để một người trong vùng nhận diện.")
            self.quality_details.clear()
        elif quality_result is not None:
            self.guidance.setText(quality_result.guidance)
            self.quality_details.setText(quality_result.details)
        else:
            self.guidance.setText("Đang kiểm tra chất lượng khuôn mặt.")
            self.quality_details.clear()
        self._update_capture_button()

    def _on_embedding(self, result) -> None:
        self.latest_embedding = result
        if len(self.samples) < len(self.POSES):
            self.embedding_status.setText(
                f"Embedding sẵn sàng · {result.vector.size} chiều"
            )
        self._update_capture_button()

    def _on_embedding_error(self, message: str) -> None:
        self.embedding_status.setText(f"Embedding chưa sẵn sàng: {message}")
        self._update_capture_button()

    def _on_antispoof_result(self, result) -> None:
        self.latest_antispoof = result
        verdict = "Real" if result.is_real else "Possible spoof"
        self.fas_status.setText(
            f"FAS: {verdict} · real {result.real_probability:.1%} · "
            f"spoof {result.spoof_probability:.1%}"
        )
        if not result.is_real:
            self.latest_embedding = None
        self._update_capture_button()

    def _on_antispoof_error(self, message: str) -> None:
        self.latest_antispoof = None
        self.latest_embedding = None
        self.fas_status.setText(f"FAS unavailable · {message}")
        self._update_capture_button()

    def _update_capture_button(self) -> None:
        if len(self.samples) >= len(self.POSES):
            self.capture_button.setEnabled(False)
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
        fas_is_current = (
            self.latest_antispoof is not None
            and self.latest_antispoof.is_real
            and self.latest_antispoof.created_at >= self.step_started_at
            and time.monotonic() - self.latest_antispoof.created_at <= 1.5
            and (
                self.current_track_id is None
                or self.latest_antispoof.track_id is None
                or self.current_track_id == self.latest_antispoof.track_id
            )
        )
        paired = (
            self.latest_embedding is not None
            and self.latest_antispoof is not None
            and abs(
                self.latest_embedding.created_at - self.latest_antispoof.created_at
            ) <= 1.5
        )
        quality_is_ready = (
            self.latest_quality is not None
            and self.latest_quality.passed
            and self.latest_quality.stable
        )
        self.capture_button.setEnabled(
            quality_is_ready and embedding_is_current and fas_is_current and paired
        )

    def _capture_pose(self) -> None:
        employee_id = self.employee_id.text().strip()
        employee_name = self.employee_name.text().strip()
        if not employee_id or not employee_name:
            QMessageBox.information(
                self, "Employee details required", "Enter employee ID and name first."
            )
            return
        if not self.capture_button.isEnabled() or self.latest_embedding is None:
            return

        pose_key = self.POSES[len(self.samples)][0]
        self.samples.append(
            EnrollmentSample(
                pose_key,
                self.latest_embedding.vector.copy(),
                self.latest_embedding.aligned_rgb.copy(),
            )
        )
        self.latest_embedding = None
        self.latest_antispoof = None
        self.step_started_at = time.monotonic()
        self.embedding_status.setText("Giữ tư thế mới; đang chờ embedding mới.")
        if len(self.samples) == len(self.POSES):
            self._save_enrollment(employee_id, employee_name)
        else:
            self._refresh_step()

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
        self._refresh_step()
        self.back_requested.emit()

    def _reset_enrollment(self) -> None:
        self.samples.clear()
        self.latest_embedding = None
        self.latest_antispoof = None
        self.step_started_at = time.monotonic()
        self.embedding_status.setText("Đang chờ embedding ổn định.")
        self._refresh_step()

    def _camera_error(self, message: str) -> None:
        self.guidance.setText(message)

    def _detector_error(self, message: str) -> None:
        self.guidance.setText(f"Face detector unavailable: {message}")

