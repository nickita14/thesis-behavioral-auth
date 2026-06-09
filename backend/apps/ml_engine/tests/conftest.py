from __future__ import annotations

import pytest
from django.utils import timezone

from apps.behavior.models import BehaviorSession, KeystrokeEvent


@pytest.fixture
def make_enrollment_session(db):
    """Factory fixture — creates a complete enrollment BehaviorSession.

    Parameters
    ----------
    user : AUTH_USER_MODEL instance
    n_repetitions : int
        Number of phrase repetitions to simulate (default 5).
    dwell_ms : int
        Key-hold duration per keystroke in ms (default 100).
    flight_ms : int
        Time between consecutive keys within a repetition in ms (default 200).

    Returns the created BehaviorSession.
    """

    def _make(user, n_repetitions: int = 10, dwell_ms: int = 100, flight_ms: int = 200):
        session = BehaviorSession.objects.create(
            user=user,
            is_enrollment=True,
            ended_at=timezone.now(),
            context={},
        )

        # Each repetition simulates 10 keystrokes (len('.tie5Roanl'))
        keys_per_rep = 10
        rep_duration_ms = (keys_per_rep - 1) * (dwell_ms + flight_ms) + dwell_ms
        inter_rep_pause_ms = 1000  # large gap so boundary detection fires

        for rep_idx in range(n_repetitions):
            rep_start = rep_idx * (rep_duration_ms + inter_rep_pause_ms)

            for key_idx in range(keys_per_rep):
                down_ts = rep_start + key_idx * (dwell_ms + flight_ms)
                up_ts = down_ts + dwell_ms
                # First key of the very first rep has no prior keyup, so no flight
                flight = flight_ms if (rep_idx > 0 or key_idx > 0) else None

                KeystrokeEvent.objects.create(
                    behavior_session=session,
                    event_type=KeystrokeEvent.EventType.KEYDOWN,
                    key_code="letter",
                    timestamp_ms=down_ts,
                    relative_time_ms=down_ts,
                    flight_time_ms=flight,
                )
                KeystrokeEvent.objects.create(
                    behavior_session=session,
                    event_type=KeystrokeEvent.EventType.KEYUP,
                    key_code="letter",
                    timestamp_ms=up_ts,
                    relative_time_ms=up_ts,
                    dwell_time_ms=dwell_ms,
                )

        return session

    return _make
