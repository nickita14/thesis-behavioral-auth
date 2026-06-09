from __future__ import annotations

from pathlib import Path

import pytest

from apps.ml_engine.behavior_features import BehaviorFeatures
from apps.ml_engine.datasets.cmu_loader import (
    CMU_DD_COLS,
    CMU_HOLD_COLS,
    CMU_UD_COLS,
    load_cmu_subjects,
)

# ---------------------------------------------------------------------------
# Fixture CSV helpers
# ---------------------------------------------------------------------------

_HEADER = (
    "subject,sessionIndex,rep,"
    + ",".join(CMU_HOLD_COLS)
    + ","
    + ",".join(CMU_DD_COLS)
    + ","
    + ",".join(CMU_UD_COLS)
)


def _make_row(
    subject: str,
    h_sec: float = 0.1,
    dd_sec: float = 0.05,
    ud_sec: float = 0.05,
    session_index: int = 1,
    rep: int = 1,
) -> str:
    h_vals  = [str(h_sec)]  * len(CMU_HOLD_COLS)
    dd_vals = [str(dd_sec)] * len(CMU_DD_COLS)
    ud_vals = [str(ud_sec)] * len(CMU_UD_COLS)
    cols = h_vals + dd_vals + ud_vals
    return f"{subject},{session_index},{rep}," + ",".join(cols)


def _write_fixture(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "fixture_cmu.csv"
    path.write_text(_HEADER + "\n" + "\n".join(rows) + "\n")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_load_cmu_subjects_parses_all_subjects(tmp_path):
    """Fixture with distinct subjects → one key per subject in result dict."""
    subjects = [f"s{i:03d}" for i in range(1, 8)]  # 7 unique subjects
    rows = [_make_row(s, rep=r) for s in subjects for r in range(1, 4)]
    path = _write_fixture(tmp_path, rows)

    result = load_cmu_subjects(path)

    assert set(result.keys()) == set(subjects)
    # Each subject has 3 repetitions
    for sid in subjects:
        assert len(result[sid]) == 3


def test_load_cmu_subjects_with_filter_returns_only_selected(tmp_path):
    """subject_filter narrows result to exactly the specified subjects."""
    rows = [
        _make_row("s001"), _make_row("s002"), _make_row("s003"),
    ]
    path = _write_fixture(tmp_path, rows)

    result = load_cmu_subjects(path, subject_filter=["s001", "s003"])

    assert "s001" in result
    assert "s003" in result
    assert "s002" not in result


def test_cmu_row_to_features_converts_seconds_to_milliseconds(tmp_path):
    """H.period = 0.1 s → avg_dwell_time_ms ≈ 100 ms (all keys identical)."""
    h_sec  = 0.1   # 100 ms
    ud_sec = 0.05  # 50 ms
    path = _write_fixture(tmp_path, [_make_row("s001", h_sec=h_sec, ud_sec=ud_sec)])

    features: BehaviorFeatures = load_cmu_subjects(path)["s001"][0]

    assert abs(features.avg_dwell_time_ms  - h_sec  * 1000) < 1e-6
    assert abs(features.avg_flight_time_ms - ud_sec * 1000) < 1e-6


def test_cmu_row_to_features_total_duration_correct(tmp_path):
    """session_duration_ms = sum(H) + sum(UD) = 11×h_ms + 10×ud_ms."""
    h_sec  = 0.1
    ud_sec = 0.05
    path = _write_fixture(tmp_path, [_make_row("s001", h_sec=h_sec, ud_sec=ud_sec)])

    features: BehaviorFeatures = load_cmu_subjects(path)["s001"][0]

    expected_ms = len(CMU_HOLD_COLS) * h_sec * 1000 + len(CMU_UD_COLS) * ud_sec * 1000
    assert abs(features.session_duration_ms - expected_ms) < 1e-6


def test_cmu_row_to_features_mouse_fields_are_zero(tmp_path):
    """CMU has no mouse data — all mouse fields must be 0.0."""
    path = _write_fixture(tmp_path, [_make_row("s001")])

    features: BehaviorFeatures = load_cmu_subjects(path)["s001"][0]

    assert features.mouse_event_count  == 0.0
    assert features.mouse_move_count   == 0.0
    assert features.mouse_click_count  == 0.0
    assert features.mouse_scroll_count == 0.0
    assert features.mouse_path_length  == 0.0
    assert features.avg_mouse_speed    == 0.0
    assert features.max_mouse_speed    == 0.0


def test_cmu_features_have_22_keystrokes(tmp_path):
    """11 keydowns + 11 keyups = 22 total keystroke events per repetition."""
    path = _write_fixture(tmp_path, [_make_row("s001")])

    features: BehaviorFeatures = load_cmu_subjects(path)["s001"][0]

    assert features.keydown_count   == 11.0
    assert features.keyup_count     == 11.0
    assert features.keystroke_count == 22.0
