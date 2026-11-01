"""Lightweight, model-independent face image quality checks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math

import cv2
import numpy as np

from common.face_region import face_roi_bounds
from face.detector import FaceDetection


@dataclass(frozen=True)
class FaceQualityResult:
    """Metrics and user guidance for one face in the capture ROI."""

    passed: bool
    stable: bool
    guidance: str
    details: str
    face_width_ratio: float
    face_height_ratio: float
    blur_score: float
    brightness: float
    yaw: float | None
    pitch: float | None
    roll: float | None


class FaceQualityChecker:
    """Check face size, sharpness, exposure, pose, framing, and stability."""

    MIN_FACE_HEIGHT_RATIO = 0.40
    MIN_FACE_WIDTH_RATIO = 0.20
    MAX_FACE_HEIGHT_RATIO = 0.78
    MAX_FACE_WIDTH_RATIO = 0.85
    MIN_BLUR_SCORE = 100.0
    MIN_BRIGHTNESS = 80.0
    MAX_BRIGHTNESS = 220.0
    # Keep pose guidance permissive so small natural head movements do not
    # interrupt attendance. These are advisory limits, not recognition gates.
    MAX_YAW_DEGREES = 35.0
    MAX_PITCH_DEGREES = 35.0
    MAX_ROLL_DEGREES = 30.0
    STABLE_FRAME_COUNT = 5

    # Approximate 3-D facial landmarks in detector order: eyes, nose, mouth corners.
    _MODEL_POINTS = np.array(
        [
            [-30.0, 30.0, -20.0],
            [30.0, 30.0, -20.0],
            [0.0, 0.0, 0.0],
            [-25.0, -30.0, -15.0],
            [25.0, -30.0, -15.0],
        ],
        dtype=np.float64,
    )

    def __init__(self) -> None:
        self._history: deque[tuple[float, float, float, float]] = deque(
            maxlen=self.STABLE_FRAME_COUNT
        )
        self._track_id: int | None = None

    def reset(self) -> None:
        self._history.clear()
        self._track_id = None

    def evaluate(
        self, frame_bgr: np.ndarray, detection: FaceDetection
    ) -> FaceQualityResult:
        frame_height, frame_width = frame_bgr.shape[:2]
        roi_left, roi_top, roi_right, roi_bottom = face_roi_bounds(
            frame_width, frame_height
        )
        roi_width = max(1, roi_right - roi_left)
        roi_height = max(1, roi_bottom - roi_top)

        x1, y1, x2, y2 = detection.bbox
        face_width = max(0.0, x2 - x1)
        face_height = max(0.0, y2 - y1)
        width_ratio = face_width / roi_width
        height_ratio = face_height / roi_height

        crop_left = max(0, int(math.floor(x1)))
        crop_top = max(0, int(math.floor(y1)))
        crop_right = min(frame_width, int(math.ceil(x2)))
        crop_bottom = min(frame_height, int(math.ceil(y2)))
        face_crop = frame_bgr[crop_top:crop_bottom, crop_left:crop_right]

        if face_crop.size:
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB)
            brightness = float(np.mean(lab[:, :, 0]))
        else:
            blur_score = 0.0
            brightness = 0.0

        pose = self._estimate_pose(detection.landmarks, frame_width, frame_height)
        issues: list[str] = []

        if (
            height_ratio < self.MIN_FACE_HEIGHT_RATIO
            or width_ratio < self.MIN_FACE_WIDTH_RATIO
        ):
            issues.append("small")
        elif (
            height_ratio > self.MAX_FACE_HEIGHT_RATIO
            or width_ratio > self.MAX_FACE_WIDTH_RATIO
        ):
            issues.append("large")

        edge_margin_x = roi_width * 0.015
        edge_margin_y = roi_height * 0.015
        if (
            x1 <= roi_left + edge_margin_x
            or x2 >= roi_right - edge_margin_x
            or y1 <= roi_top + edge_margin_y
            or y2 >= roi_bottom - edge_margin_y
        ):
            issues.append("framing")
        if blur_score < self.MIN_BLUR_SCORE:
            issues.append("blur")
        if brightness < self.MIN_BRIGHTNESS:
            issues.append("dark")
        elif brightness > self.MAX_BRIGHTNESS:
            issues.append("bright")
        if pose is None:
            issues.append("pose_unknown")
        else:
            yaw, pitch, roll = pose
            if abs(yaw) > self.MAX_YAW_DEGREES or abs(pitch) > self.MAX_PITCH_DEGREES:
                issues.append("pose_turn")
            elif abs(roll) > self.MAX_ROLL_DEGREES:
                issues.append("pose_tilt")

        # Pose estimates from five detector landmarks are approximate; do not
        # let them prevent a frame from passing basic image quality checks.
        blocking_issues = [
            issue
            for issue in issues
            if issue not in {"pose_unknown", "pose_turn", "pose_tilt"}
        ]
        passed = not blocking_issues
        stable = self._update_stability(
            detection, roi_left, roi_top, roi_width, roi_height, passed
        )
        guidance = self._guidance(issues, stable)
        details = self._format_details(
            width_ratio, height_ratio, blur_score, brightness, pose, stable
        )
        yaw, pitch, roll = pose if pose is not None else (None, None, None)
        return FaceQualityResult(
            passed=passed,
            stable=stable,
            guidance=guidance,
            details=details,
            face_width_ratio=width_ratio,
            face_height_ratio=height_ratio,
            blur_score=blur_score,
            brightness=brightness,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
        )

    def _update_stability(
        self,
        detection: FaceDetection,
        roi_left: int,
        roi_top: int,
        roi_width: int,
        roi_height: int,
        passed: bool,
    ) -> bool:
        if not passed:
            self._history.clear()
            return False

        if detection.track_id is not None and detection.track_id >= 0:
            if self._track_id is not None and detection.track_id != self._track_id:
                self._history.clear()
            self._track_id = detection.track_id

        x1, y1, x2, y2 = detection.bbox
        self._history.append(
            (
                ((x1 + x2) / 2.0 - roi_left) / roi_width,
                ((y1 + y2) / 2.0 - roi_top) / roi_height,
                (x2 - x1) / roi_width,
                (y2 - y1) / roi_height,
            )
        )
        if len(self._history) < self.STABLE_FRAME_COUNT:
            return False

        spread = np.ptp(np.asarray(self._history, dtype=np.float32), axis=0)
        return bool(
            spread[0] <= 0.035
            and spread[1] <= 0.035
            and spread[2] <= 0.06
            and spread[3] <= 0.06
        )

    @classmethod
    def _estimate_pose(
        cls,
        landmarks: tuple[tuple[float, float, float], ...],
        frame_width: int,
        frame_height: int,
    ) -> tuple[float, float, float] | None:
        if len(landmarks) != 5 or any(point[2] < 0.2 for point in landmarks):
            return None

        image_points = np.asarray(
            [(point[0], point[1]) for point in landmarks], dtype=np.float64
        )
        focal_length = float(max(frame_width, frame_height))
        camera_matrix = np.array(
            [
                [focal_length, 0.0, frame_width / 2.0],
                [0.0, focal_length, frame_height / 2.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
        try:
            success, rotation_vector, _ = cv2.solvePnP(
                cls._MODEL_POINTS,
                image_points,
                camera_matrix,
                np.zeros((4, 1), dtype=np.float64),
                flags=cv2.SOLVEPNP_EPNP,
            )
        except cv2.error:
            return None
        if not success:
            return None

        rotation, _ = cv2.Rodrigues(rotation_vector)
        sy = math.sqrt(rotation[0, 0] ** 2 + rotation[1, 0] ** 2)
        singular = sy < 1e-6
        if singular:
            pitch = math.atan2(-rotation[2, 0], sy)
            yaw = math.atan2(-rotation[1, 2], rotation[1, 1])
            roll = 0.0
        else:
            pitch = math.atan2(-rotation[2, 0], sy)
            yaw = math.atan2(rotation[1, 0], rotation[0, 0])
            roll = math.atan2(rotation[2, 1], rotation[2, 2])
        return tuple(math.degrees(angle) for angle in (yaw, pitch, roll))

    @staticmethod
    def _guidance(issues: list[str], stable: bool) -> str:
        messages = {
            "small": "Mặt hơi xa, vui lòng đưa mặt lại gần camera.",
            "large": "Bạn đang hơi gần, vui lòng lùi lại một chút.",
            "framing": "Đưa khuôn mặt vào giữa vùng, tránh sát mép.",
            "blur": "Ảnh chưa đủ nét, vui lòng giữ yên một chút.",
            "dark": "Mặt hơi tối, vui lòng đứng ở nơi đủ sáng.",
            "bright": "Mặt bị quá sáng, vui lòng tránh nguồn sáng chiếu trực tiếp.",
            "pose_unknown": "Chưa xác định được góc mặt, vui lòng nhìn rõ vào camera.",
            "pose_turn": "Vui lòng nhìn thẳng vào camera.",
            "pose_tilt": "Vui lòng giữ đầu thẳng.",
        }
        for issue in (
            "small",
            "large",
            "framing",
            "blur",
            "dark",
            "bright",
            "pose_unknown",
            "pose_turn",
            "pose_tilt",
        ):
            if issue in issues:
                return messages[issue]
        if stable:
            return "Chất lượng đạt, vui lòng giữ nguyên."
        return "Chất lượng ổn, vui lòng giữ nguyên để kiểm tra thêm."

    @staticmethod
    def _format_details(
        width_ratio: float,
        height_ratio: float,
        blur_score: float,
        brightness: float,
        pose: tuple[float, float, float] | None,
        stable: bool,
    ) -> str:
        size_text = f"Face size: {width_ratio:.0%} × {height_ratio:.0%} ROI"
        blur_text = f"Blur: {blur_score:.0f}"
        brightness_text = f"Brightness: {brightness:.0f}/255"
        if pose is None:
            pose_text = "Pose: unavailable"
        else:
            yaw, pitch, roll = pose
            pose_text = f"Pose: yaw {yaw:.0f}°, pitch {pitch:.0f}°, roll {roll:.0f}°"
        stability_text = "stable" if stable else "checking stability"
        return " · ".join(
            (size_text, blur_text, brightness_text, pose_text, stability_text)
        )
