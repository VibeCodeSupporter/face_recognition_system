"""Camera preview with ROI guidance and face detection overlays."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel

from common.face_region import FACE_ROI, face_roi_bounds
from face.detector import FaceDetection


class CameraView(QLabel):
    ROI = QRectF(*FACE_ROI)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._image = None
        self._detections: list[FaceDetection] = []
        self._spoof_detected = False
        self._spoof_track_id: int | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 180)
        self.setText("Đang khởi động camera…")
        self.setObjectName("cameraView")

    def set_frame(self, image: QImage) -> None:
        self._image = image.copy()
        self._render()

    def set_detections(self, detections: list[FaceDetection]) -> None:
        self._detections = detections
        self.update()

    def set_spoof_state(self, spoof_detected: bool, track_id: int | None = None) -> None:
        self._spoof_detected = spoof_detected
        self._spoof_track_id = track_id if spoof_detected else None
        self.update()

    def captured_image(self):
        return self._image.copy() if self._image is not None else None

    def captured_roi_image(self):
        """Return the current source frame cropped to the same detector ROI."""
        if self._image is None:
            return None
        left, top, right, bottom = face_roi_bounds(
            self._image.width(), self._image.height()
        )
        return self._image.copy(left, top, right - left, bottom - top)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._image is None:
            return
        image_rect = self._image_display_rect()
        roi = QRectF(
            image_rect.x() + image_rect.width() * self.ROI.x(),
            image_rect.y() + image_rect.height() * self.ROI.y(),
            image_rect.width() * self.ROI.width(),
            image_rect.height() * self.ROI.height(),
        )
        scale_x = image_rect.width() / self._image.width()
        scale_y = image_rect.height() / self._image.height()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#73e6ac"), 3))
        painter.drawRoundedRect(roi, 12, 12)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            roi.adjusted(12, 10, -8, -8),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            "VÙNG ĐƯA MẶT VÀO",
        )

        for detection in self._detections:
            x1, y1, x2, y2 = detection.bbox
            box = QRectF(
                image_rect.x() + x1 * scale_x,
                image_rect.y() + y1 * scale_y,
                (x2 - x1) * scale_x,
                (y2 - y1) * scale_y,
            )
            spoofed = self._spoof_detected and (
                self._spoof_track_id is None
                or detection.track_id is None
                or detection.track_id == self._spoof_track_id
            )
            box_color = QColor("#ff4d4f") if spoofed else QColor("#58a6ff")
            painter.setPen(QPen(box_color, 3 if spoofed else 2))
            painter.drawRect(box)
            track_label = (
                f"Face #{detection.track_id}"
                if detection.track_id is not None and detection.track_id >= 0
                else "Face"
            )
            painter.drawText(
                box.adjusted(4, 3, -3, -3),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                f"{'SPOOF · ' if spoofed else ''}{track_label} · {detection.confidence:.2f}",
            )
            painter.setPen(QPen(QColor("#ff6b6b"), 5))
            for point_x, point_y, visibility in detection.landmarks:
                if visibility >= 0.2:
                    painter.drawPoint(
                        round(image_rect.x() + point_x * scale_x),
                        round(image_rect.y() + point_y * scale_y),
                    )
        painter.end()

    def _image_display_rect(self) -> QRectF:
        area = QRectF(self.contentsRect())
        scale = min(area.width() / self._image.width(), area.height() / self._image.height())
        width = self._image.width() * scale
        height = self._image.height() * scale
        return QRectF(
            area.x() + (area.width() - width) / 2,
            area.y() + (area.height() - height) / 2,
            width,
            height,
        )

    def _render(self) -> None:
        if self._image is None:
            return
        pixmap = QPixmap.fromImage(self._image)
        self.setPixmap(pixmap.scaled(
            self.contentsRect().size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
