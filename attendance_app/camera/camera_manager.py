"""Small OpenCV camera adapter used by the preview worker."""
import cv2
from threading import Condition, Event, Thread
import time

class CameraManager:
    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self._capture = None
        self._condition = Condition()
        self._stop_capture = Event()
        self._capture_thread: Thread | None = None
        self._latest_frame = None
        self._latest_timestamp = 0.0
        self._frame_sequence = 0
        self._read_sequence = 0
        self._capture_error = False

    def open(self) -> bool:
        self._capture = cv2.VideoCapture(self.camera_index)
        self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self._capture.isOpened():
            return False
        self._capture_error = False
        self._frame_sequence = 0
        self._read_sequence = 0
        self._stop_capture.clear()
        self._capture_thread = Thread(target=self._capture_latest, daemon=True)
        self._capture_thread.start()
        return True

    def _capture_latest(self) -> None:
        capture = self._capture
        while not self._stop_capture.is_set():
            ok, frame = capture.read()
            with self._condition:
                if not ok:
                    self._capture_error = True
                    self._condition.notify_all()
                    return
                self._latest_frame = frame
                self._latest_timestamp = time.monotonic()
                self._frame_sequence += 1
                self._condition.notify_all()

    def read(self):
        with self._condition:
            available = self._condition.wait_for(
                lambda: self._frame_sequence != self._read_sequence
                or self._capture_error
                or self._stop_capture.is_set(),
                timeout=2.0,
            )
            if not available or self._frame_sequence == self._read_sequence:
                return False, None, None, None
            self._read_sequence = self._frame_sequence
            return (
                True,
                self._latest_frame.copy(),
                self._frame_sequence,
                self._latest_timestamp,
            )

    def close(self) -> None:
        if self._capture is not None:
            self._stop_capture.set()
            self._capture.release()
            self._capture = None
            with self._condition:
                self._condition.notify_all()
            if self._capture_thread is not None:
                self._capture_thread.join(timeout=2.0)
                self._capture_thread = None
