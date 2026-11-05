"""Lightweight, model-independent face image quality checks."""

from __future__ import annotations

from dataclasses import dataclass
import math

import cv2
import numpy as np

from common.face_region import face_roi_bounds
from config import settings
from face.detector import FaceDetection
from face.embedding import has_reliable_landmarks


@dataclass(frozen=True)
class FaceQualityResult:
    """Metrics and user guidance for one face in the capture ROI."""

    passed: bool
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

    MIN_FACE_HEIGHT_RATIO = settings.FACE_QUALITY_MIN_FACE_HEIGHT_RATIO
    MIN_FACE_WIDTH_RATIO = settings.FACE_QUALITY_MIN_FACE_WIDTH_RATIO
    MAX_FACE_HEIGHT_RATIO = settings.FACE_QUALITY_MAX_FACE_HEIGHT_RATIO
    MAX_FACE_WIDTH_RATIO = settings.FACE_QUALITY_MAX_FACE_WIDTH_RATIO
    MIN_BLUR_SCORE = settings.FACE_QUALITY_MIN_BLUR_SCORE
    MIN_BRIGHTNESS = settings.FACE_QUALITY_MIN_BRIGHTNESS
    MAX_BRIGHTNESS = settings.FACE_QUALITY_MAX_BRIGHTNESS
    FRONT_MAX_YAW = settings.FACE_POSE_FRONT_MAX_YAW
    FRONT_MAX_PITCH = settings.FACE_POSE_FRONT_MAX_PITCH
    TURN_MIN_ANGLE = settings.FACE_POSE_TURN_MIN_ANGLE
    TURN_MAX_ANGLE = settings.FACE_POSE_TURN_MAX_ANGLE
    PITCH_MIN_ANGLE = settings.FACE_POSE_PITCH_MIN_ANGLE
    PITCH_MAX_ANGLE = settings.FACE_POSE_PITCH_MAX_ANGLE
    CROSS_AXIS_MAX_ANGLE = settings.FACE_POSE_CROSS_AXIS_MAX_ANGLE

    # Approximate 3-D landmarks in detector order. Image coordinates grow
    # downward, so the eye row is above the nose and mouth row below it.
    _MODEL_POINTS = np.array(
        [
            [-30.0, -30.0, -20.0],
            [30.0, -30.0, -20.0],
            [0.0, 0.0, 0.0],
            [-25.0, 30.0, -15.0],
            [25.0, 30.0, -15.0],
        ],
        dtype=np.float64,
    )

    def evaluate(
        self,
        frame_bgr: np.ndarray,
        detection: FaceDetection,
        *,
        pose_limits: tuple[float, float, float] | None = None,
        registration: bool = False,
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
        active_pose_limits = pose_limits
        if registration and active_pose_limits is None:
            active_pose_limits = (
                settings.FACE_QUALITY_REGISTRATION_MAX_YAW,
                settings.FACE_QUALITY_REGISTRATION_MAX_PITCH,
                settings.FACE_QUALITY_REGISTRATION_MAX_ROLL,
            )
        issues: list[str] = []

        min_height = settings.FACE_QUALITY_REGISTRATION_MIN_FACE_HEIGHT_RATIO if registration else self.MIN_FACE_HEIGHT_RATIO
        min_width = settings.FACE_QUALITY_REGISTRATION_MIN_FACE_WIDTH_RATIO if registration else self.MIN_FACE_WIDTH_RATIO
        max_height = settings.FACE_QUALITY_REGISTRATION_MAX_FACE_HEIGHT_RATIO if registration else self.MAX_FACE_HEIGHT_RATIO
        max_width = settings.FACE_QUALITY_REGISTRATION_MAX_FACE_WIDTH_RATIO if registration else self.MAX_FACE_WIDTH_RATIO
        min_blur = settings.FACE_QUALITY_REGISTRATION_MIN_BLUR_SCORE if registration else self.MIN_BLUR_SCORE
        min_brightness = settings.FACE_QUALITY_REGISTRATION_MIN_BRIGHTNESS if registration else self.MIN_BRIGHTNESS
        max_brightness = settings.FACE_QUALITY_REGISTRATION_MAX_BRIGHTNESS if registration else self.MAX_BRIGHTNESS
        if (
            height_ratio < min_height
            or width_ratio < min_width
        ):
            issues.append("small")
        elif (
            height_ratio > max_height
            or width_ratio > max_width
        ):
            issues.append("large")

        edge_margin_ratio = (
            settings.FACE_QUALITY_REGISTRATION_EDGE_MARGIN_RATIO
            if registration
            else settings.FACE_QUALITY_EDGE_MARGIN_RATIO
        )
        edge_margin_x = roi_width * edge_margin_ratio
        edge_margin_y = roi_height * edge_margin_ratio
        if (
            x1 <= roi_left + edge_margin_x
            or x2 >= roi_right - edge_margin_x
            or y1 <= roi_top + edge_margin_y
            or y2 >= roi_bottom - edge_margin_y
        ):
            issues.append("framing")
        if blur_score < min_blur:
            issues.append("blur")
        if brightness < min_brightness:
            issues.append("dark")
        elif brightness > max_brightness:
            issues.append("bright")
        if pose is None:
            issues.append("pose_unknown")
        elif active_pose_limits is not None:
            yaw, pitch, roll = pose
            yaw_limit, pitch_limit, roll_limit = active_pose_limits
            if abs(yaw) > yaw_limit or abs(pitch) > pitch_limit:
                issues.append("pose_turn")
            elif abs(roll) > roll_limit:
                issues.append("pose_tilt")

        passed = not issues
        guidance = self._guidance(issues)
        details = self._format_details(
            width_ratio, height_ratio, blur_score, brightness, pose
        )
        yaw, pitch, roll = pose if pose is not None else (None, None, None)
        return FaceQualityResult(
            passed=passed,
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

    @classmethod
    def _estimate_pose(
        cls,
        landmarks: tuple[tuple[float, float, float], ...],
        frame_width: int,
        frame_height: int,
    ) -> tuple[float, float, float] | None:
        if not has_reliable_landmarks(landmarks):
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
            yaw = math.atan2(-rotation[2, 0], sy)
            pitch = math.atan2(-rotation[1, 2], rotation[1, 1])
            roll = 0.0
        else:
            # Decompose the estimated rotation as yaw (vertical axis), pitch
            # (horizontal axis), then roll (camera-facing axis). The previous
            # extraction mislabeled these components, which made turn guidance
            # react to head tilt instead of left/right rotation.
            yaw = math.atan2(-rotation[2, 0], sy)
            pitch = math.atan2(rotation[2, 1], rotation[2, 2])
            roll = math.atan2(rotation[1, 0], rotation[0, 0])
        # Normalize this model's PnP sign to the UI convention: looking down
        # is positive pitch and looking up is negative pitch.
        pitch = -pitch
        return tuple(math.degrees(angle) for angle in (yaw, pitch, roll))

    @classmethod
    def estimate_pose(
        cls,
        landmarks: tuple[tuple[float, float, float], ...],
        frame_width: int,
        frame_height: int,
    ) -> tuple[float, float, float] | None:
        """Expose the same landmark pose estimate used by quality evaluation."""
        return cls._estimate_pose(landmarks, frame_width, frame_height)

    @classmethod
    def matches_capture_pose(
        cls,
        pose_key: str,
        pose: tuple[float, float, float] | None,
        neutral_pose: tuple[float, float] | None = None,
    ) -> tuple[bool, str]:
        """Check the requested enrollment direction before costly processing."""
        if pose is None:
            return False, "Chưa xác định được góc mặt, vui lòng nhìn rõ vào camera."

        yaw, pitch, _ = pose
        if pose_key == "front":
            if abs(yaw) > cls.FRONT_MAX_YAW or abs(pitch) > cls.FRONT_MAX_PITCH:
                return False, "Vui lòng nhìn thẳng vào camera, giữ đầu không nghiêng hoặc cúi/ngửa."
            return True, "Nhìn thẳng vào camera."
        if pose_key in {"left", "right"}:
            direction = 1.0 if pose_key == "left" else -1.0
            neutral_yaw, neutral_pitch = neutral_pose or (0.0, 0.0)
            directed_yaw = (yaw - neutral_yaw) * direction
            side = "trái" if pose_key == "left" else "phải"
            if directed_yaw < cls.TURN_MIN_ANGLE:
                return False, f"Quay nhẹ sang {side}."
            if directed_yaw > cls.TURN_MAX_ANGLE:
                return False, "Bạn quay hơi nhiều, quay lại nhẹ một chút."
            return (
                abs(pitch - neutral_pitch) <= cls.CROSS_AXIS_MAX_ANGLE,
                "Giữ đầu tự nhiên, chỉ quay mặt sang bên.",
            )

        # With this pose decomposition, looking down is positive pitch and
        # looking up is negative pitch.
        neutral_yaw, neutral_pitch = neutral_pose or (0.0, 0.0)
        direction = 1.0 if pose_key == "down" else -1.0
        directed_pitch = (pitch - neutral_pitch) * direction
        if directed_pitch < cls.PITCH_MIN_ANGLE:
            return False, "Cúi nhẹ xuống." if pose_key == "down" else "Ngửa nhẹ lên."
        if directed_pitch > cls.PITCH_MAX_ANGLE:
            return False, "Góc hơi nhiều, trở lại nhẹ một chút."
        return (
            abs(yaw - neutral_yaw) <= cls.CROSS_AXIS_MAX_ANGLE,
            "Giữ mặt hướng về trước, chỉ thay đổi nhẹ góc lên/xuống.",
        )

    @staticmethod
    def _guidance(issues: list[str]) -> str:
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
        return "Chất lượng đạt, vui lòng giữ nguyên."

    @staticmethod
    def _format_details(
        width_ratio: float,
        height_ratio: float,
        blur_score: float,
        brightness: float,
        pose: tuple[float, float, float] | None,
    ) -> str:
        size_text = f"Face size: {width_ratio:.0%} × {height_ratio:.0%} ROI"
        blur_text = f"Blur: {blur_score:.0f}"
        brightness_text = f"Brightness: {brightness:.0f}/255"
        if pose is None:
            pose_text = "Pose: unavailable"
        else:
            yaw, pitch, roll = pose
            pose_text = f"Pose: yaw {yaw:.0f}°, pitch {pitch:.0f}°, roll {roll:.0f}°"
        return " · ".join((size_text, blur_text, brightness_text, pose_text))
