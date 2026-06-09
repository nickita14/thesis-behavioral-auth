from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pytest

from apps.ml_engine.behavior_features import BehaviorFeatures
from apps.ml_engine.evaluation import (
    CrossUserMatrixResult,
    EvaluationMetrics,
    SubjectData,
    compute_metrics,
    evaluate_cross_user,
    prepare_subjects_data,
    score_features,
    train_subject_model,
)
from apps.ml_engine.models import EvaluationDataset, EvaluationSubject

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RNG = np.random.default_rng(99)


def _make_features(
    n: int,
    dwell_centre: float = 80.0,
    flight_centre: float = 40.0,
    seed: int = 0,
) -> list[BehaviorFeatures]:
    rng = np.random.default_rng(seed)
    return [
        BehaviorFeatures(
            session_duration_ms=float(rng.normal(1200, 100)),
            keystroke_count=22.0,
            keydown_count=11.0,
            keyup_count=11.0,
            avg_dwell_time_ms=float(rng.normal(dwell_centre, 8)),
            std_dwell_time_ms=float(abs(rng.normal(8, 1))),
            avg_flight_time_ms=float(rng.normal(flight_centre, 5)),
            std_flight_time_ms=float(abs(rng.normal(4, 0.5))),
            typing_speed_keys_per_second=float(rng.normal(5.0, 0.4)),
            mouse_event_count=0.0,
            mouse_move_count=0.0,
            mouse_click_count=0.0,
            mouse_scroll_count=0.0,
            mouse_path_length=0.0,
            avg_mouse_speed=0.0,
            max_mouse_speed=0.0,
        )
        for _ in range(n)
    ]


def _make_evaluation_subject(dataset, subject_id: str, n: int, seed: int = 0):
    features = _make_features(n, seed=seed)
    EvaluationSubject.objects.create(
        dataset=dataset,
        subject_id=subject_id,
        feature_vectors=[asdict(f) for f in features],
        metadata={"n_repetitions": n},
    )


# ---------------------------------------------------------------------------
# 1. prepare_subjects_data — 80/20 split
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_prepare_subjects_data_80_20_split():
    dataset = EvaluationDataset.objects.create(name="test_ds_split")
    _make_evaluation_subject(dataset, "s001", n=100)

    subjects = prepare_subjects_data(dataset_names=["test_ds_split"])

    assert len(subjects) == 1
    sd = subjects[0]
    assert len(sd.train_features) == 80
    assert len(sd.test_features) == 20


# ---------------------------------------------------------------------------
# 2. prepare_subjects_data — reproducible seed
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_prepare_subjects_data_reproducible_seed():
    dataset = EvaluationDataset.objects.create(name="test_ds_seed")
    _make_evaluation_subject(dataset, "s001", n=50)

    first  = prepare_subjects_data(dataset_names=["test_ds_seed"], seed=7)
    second = prepare_subjects_data(dataset_names=["test_ds_seed"], seed=7)

    # Identical train split under the same seed
    assert [f.avg_dwell_time_ms for f in first[0].train_features] == [
        f.avg_dwell_time_ms for f in second[0].train_features
    ]


# ---------------------------------------------------------------------------
# 3. train_subject_model — returns fitted IsolationForest
# ---------------------------------------------------------------------------


def test_train_subject_model_returns_fitted():
    features = _make_features(50)
    model = train_subject_model(features)
    assert hasattr(model, "estimators_"), "model must be fitted"
    assert len(model.estimators_) == 100


# ---------------------------------------------------------------------------
# 4. score_features — returns list of floats
# ---------------------------------------------------------------------------


def test_score_features_returns_list_of_floats():
    features = _make_features(50)
    model = train_subject_model(features)
    scores = score_features(model, features[:10])
    assert isinstance(scores, list)
    assert len(scores) == 10
    assert all(isinstance(s, float) for s in scores)


# ---------------------------------------------------------------------------
# 5. score_features — empty input returns empty list
# ---------------------------------------------------------------------------


def test_score_features_empty_input_returns_empty():
    features = _make_features(50)
    model = train_subject_model(features)
    assert score_features(model, []) == []


# ---------------------------------------------------------------------------
# 6. compute_metrics — perfect separation → EER ≈ 0, AUC ≈ 1
# ---------------------------------------------------------------------------


def test_compute_metrics_perfect_separation():
    genuine  = [0.1] * 100
    impostor = [0.9] * 100
    m = compute_metrics(genuine, impostor)
    assert m.eer < 0.05
    assert m.auc > 0.95
    assert isinstance(m, EvaluationMetrics)


# ---------------------------------------------------------------------------
# 7. compute_metrics — no separation → EER ≈ 0.5, AUC ≈ 0.5
# ---------------------------------------------------------------------------


def test_compute_metrics_no_separation():
    rng = np.random.default_rng(0)
    scores = rng.uniform(0.3, 0.7, 200).tolist()
    genuine  = scores[:100]
    impostor = scores[100:]
    m = compute_metrics(genuine, impostor)
    assert m.eer > 0.3
    assert m.auc < 0.7


# ---------------------------------------------------------------------------
# 8. evaluate_cross_user — returns correct number of per_subject_results
# ---------------------------------------------------------------------------


def test_evaluate_cross_user_returns_n_results():
    subjects = [
        SubjectData(
            subject_id=f"s{i:03d}",
            train_features=_make_features(80, dwell_centre=80 + i * 50, seed=i),
            test_features=_make_features(20, dwell_centre=80 + i * 50, seed=i + 100),
            source_dataset="synthetic",
        )
        for i in range(3)
    ]

    result = evaluate_cross_user(subjects, scope_name="test_scope")

    assert isinstance(result, CrossUserMatrixResult)
    assert len(result.per_subject_results) == 3
    assert result.n_subjects == 3
    assert result.scope_name == "test_scope"
    # cross_user_scores holds n² pairs (including self-vs-self)
    assert len(result.cross_user_scores) == 9
