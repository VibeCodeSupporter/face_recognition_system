"""Small OpenCV camera adapter used by the preview worker."""
import cv2

class CameraManager:
    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self._capture = None

    def open(self) -> bool:
        self._capture = cv2.VideoCapture(self.camera_index)
        return self._capture.isOpened()

    def read(self):
        if self._capture is None:
            return False, None
        return self._capture.read()

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
