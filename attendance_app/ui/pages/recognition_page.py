"""Live camera preview with ONNX face detection in the centered ROI."""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from camera.frame_worker import FrameWorker
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
        layout.addWidget(self.camera_view, 1)

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
        self.capture_button = QPushButton("Capture ROI image")
        self.capture_button.setObjectName("primaryButton")
        self.capture_button.setEnabled(False)
        self.capture_button.clicked.connect(self.capture_image)
        footer.addWidget(self.capture_button)
        layout.addLayout(footer)

        self.last_capture = QLabel("No image captured yet")
        self.last_capture.setObjectName("mutedText")
        layout.addWidget(self.last_capture)

    def start_camera(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self.detector_available = False
        self.detector_error_message = None
        self.embedding_error_message = None
        self.fas_error_message = None
        self.embedding_status.setText("Embedding: loading ONNX model")
        self.fas_status.setText("FAS: loading ONNX model")
        self.camera_status.setText("● Loading ONNX detector")
        self.worker = FrameWorker()
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.camera_error.connect(self._camera_error)
        self.worker.detector_ready.connect(self._detector_ready)
        self.worker.detector_error.connect(self._detector_error)
        self.worker.embedding_ready.connect(self._embedding_ready)
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

    def _embedding_ready(self, result) -> None:
        self.embedding_error_message = None
        if self.recognition_service is None:
            self.embedding_status.setText(
                f"Embedding ready · {result.model_name} · {result.vector.size} dimensions"
            )
            return
        try:
            match = self.recognition_service.identify(result.vector)
        except Exception as error:
            self._embedding_error(f"Local vector search failed: {error}")
            return
        if match is None:
            self.embedding_status.setText(
                f"Unknown face · squared L2 distance exceeds local threshold"
            )
        else:
            self.embedding_status.setText(
                f"Matched {match.name} ({match.employee_id}) · "
                f"squared L2 {match.squared_l2_distance:.3f}"
            )

    def _embedding_error(self, message: str) -> None:
        self.embedding_error_message = message
        self.embedding_status.setText(f"Embedding unavailable · {message}")

    def _on_antispoof_result(self, result) -> None:
        self.fas_error_message = None
        verdict = "Real" if result.is_real else "Possible spoof"
        self.fas_status.setText(
            f"FAS: {verdict} · real {result.real_probability:.1%} · "
            f"spoof {result.spoof_probability:.1%}"
        )
        if not result.is_real:
            self.embedding_status.setText("Recognition paused · possible spoof")

    def _on_antispoof_error(self, message: str) -> None:
        self.fas_error_message = message
        self.fas_status.setText(f"FAS unavailable · {message}")

    def _on_frame(self, image, detections, quality_result) -> None:
        self.camera_view.set_frame(image)
        self.camera_view.set_detections(detections)
        self.capture_button.setEnabled(True)
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
                    guidance = "Đang kiểm tra chất lượng khuôn mặt."
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
