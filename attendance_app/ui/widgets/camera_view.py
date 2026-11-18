"""Camera preview with ROI guidance and face detection overlays."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel

from common.face_region import FACE_ROI, face_roi_bounds

class CameraView(QLabel):
    ROI = QRectF(*FACE_ROI)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._image = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 180)
        self.setText("Đang khởi động camera…")
        self.setObjectName("cameraView")

    def set_frame(self, image: QImage) -> None:
        self._image = image.copy()
        self._render()

    def captured_image(self):
        return self._image.copy() if self._image is not None else None

    def captured_roi_image(self):
        """Return the current source frame cropped to the detector ROI."""
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
        painter.end()

    def _image_display_rect(self) -> QRectF:
        area = QRectF(self.contentsRect())
        scale = min(
            area.width() / self._image.width(),
            area.height() / self._image.height(),
        )
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
