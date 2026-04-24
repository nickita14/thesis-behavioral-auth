from __future__ import annotations

from dataclasses import dataclass, fields
from math import hypot
from statistics import mean, pstdev

from apps.behavior.models import BehaviorSession, KeystrokeEvent, MouseEvent


@dataclass(frozen=True)
class BehaviorFeatures:
    """Numerical behavior feature vector for anomaly detection.

    The vector intentionally excludes raw typed values. Keystroke content is not
    needed for behavioral authentication; timing and movement metadata is enough
    for the first anomaly-detection baseline.
    """

    session_duration_ms: float = 0.0
    keystroke_count: float = 0.0
    keydown_count: float = 0.0
    keyup_count: float = 0.0
    avg_dwell_time_ms: float = 0.0
    std_dwell_time_ms: float = 0.0
    avg_flight_time_ms: float = 0.0
    std_flight_time_ms: float = 0.0
    typing_speed_keys_per_second: float = 0.0
    mouse_event_count: float = 0.0
    mouse_move_count: float = 0.0
    mouse_click_count: float = 0.0
    mouse_scroll_count: float = 0.0
    mouse_path_length: float = 0.0
    avg_mouse_speed: float = 0.0
    max_mouse_speed: float = 0.0

    def to_vector(self) -> list[float]:
        """Return a stable ML vector in dataclass field order."""
        return [float(getattr(self, field.name)) for field in fields(self)]

    @classmethod
    def feature_names(cls) -> list[str]:
        return [field.name for field in fields(cls)]


class BehaviorFeatureExtractor:
    """Extract ML-ready behavior features from persisted behavior events."""

    def extract(self, session: BehaviorSession) -> BehaviorFeatures:
        keystrokes = list(session.keystroke_events.order_by("timestamp_ms", "id"))
        mouse_events = list(session.mouse_events.order_by("timestamp_ms", "id"))

        duration_ms = self._duration_ms(session, keystrokes, mouse_events)
        dwell_times = [
            event.dwell_time_ms
            for event in keystrokes
            if event.dwell_time_ms is not None
        ]
        flight_times = [
            event.flight_time_ms
            for event in keystrokes
            if event.flight_time_ms is not None
        ]
        path_length, avg_speed, max_speed = self._mouse_movement_features(mouse_events)
        keydown_count = self._count_events(keystrokes, KeystrokeEvent.EventType.KEYDOWN)
        keyup_count = self._count_events(keystrokes, KeystrokeEvent.EventType.KEYUP)

        return BehaviorFeatures(
            session_duration_ms=float(duration_ms),
            keystroke_count=float(len(keystrokes)),
            keydown_count=float(keydown_count),
            keyup_count=float(keyup_count),
            avg_dwell_time_ms=self._avg(dwell_times),
            std_dwell_time_ms=self._std(dwell_times),
            avg_flight_time_ms=self._avg(flight_times),
            std_flight_time_ms=self._std(flight_times),
            typing_speed_keys_per_second=self._typing_speed(keyup_count, duration_ms),
            mouse_event_count=float(len(mouse_events)),
            mouse_move_count=float(self._count_events(mouse_events, MouseEvent.EventType.MOVE)),
            mouse_click_count=float(self._count_events(mouse_events, MouseEvent.EventType.CLICK)),
            mouse_scroll_count=float(self._count_events(mouse_events, MouseEvent.EventType.SCROLL)),
            mouse_path_length=path_length,
            avg_mouse_speed=avg_speed,
            max_mouse_speed=max_speed,
        )

    @staticmethod
    def _duration_ms(
        session: BehaviorSession,
        keystrokes: list[KeystrokeEvent],
        mouse_events: list[MouseEvent],
    ) -> int:
        if session.duration_ms is not None:
            return max(session.duration_ms, 0)
        relative_times = [
            event.relative_time_ms
            for event in [*keystrokes, *mouse_events]
            if event.relative_time_ms is not None
        ]
        return max(relative_times, default=0)

    @staticmethod
    def _count_events(events: list, event_type: str) -> int:
        return sum(1 for event in events if event.event_type == event_type)

    @staticmethod
    def _avg(values: list[int]) -> float:
        return float(mean(values)) if values else 0.0

    @staticmethod
    def _std(values: list[int]) -> float:
        return float(pstdev(values)) if len(values) > 1 else 0.0

    @staticmethod
    def _typing_speed(keyup_count: int, duration_ms: int) -> float:
        if duration_ms <= 0:
            return 0.0
        return keyup_count / (duration_ms / 1000)

    def _mouse_movement_features(
        self,
        events: list[MouseEvent],
    ) -> tuple[float, float, float]:
        points = [
            (event.relative_time_ms, event.x, event.y)
            for event in events
            if event.x is not None and event.y is not None
        ]
        if len(points) < 2:
            return 0.0, 0.0, 0.0

        path_length = 0.0
        max_speed = 0.0
        for (previous_t, previous_x, previous_y), (current_t, current_x, current_y) in zip(
            points,
            points[1:],
            strict=False,
        ):
            distance = hypot(current_x - previous_x, current_y - previous_y)
            path_length += distance
            elapsed_seconds = (current_t - previous_t) / 1000
            if elapsed_seconds > 0:
                max_speed = max(max_speed, distance / elapsed_seconds)

        total_elapsed_seconds = (points[-1][0] - points[0][0]) / 1000
        avg_speed = path_length / total_elapsed_seconds if total_elapsed_seconds > 0 else 0.0
        return float(path_length), float(avg_speed), float(max_speed)
