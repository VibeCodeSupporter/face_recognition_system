"""ByteTrack adapter for model-independent face detections."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import supervision as sv
from trackers import ByteTrackTracker

from config.settings import FACE_TRACKER_LOST_BUFFER
from face.detector import FaceDetection


class ByteTrackFaceTracker:
    """Attach short-lived track IDs while preserving face landmarks."""

    def __init__(self) -> None:
        self._tracker = ByteTrackTracker(
            lost_track_buffer=FACE_TRACKER_LOST_BUFFER,
            frame_rate=30.0,
            track_activation_threshold=0.50,
            minimum_consecutive_frames=2,
            minimum_iou_threshold=0.10,
            high_conf_det_threshold=0.65,
        )

    def update(self, detections: list[FaceDetection]) -> list[FaceDetection]:
        boxes = np.asarray([item.bbox for item in detections], dtype=np.float32)
        if not detections:
            boxes = np.empty((0, 4), dtype=np.float32)
        tracker_input = sv.Detections(
            xyxy=boxes,
            confidence=np.asarray(
                [item.confidence for item in detections], dtype=np.float32
            ),
            data={"source_index": np.arange(len(detections), dtype=np.int64)},
        )
        tracked = self._tracker.update(tracker_input)
        source_indices = tracked.data.get("source_index", np.empty(0, dtype=np.int64))
        track_ids = tracked.tracker_id
        if track_ids is None:
            return detections

        ids_by_source = {
            int(source_index): int(track_id)
            for source_index, track_id in zip(source_indices, track_ids)
        }
        return [
            replace(item, track_id=ids_by_source.get(index, -1))
            for index, item in enumerate(detections)
        ]
