from __future__ import annotations

import io

import joblib
import numpy as np
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from sklearn.ensemble import IsolationForest

from apps.ml_engine.models import BehaviorProfile
from apps.ml_engine.training import (
    DETECTOR_VERSION,
    FEATURE_SCHEMA_VERSION,
    MIN_ENROLLMENT_SESSIONS,
    MIN_TRAINING_SAMPLES,
    BehaviorProfileTrainer,
)

User = get_user_model()


# ── helpers ────────────────────────────────────────────────────────────────


def _user(username: str = "trainer-test"):
    return User.objects.create_user(username=username, password="unused")


def _train_url() -> str:
    return reverse("ml_engine:train-profile")


def _status_url() -> str:
    return reverse("ml_engine:profile-status")


def _make_fitted_blob() -> bytes:
    """Return a minimal serialized IsolationForest fitted on dummy data."""
    rng = np.random.default_rng(42)
    X = rng.random((60, 16)).tolist()
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(X)
    buf = io.BytesIO()
    joblib.dump(model, buf)
    return buf.getvalue()


def _create_profile(user) -> BehaviorProfile:
    return BehaviorProfile.objects.create(
        user=user,
        model_blob=_make_fitted_blob(),
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        detector_version=DETECTOR_VERSION,
        n_training_sessions=10,
        n_training_samples=60,
        training_score_mean=0.4,
        training_score_std=0.05,
        is_active=True,
    )


# ── trainer unit tests ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_training_insufficient_sessions(make_enrollment_session) -> None:
    user = _user("insuf-sessions")
    for _ in range(2):
        make_enrollment_session(user)

    result = BehaviorProfileTrainer().train(user)

    assert result.success is False
    assert "Insufficient enrollment sessions" in result.error
    assert result.n_sessions == 2
    assert BehaviorProfile.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_training_insufficient_samples(make_enrollment_session) -> None:
    user = _user("insuf-samples")
    # 10 sessions × 2 reps = 20 samples < MIN_TRAINING_SAMPLES
    for _ in range(10):
        make_enrollment_session(user, n_repetitions=2)

    result = BehaviorProfileTrainer().train(user)

    assert result.success is False
    assert "Insufficient training samples" in result.error
    assert result.n_sessions == 10
    assert result.n_samples == 20


@pytest.mark.django_db
def test_training_happy_path(make_enrollment_session) -> None:
    user = _user("happy-path")
    for _ in range(5):
        make_enrollment_session(user)  # 10 reps each → 50 samples total

    result = BehaviorProfileTrainer().train(user)

    assert result.success is True
    assert result.n_sessions == 5
    assert result.n_samples == 50
    profile = BehaviorProfile.objects.get(user=user)
    assert profile.feature_schema_version == FEATURE_SCHEMA_VERSION
    assert profile.detector_version == DETECTOR_VERSION
    assert profile.n_training_samples == 50
    assert profile.training_score_mean is not None
    assert profile.is_active is True


@pytest.mark.django_db
def test_training_replaces_existing_profile(make_enrollment_session) -> None:
    user = _user("replace-profile")
    for _ in range(10):
        make_enrollment_session(user)
    BehaviorProfileTrainer().train(user)
    first_profile = BehaviorProfile.objects.get(user=user)

    # Train again with more sessions
    for _ in range(5):
        make_enrollment_session(user)
    BehaviorProfileTrainer().train(user)

    assert BehaviorProfile.objects.filter(user=user).count() == 1
    updated = BehaviorProfile.objects.get(user=user)
    assert updated.pk == first_profile.pk
    assert updated.n_training_sessions == 15


@pytest.mark.django_db
def test_training_skips_unended_sessions(make_enrollment_session) -> None:
    from apps.behavior.models import BehaviorSession

    user = _user("unended")
    for _ in range(2):
        make_enrollment_session(user)
    # 8 sessions without ended_at
    for _ in range(8):
        BehaviorSession.objects.create(user=user, is_enrollment=True, context={})

    result = BehaviorProfileTrainer().train(user)

    assert result.success is False
    assert result.n_sessions == 2  # only closed sessions counted


@pytest.mark.django_db
def test_training_skips_non_enrollment_sessions(make_enrollment_session) -> None:
    from apps.behavior.models import BehaviorSession
    from django.utils import timezone

    user = _user("non-enrollment")
    for _ in range(10):
        BehaviorSession.objects.create(
            user=user,
            is_enrollment=False,
            ended_at=timezone.now(),
            context={},
        )

    result = BehaviorProfileTrainer().train(user)

    assert result.success is False
    assert result.n_sessions == 0


@pytest.mark.django_db
def test_extraction_failure_in_one_session_does_not_abort_training(
    make_enrollment_session,
) -> None:
    from apps.behavior.models import BehaviorSession
    from django.utils import timezone

    user = _user("partial-failure")
    # 9 good sessions × 6 reps = 54 samples >= MIN_TRAINING_SAMPLES
    for _ in range(9):
        make_enrollment_session(user, n_repetitions=6)
    # 1 broken session: ended but has no keystrokes → extract_repetitions returns []
    BehaviorSession.objects.create(
        user=user,
        is_enrollment=True,
        ended_at=timezone.now(),
        context={},
    )

    result = BehaviorProfileTrainer().train(user)

    assert result.success is True
    assert result.n_sessions == 10
    assert result.n_samples == 54


def test_serialize_deserialize_round_trip() -> None:
    rng = np.random.default_rng(0)
    X_train = rng.random((50, 16)).tolist()
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(X_train)

    blob = BehaviorProfileTrainer._serialize_model(model)
    loaded = BehaviorProfileTrainer.deserialize_model(blob)

    X_test = rng.random((10, 16)).tolist()
    assert list(model.predict(X_test)) == list(loaded.predict(X_test))


# ── API endpoint tests ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_endpoint_train_unauthenticated_returns_401() -> None:
    response = APIClient().post(_train_url())
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_endpoint_train_insufficient_data_returns_400() -> None:
    user = _user("ep-insuf")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(_train_url())

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "required_sessions" in data
    assert data["required_sessions"] == MIN_ENROLLMENT_SESSIONS
    assert "required_samples" in data
    assert data["required_samples"] == MIN_TRAINING_SAMPLES


@pytest.mark.django_db
def test_endpoint_train_success(make_enrollment_session) -> None:
    user = _user("ep-success")
    for _ in range(5):
        make_enrollment_session(user)  # 10 reps each → 50 samples
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(_train_url())

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    profile = data["profile"]
    assert profile["feature_schema_version"] == FEATURE_SCHEMA_VERSION
    assert profile["detector_version"] == DETECTOR_VERSION
    assert profile["n_training_samples"] == 50
    assert "trained_at" in profile


@pytest.mark.django_db
def test_endpoint_status_no_profile() -> None:
    user = _user("ep-no-profile")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(_status_url())

    assert response.status_code == 200
    data = response.json()
    assert data["is_trained"] is False
    assert data["profile"] is None


@pytest.mark.django_db
def test_endpoint_status_with_profile(db) -> None:
    user = _user("ep-with-profile")
    _create_profile(user)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(_status_url())

    assert response.status_code == 200
    data = response.json()
    assert data["is_trained"] is True
    assert data["profile"]["feature_schema_version"] == FEATURE_SCHEMA_VERSION
    assert data["profile"]["n_training_samples"] == 60


@pytest.mark.django_db
def test_endpoint_status_partial_enrollment(make_enrollment_session) -> None:
    user = _user("ep-partial")
    for _ in range(3):
        make_enrollment_session(user)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(_status_url())

    assert response.status_code == 200
    data = response.json()
    assert data["enrollment_sessions_completed"] == 3
    assert data["ready_to_train"] is False
    assert data["is_trained"] is False


def _delete_url() -> str:
    return reverse("ml_engine:delete-profile")


@pytest.mark.django_db
def test_delete_profile_unauthenticated_returns_401() -> None:
    response = APIClient().delete(_delete_url())
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_delete_profile_no_existing_returns_404(db) -> None:
    user = _user("del-no-profile")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.delete(_delete_url())

    assert response.status_code == 404
    assert response.json()["deleted"] is False


@pytest.mark.django_db
def test_delete_profile_existing_returns_204_and_deletes(db) -> None:
    user = _user("del-with-profile")
    _create_profile(user)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.delete(_delete_url())

    assert response.status_code == 204
    assert BehaviorProfile.objects.filter(user=user).count() == 0
