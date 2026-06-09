from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from math import hypot
from statistics import mean, pstdev

from apps.behavior.models import BehaviorSession, KeystrokeEvent, MouseEvent

logger = logging.getLogger(__name__)

# Repetition boundary detection constants (Tukey's fence on inter-keyup gaps)
MIN_GAP_THRESHOLD_MS: int = 400
MIN_KEYSTROKES_FOR_SPLITTING: int = 15
TUKEY_FENCE_MULTIPLIER: int = 3


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
        """Extract a single aggregated feature vector from the whole session."""
        keystrokes = list(session.keystroke_events.order_by("timestamp_ms", "id"))
        mouse_events = list(session.mouse_events.order_by("timestamp_ms", "id"))
        duration_ms = self._duration_ms(session, keystrokes, mouse_events)
        return self._extract_features_from_events(keystrokes, mouse_events, duration_ms)

    def extract_repetitions(self, session: BehaviorSession) -> list[BehaviorFeatures]:
        """Split an enrollment session into per-repetition feature vectors.

        Returns one BehaviorFeatures per detected repetition. Returns an empty
        list when the session has fewer than 5 keystrokes — not enough data for
        even one repetition.
        """
        keystrokes = list(session.keystroke_events.order_by("timestamp_ms", "id"))
        mouse_events = list(session.mouse_events.order_by("timestamp_ms", "id"))

        if len(keystrokes) < 5:
            return []

        boundaries = self._detect_repetition_boundaries(keystrokes)

        result: list[BehaviorFeatures] = []
        for start, end in boundaries:
            ks_slice = keystrokes[start:end]
            if not ks_slice:
                continue

            keydowns = [k for k in ks_slice if k.event_type == KeystrokeEvent.EventType.KEYDOWN]
            keyups = [k for k in ks_slice if k.event_type == KeystrokeEvent.EventType.KEYUP]

            if keydowns and keyups:
                duration_ms = max(keyups[-1].timestamp_ms - keydowns[0].timestamp_ms, 0)
            else:
                duration_ms = max(ks_slice[-1].timestamp_ms - ks_slice[0].timestamp_ms, 0)

            t_start = ks_slice[0].timestamp_ms
            t_end = ks_slice[-1].timestamp_ms
            ms_slice = [m for m in mouse_events if t_start <= m.timestamp_ms <= t_end]

            result.append(self._extract_features_from_events(ks_slice, ms_slice, duration_ms))

        return result

    def _detect_repetition_boundaries(
        self,
        keystrokes: list[KeystrokeEvent],
    ) -> list[tuple[int, int]]:
        """Detect repetition boundaries using adaptive Tukey's fence on inter-keyup gaps.

        Returns list of (start_idx, end_idx) tuples into the keystrokes list,
        one per detected repetition. If no large gaps are found the entire
        session is returned as a single repetition.
        """
        if len(keystrokes) < MIN_KEYSTROKES_FOR_SPLITTING:
            return [(0, len(keystrokes))]

        keyup_positions = [
            (i, e.timestamp_ms)
            for i, e in enumerate(keystrokes)
            if e.event_type == KeystrokeEvent.EventType.KEYUP
        ]

        if len(keyup_positions) < 2:
            return [(0, len(keystrokes))]

        gaps = [
            t2 - t1
            for (_, t1), (_, t2) in zip(keyup_positions, keyup_positions[1:])
        ]
        threshold = self._compute_adaptive_gap_threshold(gaps)

        boundary_keyup_indices = [i for i, gap in enumerate(gaps) if gap > threshold]

        # Sanity-check: warn when boundary count diverges significantly from expected.
        # One repetition = 10 keystrokes (len('.tie5Roanl')), so expected boundaries
        # = (keyups // 10) - 1. Only fires when we have enough data (>= 80 keyups).
        if len(keyup_positions) >= 80:
            expected_boundaries = (len(keyup_positions) // 10) - 1
            if abs(len(boundary_keyup_indices) - expected_boundaries) >= 2:
                logger.warning(
                    "Unexpected number of repetition boundaries: "
                    "got %d, expected ~%d (keyups=%d, threshold=%.0f ms). "
                    "Session may be malformed.",
                    len(boundary_keyup_indices),
                    expected_boundaries,
                    len(keyup_positions),
                    threshold,
                )

        if not boundary_keyup_indices:
            return [(0, len(keystrokes))]

        # Each boundary splits after the last keyup of the current rep.
        # The next rep begins immediately after that keyup, which naturally
        # skips the first keydown of subsequent reps (those have abnormally
        # large flight_time_ms from the inter-repetition pause and would
        # skew per-rep flight statistics).
        boundaries: list[tuple[int, int]] = []
        last_start = 0
        for boundary_kup_idx in boundary_keyup_indices:
            end_in_keystrokes = keyup_positions[boundary_kup_idx][0] + 1
            boundaries.append((last_start, end_in_keystrokes))
            last_start = end_in_keystrokes
        boundaries.append((last_start, len(keystrokes)))

        return boundaries

    @staticmethod
    def _compute_adaptive_gap_threshold(gaps: list[int]) -> float:
        """Compute Tukey's fence: median + 3 × IQR, with a floor of MIN_GAP_THRESHOLD_MS.

        Robust to outliers — unlike mean/std, median and IQR are not pulled by
        the very large inter-repetition gaps we are trying to detect.
        """
        if len(gaps) < 4:
            return float(MIN_GAP_THRESHOLD_MS)

        sorted_gaps = sorted(gaps)
        n = len(sorted_gaps)
        q1 = sorted_gaps[n // 4]
        q3 = sorted_gaps[(3 * n) // 4]
        median = sorted_gaps[n // 2]
        iqr = q3 - q1

        adaptive = median + TUKEY_FENCE_MULTIPLIER * iqr
        return max(adaptive, float(MIN_GAP_THRESHOLD_MS))

    def _extract_features_from_events(
        self,
        keystrokes: list[KeystrokeEvent],
        mouse_events: list[MouseEvent],
        duration_ms: int,
    ) -> BehaviorFeatures:
        """Build a BehaviorFeatures vector from an explicit slice of events."""
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
            mouse_move_count=float(
                self._count_events(mouse_events, MouseEvent.EventType.MOVE)
            ),
            mouse_click_count=float(
                self._count_events(mouse_events, MouseEvent.EventType.CLICK)
            ),
            mouse_scroll_count=float(
                self._count_events(mouse_events, MouseEvent.EventType.SCROLL)
            ),
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
