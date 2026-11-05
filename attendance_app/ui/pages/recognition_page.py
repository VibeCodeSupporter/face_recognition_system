"""Live camera preview with ONNX face detection in the centered ROI."""

from datetime import datetime
from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from camera.frame_worker import FrameWorker
from config.settings import FACE_MATCH_THRESHOLD
from recognition.recognition_controller import RecognitionController
from recognition.recognition_service import RecognitionService
from ui.widgets.camera_view import CameraView


class RecognitionPage(QWidget):
    register_requested = pyqtSignal()

    def __init__(self, recognition_service: RecognitionService | None = None, parent=None) -> None:
        super().__init__(parent)
        self.recognition_service = recognition_service
        self.worker = None
        self.detector_available = False
        self.detector_error_message = None
        self.embedding_error_message = None
        self.fas_error_message = None
        self.current_track_id: int | None = None
        self.current_face_count = 0
        self.recognized_employee_ids: set[str] = set()
        self.recognition_controller = (
            RecognitionController(recognition_service, self)
            if recognition_service is not None
            else None
        )
        if self.recognition_controller is not None:
            self.recognition_controller.result_ready.connect(self._recognition_ready)
            self.recognition_controller.error.connect(self._embedding_error)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        heading = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel("Face recognition preview")
        title.setObjectName("pageTitle")
        subtitle = QLabel("ONNX detection · GhostFaceNet embeddings · local FAISS search")
        subtitle.setObjectName("mutedText")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        heading.addLayout(title_block)
        heading.addStretch()
        self.register_button = QPushButton("Register face")
        self.register_button.setObjectName("primaryButton")
        self.register_button.clicked.connect(self.register_requested.emit)
        heading.addWidget(self.register_button)
        self.camera_status = QLabel("● Starting camera")
        self.camera_status.setObjectName("statusPill")
        heading.addWidget(self.camera_status, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(heading)

        self.camera_view = CameraView()
        self.camera_view.setMinimumSize(640, 400)
        preview_row = QHBoxLayout()
        preview_row.setSpacing(16)
        preview_row.addWidget(self.camera_view, 1)

        self.result_panel = QFrame()
        self.result_panel.setObjectName("recognitionResultPanel")
        self.result_panel.setMinimumWidth(320)
        self.result_panel.setStyleSheet(
            "QFrame#recognitionResultPanel { background: #151d28; "
            "border: 1px solid #2c3745; border-radius: 12px; }"
        )
        result_layout = QVBoxLayout(self.result_panel)
        result_layout.setContentsMargins(16, 18, 16, 18)
        result_layout.setSpacing(12)
        result_title = QLabel("Kết quả nhận diện gần nhất")
        result_title.setStyleSheet("font-size: 17px; font-weight: 700; border: 0;")
        result_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(result_title)
        self.result_image = QLabel("Chưa có match")
        self.result_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_image.setFixedSize(220, 220)
        self.result_image.setStyleSheet(
            "background: #080b10; border: 1px solid #344152; border-radius: 8px;"
        )
        result_layout.addWidget(self.result_image, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.result_state = QLabel("Chờ nhận diện thành công")
        self.result_state.setObjectName("mutedText")
        self.result_state.setWordWrap(True)
        result_layout.addWidget(self.result_state)
        self.result_name = QLabel("Tên: —")
        self.result_name.setWordWrap(True)
        self.result_id = QLabel("ID: —")
        self.result_score = QLabel("Squared L2 (càng thấp càng gần): —")
        self.result_threshold = QLabel(f"Ngưỡng: ≤ {FACE_MATCH_THRESHOLD:.2f}")
        for label in (self.result_name, self.result_id, self.result_score, self.result_threshold):
            label.setObjectName("mutedText")
            label.setWordWrap(True)
            result_layout.addWidget(label)
        result_layout.addStretch(1)
        preview_row.addWidget(self.result_panel, 0)
        layout.addLayout(preview_row, 1)

        self.face_guidance = QLabel("Đưa một khuôn mặt vào vùng giữa.")
        self.face_guidance.setObjectName("faceGuidance")
        self.face_guidance.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.face_guidance)
        self.quality_details = QLabel("")
        self.quality_details.setObjectName("mutedText")
        self.quality_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.quality_details)
        self.embedding_status = QLabel("Embedding: waiting for face quality check")
        self.embedding_status.setObjectName("mutedText")
        self.embedding_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.embedding_status)
        self.fas_status = QLabel("FAS: loading ONNX model")
        self.fas_status.setObjectName("mutedText")
        self.fas_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.fas_status)

        footer = QHBoxLayout()
        hint = QLabel("Đưa một mặt vào vùng giữa; các mặt ngoài vùng này không được detect.")
        hint.setObjectName("mutedText")
        footer.addWidget(hint)
        footer.addStretch()
        self.rebuild_index_button = QPushButton("Rebuild FAISS index")
        self.rebuild_index_button.setObjectName("primaryButton")
        self.rebuild_index_button.setEnabled(self.recognition_service is not None)
        self.rebuild_index_button.clicked.connect(self.rebuild_index)
        footer.addWidget(self.rebuild_index_button)
        self.capture_button = QPushButton("Capture ROI image")
        self.capture_button.setObjectName("primaryButton")
        self.capture_button.setEnabled(False)
        self.capture_button.clicked.connect(self.capture_image)
        footer.addWidget(self.capture_button)
        layout.addLayout(footer)

        self.last_capture = QLabel("No image captured yet")
        self.last_capture.setObjectName("mutedText")
        layout.addWidget(self.last_capture)

    def rebuild_index(self) -> None:
        if self.recognition_service is None:
            return
        answer = QMessageBox.question(
            self,
            "Rebuild FAISS index",
            "Dựng lại index từ embedding trong SQLite? Dữ liệu đăng ký sẽ được giữ nguyên.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.rebuild_index_button.setEnabled(False)
        self.rebuild_index_button.setText("Đang rebuild…")
        try:
            count = self.recognition_service.vector_store.rebuild()
        except Exception as error:
            QMessageBox.warning(self, "FAISS rebuild failed", str(error))
        else:
            QMessageBox.information(
                self,
                "FAISS index rebuilt",
                f"Đã dựng lại index từ {count} embedding trong SQLite.",
            )
        finally:
            self.rebuild_index_button.setText("Rebuild FAISS index")
            self.rebuild_index_button.setEnabled(True)

    def start_camera(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self.detector_available = False
        self.detector_error_message = None
        self.embedding_error_message = None
        self.fas_error_message = None
        self.current_track_id = None
        self.current_face_count = 0
        self.recognized_employee_ids.clear()
        self.camera_view.set_spoof_state(False)
        self.embedding_status.setText("Embedding: loading ONNX model")
        self.fas_status.setText("FAS: loading ONNX model")
        self.camera_status.setText("● Loading ONNX detector")
        self.worker = FrameWorker()
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.camera_error.connect(self._camera_error)
        self.worker.detector_ready.connect(self._detector_ready)
        self.worker.detector_error.connect(self._detector_error)
        if self.recognition_controller is not None:
            self.worker.embedding_ready.connect(self.recognition_controller.identify)
        else:
            self.worker.embedding_ready.connect(self._embedding_preview)
        self.worker.embedding_error.connect(self._embedding_error)
        self.worker.antispoof_result.connect(self._on_antispoof_result)
        self.worker.antispoof_error.connect(self._on_antispoof_error)
        self.worker.start()

    def stop_camera(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)

    def capture_image(self) -> None:
        image = self.camera_view.captured_roi_image()
        if image is None:
            QMessageBox.information(self, "Camera not ready", "Wait for a camera frame, then capture.")
            return
        default_dir = Path(__file__).resolve().parents[2] / "data" / "captures"
        default_dir.mkdir(parents=True, exist_ok=True)
        default_name = default_dir / f"capture_roi_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save cropped ROI image",
            str(default_name),
            "JPEG image (*.jpg);;PNG image (*.png)",
        )
        if path and image.save(path):
            self.last_capture.setText(f"Saved: {path}")
        elif path:
            QMessageBox.warning(self, "Save failed", "Could not save the captured image.")

    def _set_result_state(self, message: str, color: str = "#9aa8b8") -> None:
        self.result_state.setText(message)
        self.result_state.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _camera_error(self, message: str) -> None:
        self.camera_status.setText("● Camera unavailable")
        self.camera_status.setProperty("state", "error")
        self.camera_status.style().unpolish(self.camera_status)
        self.camera_status.style().polish(self.camera_status)
        self.camera_view.setText(message + "\nCheck the camera connection and restart the app.")

    def _detector_ready(self) -> None:
        self.detector_available = True
        self.detector_error_message = None

    def _detector_error(self, message: str) -> None:
        self.detector_available = False
        self.detector_error_message = message
        self.camera_status.setText("● ONNX detector unavailable")
        self.camera_status.setProperty("state", "error")
        self.camera_status.style().unpolish(self.camera_status)
        self.camera_status.style().polish(self.camera_status)

    def _recognition_ready(self, result, match) -> None:
        self.embedding_error_message = None
        if match is None:
            self._set_result_state("Không khớp hồ sơ nào trong gallery", "#f6c177")
            self.embedding_status.setText(
                "Không nhận diện được người này · khoảng cách vượt ngưỡng."
            )
        else:
            already_seen = match.employee_id in self.recognized_employee_ids
            self.recognized_employee_ids.add(match.employee_id)
            image = np.ascontiguousarray(result.aligned_rgb)
            height, width = image.shape[:2]
            qimage = QImage(
                image.data,
                width,
                height,
                image.strides[0],
                QImage.Format.Format_RGB888,
            ).copy()
            self.result_image.setPixmap(
                QPixmap.fromImage(qimage).scaled(
                    self.result_image.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            threshold = getattr(
                self.recognition_service.vector_store,
                "threshold",
                FACE_MATCH_THRESHOLD,
            )
            self._set_result_state(
                f"Đã nhận diện rồi: {match.name} ({match.employee_id})"
                if already_seen
                else "Nhận diện thành công",
                "#81e6b0",
            )
            self.result_name.setText(f"Tên: {match.name}")
            self.result_id.setText(f"ID: {match.employee_id}")
            self.result_score.setText(
                f"Squared L2 (0–4, càng thấp càng giống): {match.squared_l2_distance:.3f}"
            )
            self.result_threshold.setText(f"Ngưỡng squared L2: ≤ {threshold:.2f}")
            self.embedding_status.setText(
                f"Người này đã được nhận diện trong lượt hiện tại · "
                f"squared L2 {match.squared_l2_distance:.3f}"
                if already_seen
                else f"Đã nhận diện {match.name} ({match.employee_id}) · "
                f"squared L2 {match.squared_l2_distance:.3f}"
            )

    def _embedding_preview(self, result) -> None:
        self.embedding_status.setText(
            f"Embedding ready · {result.model_name} · {result.vector.size} dimensions"
        )

    def _embedding_error(self, message: str) -> None:
        self.embedding_error_message = message
        self.embedding_status.setText(f"Embedding unavailable · {message}")

    def _on_antispoof_result(self, result) -> None:
        self.fas_error_message = None
        verdict = "Real" if result.is_real else "Possible spoof"
        self.fas_status.setText(
            f"FAS: {verdict} · score {result.logit_difference:+.2f} "
            f"(threshold {result.logit_threshold:+.2f})"
        )
        self.camera_view.set_spoof_state(not result.is_real, result.track_id)
        if not result.is_real:
            self._set_result_state(
                "Spoof phát hiện · nhận diện đang tạm dừng", "#ff6b6b"
            )
            self.embedding_status.setText("Recognition paused · possible spoof")
        elif self.result_state.text().startswith("Spoof"):
            self._set_result_state("FAS báo Real · đang chờ kết quả nhận diện")

    def _on_antispoof_error(self, message: str) -> None:
        self.fas_error_message = message
        self.camera_view.set_spoof_state(False)
        self.fas_status.setText(f"FAS unavailable · {message}")

    def _on_frame(self, image, detections, quality_result) -> None:
        self.camera_view.set_frame(image)
        self.camera_view.set_detections(detections)
        self.capture_button.setEnabled(True)
        previous_track_id = self.current_track_id
        self.current_face_count = len(detections)
        self.current_track_id = detections[0].track_id if len(detections) == 1 else None
        if (
            self.current_track_id is not None
            and previous_track_id is not None
            and self.current_track_id != previous_track_id
        ):
            self.camera_view.set_spoof_state(False)
            self.fas_error_message = None
            self.fas_status.setText("FAS: collecting same-track samples")
        if self.current_face_count == 0:
            self.camera_view.set_spoof_state(False)
            self._set_result_state("Chờ khuôn mặt trong vùng")
        elif self.current_face_count > 1:
            self.camera_view.set_spoof_state(False)
            self._set_result_state("Có nhiều mặt · nhận diện tạm dừng", "#f6c177")
        if self.detector_error_message:
            self.camera_status.setText("● Camera live · detector unavailable")
            self.face_guidance.setText("Không thể kiểm tra khuôn mặt; hãy kiểm tra model ONNX.")
            self.quality_details.clear()
        elif self.detector_available:
            count = len(detections)
            if count == 0:
                message = "No face in zone"
                guidance = "Đưa một khuôn mặt vào vùng giữa."
                details = ""
                self.fas_status.setText("FAS: waiting for one face")
            elif count == 1:
                message = "1 face detected"
                if quality_result is None:
                    guidance = "Đang xác nhận khuôn mặt thật từ các frame FAS."
                    if (
                        self.fas_error_message is None
                        and self.fas_status.text()
                        in {"FAS: loading ONNX model", "FAS: waiting for one face"}
                    ):
                        self.fas_status.setText("FAS: collecting same-track samples")
                    details = ""
                else:
                    guidance = quality_result.guidance
                    details = quality_result.details
            else:
                message = f"{count} faces detected"
                guidance = "Có nhiều khuôn mặt; vui lòng để một người trong vùng."
                details = ""
                self.fas_status.setText("FAS: paused · multiple faces in zone")
            self.face_guidance.setText(guidance)
            self.quality_details.setText(details)
            self.camera_status.setText(f"● Camera live · {message}")
