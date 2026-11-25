from __future__ import annotations

import logging
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QBoxLayout, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from camera.frame_worker import FrameWorker
from registration.registration_flow import RegistrationFrameStatus
from registration.registration_session import RegistrationSession
from registration.registration_service import RegistrationService
from sync.api_client import ApiClient
from ui.widgets.camera_view import CameraView

logger = logging.getLogger(__name__)


class RegistrationPage(QWidget):
    """Qt presentation for the registration flow; capture gates live elsewhere."""

    back_requested = pyqtSignal()

    def __init__(self, registration_service: RegistrationService, sync_service=None, parent=None) -> None:
        super().__init__(parent)
        self.registration_service = registration_service
        self.sync_service = sync_service
        self.api_client = ApiClient()
        self.session = RegistrationSession(registration_service)
        self.worker: FrameWorker | None = None
        self.enrollment_started = False
        self.current_session_id: str | None = None
        self.current_user_id: str | None = None
        self.pending_sessions_map: dict[str, dict] = {}
        self._build_ui()
        self._refresh_step()
        self.reload_pending_sessions()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.reload_pending_sessions()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
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

        main_content = QHBoxLayout()

        # Side panel: Danh sách phiên chờ đăng ký
        sidebar = QVBoxLayout()
        sidebar_title = QLabel("Phiên chờ đăng ký")
        sidebar_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #63b3ed;")
        sidebar.addWidget(sidebar_title)

        sidebar_sub = QLabel("Chọn người bên dưới để bắt đầu:")
        sidebar_sub.setObjectName("mutedText")
        sidebar.addWidget(sidebar_sub)

        self.session_list = QListWidget()
        self.session_list.setFixedWidth(260)
        self.session_list.setStyleSheet(
            "QListWidget { background: #1a2332; border: 1px solid #2c3e50; border-radius: 8px; padding: 4px; }"
            "QListWidget::item { padding: 10px; border-bottom: 1px solid #243042; border-radius: 4px; color: #e2e8f0; }"
            "QListWidget::item:hover { background: #2b3a4e; }"
            "QListWidget::item:selected { background: #3182ce; color: #ffffff; font-weight: bold; }"
        )
        self.session_list.itemClicked.connect(self._on_session_item_clicked)
        sidebar.addWidget(self.session_list, 1)

        self.reload_sessions_button = QPushButton("Tải lại danh sách")
        self.reload_sessions_button.clicked.connect(self.reload_pending_sessions)
        sidebar.addWidget(self.reload_sessions_button)
        main_content.addLayout(sidebar)

        # Right panel: Form và Camera đăng ký
        right_panel = QVBoxLayout()
        identity_form = QFormLayout()
        self.employee_id = QLineEdit()
        self.employee_id.setPlaceholderText("e.g. E001")
        self.employee_name = QLineEdit()
        self.employee_name.setPlaceholderText("Employee name")
        self.employee_id.returnPressed.connect(self._check_employee_id)
        self.employee_name.returnPressed.connect(self._start_enrollment)
        identity_form.addRow("Employee ID", self.employee_id)
        identity_form.addRow("Name", self.employee_name)
        right_panel.addLayout(identity_form)

        self.camera_view = CameraView()
        right_panel.addWidget(self.camera_view, 1)
        self.step_label = QLabel()
        self.step_label.setObjectName("faceGuidance")
        self.step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.addWidget(self.step_label)
        self.instruction = QLabel()
        self.instruction.setObjectName("mutedText")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.addWidget(self.instruction)
        self.progress = QProgressBar()
        self.progress.setRange(0, len(self.session.POSES))
        right_panel.addWidget(self.progress)

        self.guidance = QLabel("Đưa một khuôn mặt vào vùng giữa.")
        self.guidance.setObjectName("faceGuidance")
        self.guidance.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.addWidget(self.guidance)
        self.quality_details = QLabel("")
        self.quality_details.setObjectName("mutedText")
        self.quality_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.addWidget(self.quality_details)
        self.embedding_status = QLabel("Đang chờ enrollment.")
        self.embedding_status.setObjectName("mutedText")
        self.embedding_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.addWidget(self.embedding_status)
        self.fas_status = QLabel("FAS: waiting for model")
        self.fas_status.setObjectName("mutedText")
        self.fas_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.addWidget(self.fas_status)

        actions = QHBoxLayout()
        actions.addStretch()
        self.start_button = QPushButton("Bắt đầu đăng ký")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self._start_enrollment)
        actions.addWidget(self.start_button)
        self.reset_button = QPushButton("Reset enrollment")
        self.reset_button.clicked.connect(self._reset_enrollment)
        actions.addWidget(self.reset_button)
        right_panel.addLayout(actions)

        main_content.addLayout(right_panel, 1)
        layout.addLayout(main_content)
        self._heading_layout = heading
        self._actions_layout = actions

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.reload_pending_sessions()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        compact = self.width() < 760
        direction = (
            QBoxLayout.Direction.TopToBottom
            if compact
            else QBoxLayout.Direction.LeftToRight
        )
        self._heading_layout.setDirection(direction)
        self._actions_layout.setDirection(direction)
        margin = 12 if compact else 20
        self.layout().setContentsMargins(
            margin, 10 if compact else 16, margin, 10 if compact else 16
        )
        self.layout().setSpacing(6 if compact else 8)

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
        self.worker.preview_worker.frame_ready.connect(self._on_preview)
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.guidance_result.connect(self._on_guidance_result)
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
        self.fas_status.setText("FAS: waiting for one eligible face")
        self.guidance.setText("Đang kiểm tra khuôn mặt…")
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
                self, "Nhân viên đã đăng ký",
                f"Mã nhân viên '{employee_id}' đã có dữ liệu khuôn mặt trong hệ thống.\n"
                "Để đảm bảo an toàn bảo mật, không được phép đăng ký mới hoặc ghi đè khuôn mặt.",
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
                self, "Nhân viên đã đăng ký",
                f"Mã nhân viên '{employee_id}' đã có dữ liệu khuôn mặt trong hệ thống.\n"
                "Để đảm bảo an toàn bảo mật, không được phép đăng ký mới hoặc ghi đè khuôn mặt.",
            )
            self.employee_id.setFocus()
            self.employee_id.selectAll()
            return
        self.enrollment_started = True
        self.session.begin(employee_id, name)
        self.employee_id.setEnabled(False)
        self.employee_name.setEnabled(False)
        self.start_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.guidance.setText("Đang khởi tạo camera và model…")
        self.camera_view.setText("Đang khởi tạo camera và model…")
        self._start_camera_worker()

    def _on_frame(self, image, detections, result) -> None:
        if not detections:
            self.quality_details.clear()
            self.fas_status.setText("FAS: waiting for one face")
            return
        if len(detections) > 1:
            self.quality_details.clear()
            self.fas_status.setText("FAS: paused · multiple faces in zone")
            return
        if not isinstance(result, RegistrationFrameStatus):
            return

        if result.quality is not None:
            self.quality_details.setText(result.quality.details)
        elif result.yaw is not None and result.pitch is not None:
            self.quality_details.setText(
                f"Pose: yaw {result.yaw:+.0f}°, pitch {result.pitch:+.0f}°"
            )

    def _on_preview(self, image) -> None:
        self.camera_view.set_frame(image)

    def _on_guidance_result(self, event) -> None:
        _frame_id, _timestamp, outcome, _track_id, message = event
        if outcome == "NO_FACE":
            text = "Đưa một khuôn mặt vào vùng giữa."
        elif outcome == "MULTIPLE_FACES":
            text = "Chỉ để một người trong vùng nhận diện."
        elif outcome == "ALL_PASS":
            text = "Đạt kiểm tra, đang lưu mẫu…"
        elif outcome == "ERROR":
            text = message or "Pipeline gặp lỗi kỹ thuật; vui lòng kiểm tra log."
        else:
            text = message
        if text:
            self.guidance.setText(text)

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

            # Gửi face embedding và hoàn tất phiên lên Backend Cloud
            cloud_synced = False
            if self.current_user_id and self.current_session_id:
                try:
                    vector = self.session.samples[0].vector.tolist()
                    up_ok = self.api_client.upload_face_embedding(self.current_user_id, vector)
                    done_ok = self.api_client.complete_session(self.current_session_id)
                    cloud_synced = up_ok and done_ok
                    if cloud_synced:
                        self._remove_completed_session(self.current_session_id)
                except Exception as e:
                    logger.error(f"[RegistrationPage] Cloud sync error: {e}")

            cloud_msg = "\n(Đã đồng bộ vector và hoàn tất phiên lên Cloud Backend!)" if cloud_synced else ""
            QMessageBox.information(
                self, "Registration complete",
                f"{self.session.name} ({self.session.employee_id}) was saved locally with five embeddings.\n"
                f"Aligned images: {saved_path}{cloud_msg}",
            )
            self.session.reset()
            self.employee_id.clear()
            self.employee_name.clear()
            self.current_session_id = None
            self.current_user_id = None
            self.enrollment_started = False
            self.employee_id.setEnabled(True)
            self.employee_name.setEnabled(True)
            self.start_button.setEnabled(True)
            self.back_button.setEnabled(True)
            self.reset_button.setEnabled(True)
            self._refresh_step()
            return
        self._refresh_step(captured_pose)
        if self.worker is not None:
            self.worker.set_required_pose(self.session.current_pose)

    def _on_embedding_error(self, message: str) -> None:
        self.embedding_status.setText(f"Embedding unavailable · {message}")

    def _on_antispoof_result(self, result) -> None:
        verdict = "Real" if result.is_real else "Possible spoof"
        self.fas_status.setText(
            f"FAS: {verdict} · real probability {result.real_probability:.2f} "
            f"(threshold {result.real_threshold:.2f})"
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
        self.back_button.setEnabled(True)
        self.reset_button.setEnabled(True)
        self._refresh_step()
        self.camera_view.setText("Nhập ID và tên rồi nhấn Enter để bắt đầu đăng ký.")

    def _camera_error(self, message: str) -> None:
        self.guidance.setText(message)

    def _back_to_recognition(self) -> None:
        if self.enrollment_started:
            return
        self.stop_camera()
        self.session.reset()
        self.enrollment_started = False
        self.employee_id.setEnabled(True)
        self.employee_name.setEnabled(True)
        self.start_button.setEnabled(True)
        self.back_requested.emit()

    def _detector_error(self, message: str) -> None:
        self.guidance.setText(f"Face detector unavailable: {message}")

    # ==================== PENDING SESSIONS MANAGEMENT ====================

    def reload_pending_sessions(self) -> None:
        """Fetch active pending sessions from Backend."""
        try:
            sessions = self.api_client.get_pending_sessions()
            self.session_list.clear()
            self.pending_sessions_map.clear()
            for s in sessions:
                self.add_pending_session(s)
            self.guidance.setText(f"Đã tải {len(sessions)} phiên đăng ký chờ.")
        except Exception as e:
            logger.error(f"[RegistrationPage] reload_pending_sessions failed: {e}")

    def add_pending_session(self, session: dict) -> None:
        """Add or update a pending session in the list."""
        session_id = str(session.get("id"))
        if not session_id or session_id in self.pending_sessions_map:
            return

        # Fetch user info if missing
        if ("user_code" not in session or "full_name" not in session) and session.get("user_id"):
            try:
                user = self.api_client.get_user(session["user_id"])
                if user:
                    session["user_code"] = user.get("user_code", "")
                    session["full_name"] = user.get("full_name", "")
            except Exception as e:
                logger.warning(f"[RegistrationPage] Could not fetch user details for {session.get('user_id')}: {e}")

        self.pending_sessions_map[session_id] = session

        full_name = session.get("full_name") or session.get("name") or "Người dùng mới"
        user_code = session.get("user_code") or session_id[:8]
        display_text = f"👤 {full_name}\n🆔 {user_code}"

        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, session)
        self.session_list.addItem(item)
        self.guidance.setText(f"🔔 Có phiên đăng ký mới: {full_name}! Chọn người để đăng ký.")

    def _remove_completed_session(self, session_id: str) -> None:
        """Remove a finalized session from list."""
        if session_id in self.pending_sessions_map:
            del self.pending_sessions_map[session_id]
        for row in range(self.session_list.count()):
            item = self.session_list.item(row)
            if item:
                s = item.data(Qt.ItemDataRole.UserRole)
                if s and str(s.get("id")) == str(session_id):
                    self.session_list.takeItem(row)
                    break

    def _on_session_item_clicked(self, item: QListWidgetItem) -> None:
        """Triggered when user clicks a pending candidate from the list."""
        if self.enrollment_started:
            return
        session = item.data(Qt.ItemDataRole.UserRole)
        if not session:
            return
        self.current_session_id = str(session.get("id"))
        self.current_user_id = str(session.get("user_id"))

        user_code = session.get("user_code") or f"U_{self.current_user_id[:8]}"
        full_name = session.get("full_name") or "Người dùng"

        self.employee_id.setText(user_code)
        self.employee_name.setText(full_name)
        self.guidance.setText(f"Đã chọn {full_name}. Nhấn 'Bắt đầu đăng ký' để tiếp tục.")
        self.start_button.setFocus()

