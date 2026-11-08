"""Time-window aggregation for recognition-page guidance only."""

from __future__ import annotations

from collections import Counter, deque

from config import settings


class GuidanceAggregator:
    PRIORITY = ("QUALITY_FAIL", "POSE_FAIL", "FAS_FAIL")
    MESSAGES = {
        "NO_FACE": "Đưa một khuôn mặt vào vùng giữa.",
        "MULTIPLE_FACES": "Chỉ để một người trong vùng nhận diện.",
        "POSE_FAIL": "Vui lòng điều chỉnh góc mặt và nhìn rõ vào camera.",
        "QUALITY_FAIL": "Cải thiện ánh sáng, độ nét hoặc khoảng cách tới camera.",
        "FAS_FAIL": "Không xác nhận được khuôn mặt thật; vui lòng thử lại.",
        "CHECKING": "Đang kiểm tra khuôn mặt…",
        "RECOGNIZING": "Đang nhận diện…",
        "TECHNICAL_ERROR": "Pipeline gặp lỗi kỹ thuật; vui lòng kiểm tra model hoặc log.",
    }
    TECHNICAL_OUTCOMES = {"ERROR", "ALIGNMENT_FAIL", "EMBEDDING_ERROR"}

    def __init__(self) -> None:
        self.window_seconds = settings.RECOGNITION_UI_WINDOW_SECONDS
        self.min_samples = settings.RECOGNITION_UI_MIN_SAMPLES
        self.no_face_debounce = settings.RECOGNITION_NO_FACE_DEBOUNCE
        self.multiple_debounce = settings.RECOGNITION_MULTIPLE_FACES_DEBOUNCE
        self.events: deque[tuple[float, str, int | None, str | None]] = deque()
        self.last_guidance = "CHECKING"
        self._special_streak = 0
        self._special_candidate = ""
        self._track_id: int | None = None

    def add(
        self,
        timestamp: float,
        outcome: str,
        track_id: int | None,
        message: str | None = None,
    ) -> None:
        if self._track_id is not None and track_id != self._track_id:
            self.events.clear()
            self.last_guidance = "CHECKING"
            self._special_streak = 0
            self._special_candidate = ""
        self._track_id = track_id
        if outcome in {"NO_FACE", "MULTIPLE_FACES"}:
            self._special_streak = (
                self._special_streak + 1
                if outcome == self._special_candidate
                else 1
            )
            self._special_candidate = outcome
        else:
            self._special_streak = 0
            self._special_candidate = ""
        self.events.append((timestamp, outcome, track_id, message))
        self._prune(timestamp)

    def _prune(self, now: float) -> None:
        while self.events and now - self.events[0][0] > self.window_seconds:
            self.events.popleft()

    def guidance(self, now: float, *, recognizing: bool = False) -> str:
        self._prune(now)
        if recognizing:
            self.last_guidance = "RECOGNIZING"
            return self.MESSAGES[self.last_guidance]
        if not self.events:
            self.last_guidance = "CHECKING"
            return self.MESSAGES[self.last_guidance]

        outcomes = [outcome for _, outcome, _, _ in self.events]
        if outcomes[-1] in self.TECHNICAL_OUTCOMES:
            self.last_guidance = "TECHNICAL_ERROR"
            return self.MESSAGES[self.last_guidance]
        special = outcomes[-1] if outcomes[-1] in {"NO_FACE", "MULTIPLE_FACES"} else None
        if special:
            required = self.no_face_debounce if special == "NO_FACE" else self.multiple_debounce
            if self._special_candidate == special and self._special_streak >= required:
                self.last_guidance = special
                return self._message_for(special)

        if len(outcomes) < self.min_samples:
            return self.MESSAGES.get(self.last_guidance, self.MESSAGES["CHECKING"])
        counts = Counter(outcome for outcome in outcomes if outcome in self.PRIORITY)
        if not counts:
            self.last_guidance = "CHECKING"
        else:
            self.last_guidance = min(
                counts, key=lambda outcome: (-counts[outcome], self.PRIORITY.index(outcome))
            )
        return self._message_for(self.last_guidance)

    def _message_for(self, outcome: str) -> str:
        custom_messages = [
            message
            for _, event_outcome, _, message in self.events
            if event_outcome == outcome and message
        ]
        if custom_messages:
            return Counter(custom_messages).most_common(1)[0][0]
        return self.MESSAGES[outcome]
