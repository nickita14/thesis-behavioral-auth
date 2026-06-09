from __future__ import annotations

import csv
import logging
from pathlib import Path
from statistics import mean, stdev
from typing import Iterable

from apps.ml_engine.behavior_features import BehaviorFeatures

logger = logging.getLogger(__name__)

# CMU Keystroke Dynamics Benchmark column names (Killourhy & Maxion, 2009)
# Password: .tie5Roanl → 11 distinct keys
# Reference: https://www.cs.cmu.edu/~keystroke/
CMU_HOLD_COLS = [
    'H.period', 'H.t', 'H.i', 'H.e', 'H.five',
    'H.Shift.r', 'H.o', 'H.a', 'H.n', 'H.l', 'H.Return',
]
CMU_DD_COLS = [
    'DD.period.t', 'DD.t.i', 'DD.i.e', 'DD.e.five', 'DD.five.Shift.r',
    'DD.Shift.r.o', 'DD.o.a', 'DD.a.n', 'DD.n.l', 'DD.l.Return',
]
CMU_UD_COLS = [
    'UD.period.t', 'UD.t.i', 'UD.i.e', 'UD.e.five', 'UD.five.Shift.r',
    'UD.Shift.r.o', 'UD.o.a', 'UD.a.n', 'UD.n.l', 'UD.l.Return',
]

CMU_FEATURE_COLUMNS = ['subject', 'sessionIndex', 'rep'] + CMU_HOLD_COLS + CMU_DD_COLS + CMU_UD_COLS

# .tie5Roanl: 11 distinct key presses → 11 keydown + 11 keyup = 22 events
_KEYSTROKES_PER_REP = 11


def load_cmu_subjects(
    csv_path: str | Path,
    subject_filter: list[str] | None = None,
) -> dict[str, list[BehaviorFeatures]]:
    """Load CMU dataset CSV into per-subject feature vectors.

    Each CMU CSV row represents one .tie5Roanl repetition typed by one subject.

    Parameters
    ----------
    csv_path : str | Path
        Path to DSL-StrongPasswordData.csv.
    subject_filter : list[str] | None
        If given, load only these subject IDs (e.g. ["s002", "s003"]).
        If None, load all subjects.

    Returns
    -------
    dict mapping subject_id → list[BehaviorFeatures], one vector per row.
    """
    subjects: dict[str, list[BehaviorFeatures]] = {}
    path = Path(csv_path)

    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject_id = row['subject']
            if subject_filter is not None and subject_id not in subject_filter:
                continue
            subjects.setdefault(subject_id, []).append(_cmu_row_to_features(row))

    logger.info("Loaded %d CMU subjects from %s", len(subjects), path)
    return subjects


def _cmu_row_to_features(row: dict[str, str]) -> BehaviorFeatures:
    """Convert one CMU CSV row (one password repetition) to BehaviorFeatures.

    CMU timing columns are in seconds; converted to milliseconds here.

    - H.* (hold/dwell): time from keydown to keyup for each key.
    - UD.* (keyUp-to-keyDown): time from keyup of key i to keydown of key i+1.
    - DD.* (keyDown-to-keyDown): not used — H + UD captures all timing information.
    - Mouse fields are zero: CMU has no mouse data.
    """
    hold_times_ms = [float(row[c]) * 1000 for c in CMU_HOLD_COLS]
    flight_times_ms = [float(row[c]) * 1000 for c in CMU_UD_COLS]

    total_duration_ms = sum(hold_times_ms) + sum(flight_times_ms)

    keyup_count = len(hold_times_ms)    # 11
    keydown_count = keyup_count          # 11
    keystroke_count = keyup_count + keydown_count  # 22

    typing_speed = (
        keyup_count / (total_duration_ms / 1000.0)
        if total_duration_ms > 0
        else 0.0
    )

    return BehaviorFeatures(
        session_duration_ms=total_duration_ms,
        keystroke_count=float(keystroke_count),
        keydown_count=float(keydown_count),
        keyup_count=float(keyup_count),
        avg_dwell_time_ms=mean(hold_times_ms),
        std_dwell_time_ms=stdev(hold_times_ms) if len(hold_times_ms) > 1 else 0.0,
        avg_flight_time_ms=mean(flight_times_ms),
        std_flight_time_ms=stdev(flight_times_ms) if len(flight_times_ms) > 1 else 0.0,
        typing_speed_keys_per_second=typing_speed,
        mouse_event_count=0.0,
        mouse_move_count=0.0,
        mouse_click_count=0.0,
        mouse_scroll_count=0.0,
        mouse_path_length=0.0,
        avg_mouse_speed=0.0,
        max_mouse_speed=0.0,
    )
