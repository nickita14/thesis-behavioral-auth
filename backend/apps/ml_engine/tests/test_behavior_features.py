from __future__ import annotations

import types
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.behavior.models import BehaviorSession, KeystrokeEvent, MouseEvent
from apps.ml_engine.behavior_detectors import (
    DECISION_LEGITIMATE,
    DECISION_SUSPICIOUS,
    BehaviorAnomalyDetector,
)
from apps.ml_engine.behavior_features import (
    MIN_GAP_THRESHOLD_MS,
    BehaviorFeatureExtractor,
    BehaviorFeatures,
)


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


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_ks(event_type: str, timestamp_ms: int) -> types.SimpleNamespace:
    """Lightweight keystroke stand-in for non-DB boundary tests."""
    return types.SimpleNamespace(event_type=event_type, timestamp_ms=timestamp_ms)


def _make_fake_enrollment(
    reps: int = 5,
    chars_per_rep: int = 10,
    dwell: int = 100,
    intra_flight: int = 200,
    inter_pause: int = 800,
) -> list[types.SimpleNamespace]:
    """Generate alternating keydown/keyup pairs simulating typed enrollment phrases."""
    ks: list[types.SimpleNamespace] = []
    t = 200
    for _ in range(reps):
        for _ in range(chars_per_rep):
            ks.append(_fake_ks("keydown", t))
            t += dwell
            ks.append(_fake_ks("keyup", t))
            t += intra_flight
        t += inter_pause
    return ks


def _create_enrollment_keystrokes(
    session: BehaviorSession,
    reps: int = 5,
    chars_per_rep: int = 10,
    dwell: int = 100,
    intra_flight: int = 200,
    inter_pause: int = 800,
) -> None:
    """Persist keystroke events for an enrollment session into the test DB."""
    t = 200
    for _ in range(reps):
        for char_i in range(chars_per_rep):
            prev_keyup_t = t - intra_flight if char_i > 0 else None
            KeystrokeEvent.objects.create(
                behavior_session=session,
                event_type=KeystrokeEvent.EventType.KEYDOWN,
                key_code="letter",
                timestamp_ms=t,
                relative_time_ms=t,
                flight_time_ms=(intra_flight if prev_keyup_t is not None else None),
            )
            t += dwell
            KeystrokeEvent.objects.create(
                behavior_session=session,
                event_type=KeystrokeEvent.EventType.KEYUP,
                key_code="letter",
                timestamp_ms=t,
                relative_time_ms=t,
                dwell_time_ms=dwell,
            )
            t += intra_flight
        t += inter_pause


# ── Part 2, tests 1-10 ────────────────────────────────────────────────────────

def test_detect_boundaries_5_repetitions() -> None:
    """5 reps of 10 chars → exactly 4 inter-rep boundaries detected."""
    extractor = BehaviorFeatureExtractor()
    ks = _make_fake_enrollment(reps=5, chars_per_rep=10, dwell=100, intra_flight=200, inter_pause=800)

    boundaries = extractor._detect_repetition_boundaries(ks)

    assert len(boundaries) == 5
    # Each rep covers exactly 20 keystrokes (10 keydown + 10 keyup)
    for start, end in boundaries:
        assert end - start == 20


def test_detect_boundaries_no_gaps() -> None:
    """Uniform inter-keyup gaps below threshold → whole session is one repetition."""
    extractor = BehaviorFeatureExtractor()
    # dwell=100, intra_flight=100 → keyup gaps = 200ms, well below 400ms floor
    ks = _make_fake_enrollment(reps=3, chars_per_rep=10, dwell=100, intra_flight=100, inter_pause=200)

    boundaries = extractor._detect_repetition_boundaries(ks)

    assert boundaries == [(0, len(ks))]


def test_detect_boundaries_single_keystroke() -> None:
    """Below MIN_KEYSTROKES_FOR_SPLITTING → single boundary covering all, no crash."""
    extractor = BehaviorFeatureExtractor()
    ks = [_fake_ks("keydown", 0), _fake_ks("keyup", 100)]

    boundaries = extractor._detect_repetition_boundaries(ks)

    assert boundaries == [(0, 2)]


@pytest.mark.django_db
def test_extract_repetitions_returns_5_for_enrollment_session(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    """Enrollment session with 5 reps produces 5 BehaviorFeatures."""
    _create_enrollment_keystrokes(behavior_session)

    reps = extractor.extract_repetitions(behavior_session)

    assert len(reps) == 5


@pytest.mark.django_db
def test_extract_repetitions_features_are_similar(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    """Uniform dwell across all reps → avg_dwell_time_ms consistent per rep."""
    _create_enrollment_keystrokes(behavior_session, dwell=120)

    reps = extractor.extract_repetitions(behavior_session)

    assert len(reps) == 5
    dwell_values = [r.avg_dwell_time_ms for r in reps]
    assert all(d == pytest.approx(120.0) for d in dwell_values)


@pytest.mark.django_db
def test_extract_repetitions_duration_is_correct(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    """Per-rep duration_ms reflects typing time, not wall-clock session time."""
    behavior_session.ended_at = timezone.now() + timedelta(hours=1)
    behavior_session.save(update_fields=["ended_at"])
    _create_enrollment_keystrokes(behavior_session, dwell=100, intra_flight=200)

    reps = extractor.extract_repetitions(behavior_session)

    assert len(reps) == 5
    wall_clock_ms = behavior_session.duration_ms
    for rep in reps:
        # Typing 10 chars: 9 inter-char intervals (300ms each) + last dwell → ~2800ms
        assert rep.session_duration_ms < wall_clock_ms
        assert rep.session_duration_ms > 0
        assert rep.session_duration_ms < 10_000


@pytest.mark.django_db
def test_extract_repetitions_empty_session(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    """Session with no keystrokes returns empty list."""
    reps = extractor.extract_repetitions(behavior_session)

    assert reps == []


@pytest.mark.django_db
def test_extract_repetitions_tiny_session(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    """Session with fewer than 5 keystrokes returns empty list."""
    for i in range(4):
        KeystrokeEvent.objects.create(
            behavior_session=behavior_session,
            event_type=KeystrokeEvent.EventType.KEYUP,
            key_code="letter",
            timestamp_ms=i * 200,
            relative_time_ms=i * 200,
            dwell_time_ms=100,
        )

    reps = extractor.extract_repetitions(behavior_session)

    assert reps == []


@pytest.mark.django_db
def test_existing_extract_still_works(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    """Backward-compat: extract() still returns a single BehaviorFeatures."""
    _create_enrollment_keystrokes(behavior_session)

    result = extractor.extract(behavior_session)

    assert isinstance(result, BehaviorFeatures)


@pytest.mark.django_db
def test_existing_extract_features_match_old_behavior(
    extractor: BehaviorFeatureExtractor,
    behavior_session: BehaviorSession,
) -> None:
    """Refactored extract() produces identical values to the original implementation."""
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


# ── Part 2, tests 11-15 (adaptive threshold) ─────────────────────────────────

def test_adaptive_threshold_handles_slow_typist() -> None:
    """Slow typist: intra-rep gaps ~600ms, inter-rep ~1400ms → 4 boundaries."""
    extractor = BehaviorFeatureExtractor()
    # dwell=200ms, intra_flight=400ms → intra-rep keyup gap = 600ms
    # inter_pause=800ms → inter-rep keyup gap = 800+200 = ~1000ms+ above intra
    ks = _make_fake_enrollment(dwell=200, intra_flight=400, inter_pause=800)

    boundaries = extractor._detect_repetition_boundaries(ks)

    # Adaptive threshold (median+3*IQR) should yield 5 slices, not 1 or 49
    assert len(boundaries) == 5


def test_min_threshold_floor_for_uniform_gaps() -> None:
    """Pathologically uniform gaps (IQR=0) use the MIN_GAP_THRESHOLD_MS floor."""
    extractor = BehaviorFeatureExtractor()
    # All gaps 100ms → IQR=0, adaptive=100 → floor=400 → nothing detected
    ks = _make_fake_enrollment(dwell=50, intra_flight=50, inter_pause=50)

    boundaries = extractor._detect_repetition_boundaries(ks)

    assert boundaries == [(0, len(ks))]


def test_compute_adaptive_threshold_basic() -> None:
    """IQR=0 → adaptive collapses to median, floor kicks in."""
    extractor = BehaviorFeatureExtractor()
    gaps = [100, 100, 100, 100, 1000]

    threshold = extractor._compute_adaptive_gap_threshold(gaps)

    # median=100, q1=100, q3=100, IQR=0 → adaptive=100 → floor=400
    assert threshold == float(MIN_GAP_THRESHOLD_MS)


def test_compute_adaptive_threshold_with_variance() -> None:
    """Non-zero IQR pushes threshold above floor."""
    extractor = BehaviorFeatureExtractor()
    gaps = [100, 200, 200, 300, 1500]

    threshold = extractor._compute_adaptive_gap_threshold(gaps)

    # n=5: q1=sorted[1]=200, q3=sorted[3]=300, median=sorted[2]=200
    # IQR=100, adaptive=200+300=500 → max(500, 400) = 500
    assert threshold == pytest.approx(500.0)


def test_warning_logged_for_unusual_repetition_count(caplog: pytest.LogCaptureFixture) -> None:
    """Warning fires when boundary count diverges from expected by ≥2.

    Uses 10 reps to satisfy the ≥80 keyups gate. All inter-keyup gaps are
    200ms ≤ 400ms floor, so 0 boundaries detected; |0 - 9| = 9 ≥ 2 → warning.
    """
    import logging

    extractor = BehaviorFeatureExtractor()
    # 10 reps × 10 chars = 100 keyups ≥ 80 → sanity check fires
    # all gaps = dwell + intra_flight = 200ms ≤ 400ms → 0 boundaries detected
    ks = _make_fake_enrollment(reps=10, dwell=100, intra_flight=100, inter_pause=100)

    with caplog.at_level(logging.WARNING, logger="apps.ml_engine.behavior_features"):
        extractor._detect_repetition_boundaries(ks)

    assert any("Unexpected number of repetition boundaries" in r.message for r in caplog.records)
