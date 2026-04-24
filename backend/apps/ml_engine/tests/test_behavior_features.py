from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.behavior.models import BehaviorSession, KeystrokeEvent, MouseEvent
from apps.ml_engine.behavior_detectors import (
    DECISION_LEGITIMATE,
    DECISION_SUSPICIOUS,
    BehaviorAnomalyDetector,
)
from apps.ml_engine.behavior_features import BehaviorFeatureExtractor, BehaviorFeatures


@pytest.fixture
def extractor() -> BehaviorFeatureExtractor:
    return BehaviorFeatureExtractor()


@pytest.fixture
def behavior_session(db) -> BehaviorSession:
    return BehaviorSession.objects.create(context={"page": "transaction"})


@pytest.mark.django_db
def test_empty_session_returns_zero_features(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    features = extractor.extract(behavior_session)

    assert features == BehaviorFeatures()


@pytest.mark.django_db
def test_keystroke_stats_counted_correctly(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    started_at = timezone.now()
    behavior_session.started_at = started_at
    behavior_session.ended_at = started_at + timedelta(seconds=2)
    behavior_session.save(update_fields=["started_at", "ended_at"])
    KeystrokeEvent.objects.create(
        behavior_session=behavior_session,
        event_type=KeystrokeEvent.EventType.KEYDOWN,
        key_code="KeyA",
        key_value_hash="hash-a",
        timestamp_ms=100,
        relative_time_ms=100,
    )
    KeystrokeEvent.objects.create(
        behavior_session=behavior_session,
        event_type=KeystrokeEvent.EventType.KEYUP,
        key_code="KeyA",
        key_value_hash="hash-a",
        timestamp_ms=200,
        relative_time_ms=200,
        dwell_time_ms=100,
        flight_time_ms=40,
    )
    KeystrokeEvent.objects.create(
        behavior_session=behavior_session,
        event_type=KeystrokeEvent.EventType.KEYUP,
        key_code="KeyB",
        key_value_hash="hash-b",
        timestamp_ms=350,
        relative_time_ms=350,
        dwell_time_ms=200,
        flight_time_ms=80,
    )

    features = extractor.extract(behavior_session)

    assert features.session_duration_ms == 2000
    assert features.keystroke_count == 3
    assert features.keydown_count == 1
    assert features.keyup_count == 2
    assert features.avg_dwell_time_ms == 150
    assert features.std_dwell_time_ms == 50
    assert features.avg_flight_time_ms == 60
    assert features.std_flight_time_ms == 20
    assert features.typing_speed_keys_per_second == 1


@pytest.mark.django_db
def test_mouse_counts_counted_correctly(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    MouseEvent.objects.create(
        behavior_session=behavior_session,
        event_type=MouseEvent.EventType.MOVE,
        x=0,
        y=0,
        timestamp_ms=0,
        relative_time_ms=0,
    )
    MouseEvent.objects.create(
        behavior_session=behavior_session,
        event_type=MouseEvent.EventType.CLICK,
        x=1,
        y=1,
        timestamp_ms=100,
        relative_time_ms=100,
    )
    MouseEvent.objects.create(
        behavior_session=behavior_session,
        event_type=MouseEvent.EventType.SCROLL,
        scroll_delta_y=12,
        timestamp_ms=200,
        relative_time_ms=200,
    )

    features = extractor.extract(behavior_session)

    assert features.mouse_event_count == 3
    assert features.mouse_move_count == 1
    assert features.mouse_click_count == 1
    assert features.mouse_scroll_count == 1


@pytest.mark.django_db
def test_mouse_path_length_counted_correctly(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    points = [(0, 0, 0), (1000, 3, 4), (2000, 6, 8)]
    for timestamp, x, y in points:
        MouseEvent.objects.create(
            behavior_session=behavior_session,
            event_type=MouseEvent.EventType.MOVE,
            x=x,
            y=y,
            timestamp_ms=timestamp,
            relative_time_ms=timestamp,
        )

    features = extractor.extract(behavior_session)

    assert features.mouse_path_length == 10
    assert features.avg_mouse_speed == 5
    assert features.max_mouse_speed == 5


@pytest.mark.django_db
def test_no_raw_key_values_required(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    KeystrokeEvent.objects.create(
        behavior_session=behavior_session,
        event_type=KeystrokeEvent.EventType.KEYUP,
        key_code="KeyA",
        key_value_hash="only-a-hash",
        timestamp_ms=100,
        relative_time_ms=100,
        dwell_time_ms=50,
    )

    features = extractor.extract(behavior_session)

    assert features.keystroke_count == 1
    assert features.avg_dwell_time_ms == 50
    assert not hasattr(KeystrokeEvent, "key_value")


def test_vector_order_stable() -> None:
    features = BehaviorFeatures(
        session_duration_ms=1,
        keystroke_count=2,
        keydown_count=3,
        keyup_count=4,
        avg_dwell_time_ms=5,
        std_dwell_time_ms=6,
        avg_flight_time_ms=7,
        std_flight_time_ms=8,
        typing_speed_keys_per_second=9,
        mouse_event_count=10,
        mouse_move_count=11,
        mouse_click_count=12,
        mouse_scroll_count=13,
        mouse_path_length=14,
        avg_mouse_speed=15,
        max_mouse_speed=16,
    )

    assert BehaviorFeatures.feature_names() == [
        "session_duration_ms",
        "keystroke_count",
        "keydown_count",
        "keyup_count",
        "avg_dwell_time_ms",
        "std_dwell_time_ms",
        "avg_flight_time_ms",
        "std_flight_time_ms",
        "typing_speed_keys_per_second",
        "mouse_event_count",
        "mouse_move_count",
        "mouse_click_count",
        "mouse_scroll_count",
        "mouse_path_length",
        "avg_mouse_speed",
        "max_mouse_speed",
    ]
    assert features.to_vector() == [float(value) for value in range(1, 17)]


def test_detector_can_fit_and_predict() -> None:
    training = [
        BehaviorFeatures(session_duration_ms=1000, keystroke_count=10, mouse_event_count=20),
        BehaviorFeatures(session_duration_ms=1100, keystroke_count=11, mouse_event_count=22),
        BehaviorFeatures(session_duration_ms=900, keystroke_count=9, mouse_event_count=18),
        BehaviorFeatures(session_duration_ms=1050, keystroke_count=10, mouse_event_count=21),
    ]
    detector = BehaviorAnomalyDetector(contamination=0.25).fit(training)

    result = detector.predict(training[0])

    assert isinstance(result.anomaly_score, float)
    assert isinstance(result.is_anomaly, bool)
    assert result.decision in {DECISION_LEGITIMATE, "anomalous"}


def test_detector_handles_unfitted_state_safely() -> None:
    detector = BehaviorAnomalyDetector()

    result = detector.predict(BehaviorFeatures())

    assert result.anomaly_score == 0
    assert result.is_anomaly is False
    assert result.decision == DECISION_SUSPICIOUS
    assert detector.score(BehaviorFeatures()) == 0
