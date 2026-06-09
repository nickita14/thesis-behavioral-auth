from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from statistics import mean, pstdev

import joblib
from django.contrib.auth import get_user_model
from django.db import transaction
from sklearn.ensemble import IsolationForest

from apps.behavior.models import BehaviorSession

from .behavior_features import BehaviorFeatureExtractor, BehaviorFeatures
from .models import BehaviorProfile

logger = logging.getLogger(__name__)

User = get_user_model()

FEATURE_SCHEMA_VERSION = "v1"
DETECTOR_VERSION = "isolation_forest_v1"

MIN_ENROLLMENT_SESSIONS = 5
MIN_TRAINING_SAMPLES = 50
ISOLATION_FOREST_CONTAMINATION = 0.1
RANDOM_STATE = 42


@dataclass(frozen=True)
class TrainingResult:
    """Result of a behavior profile training attempt."""

    success: bool
    profile: BehaviorProfile | None
    n_sessions: int
    n_samples: int
    error: str | None = None


class BehaviorProfileTrainer:
    """Trains per-user IsolationForest model from enrollment sessions.

    Workflow:
    1. Collect all completed enrollment sessions of the user.
    2. Extract per-repetition feature vectors from each session.
    3. Check minimum thresholds (sessions + samples).
    4. Train IsolationForest on the aggregated vectors.
    5. Serialize the model and save (or replace) a BehaviorProfile.
    """

    def __init__(self) -> None:
        self.extractor = BehaviorFeatureExtractor()

    def train(self, user) -> TrainingResult:
        sessions = self._collect_enrollment_sessions(user)
        feature_vectors = self._extract_all_features(sessions)

        n_sessions = len(sessions)
        n_samples = len(feature_vectors)

        if n_sessions < MIN_ENROLLMENT_SESSIONS:
            return TrainingResult(
                success=False,
                profile=None,
                n_sessions=n_sessions,
                n_samples=n_samples,
                error=(
                    f"Insufficient enrollment sessions: "
                    f"{n_sessions}/{MIN_ENROLLMENT_SESSIONS}"
                ),
            )

        if n_samples < MIN_TRAINING_SAMPLES:
            return TrainingResult(
                success=False,
                profile=None,
                n_sessions=n_sessions,
                n_samples=n_samples,
                error=(
                    f"Insufficient training samples after repetition split: "
                    f"{n_samples}/{MIN_TRAINING_SAMPLES}"
                ),
            )

        try:
            model, score_mean, score_std = self._fit_isolation_forest(feature_vectors)
        except Exception as exc:
            logger.exception("Training failed for %s: %s", user.username, exc)
            return TrainingResult(
                success=False,
                profile=None,
                n_sessions=n_sessions,
                n_samples=n_samples,
                error=f"Training failed: {exc}",
            )

        model_blob = self._serialize_model(model)

        with transaction.atomic():
            profile, _created = BehaviorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "model_blob": model_blob,
                    "feature_schema_version": FEATURE_SCHEMA_VERSION,
                    "detector_version": DETECTOR_VERSION,
                    "n_training_sessions": n_sessions,
                    "n_training_samples": n_samples,
                    "training_score_mean": score_mean,
                    "training_score_std": score_std,
                    "is_active": True,
                },
            )

        logger.info(
            "Trained BehaviorProfile for %s: sessions=%d, samples=%d, mean_score=%.3f",
            user.username,
            n_sessions,
            n_samples,
            score_mean,
        )

        return TrainingResult(
            success=True,
            profile=profile,
            n_sessions=n_sessions,
            n_samples=n_samples,
        )

    @staticmethod
    def _collect_enrollment_sessions(user) -> list[BehaviorSession]:
        return list(
            BehaviorSession.objects.filter(user=user, is_enrollment=True)
            .exclude(ended_at=None)
            .order_by("started_at")
        )

    def _extract_all_features(
        self, sessions: list[BehaviorSession]
    ) -> list[BehaviorFeatures]:
        all_vectors: list[BehaviorFeatures] = []
        for session in sessions:
            try:
                vectors = self.extractor.extract_repetitions(session)
                all_vectors.extend(vectors)
            except Exception as exc:
                logger.warning(
                    "Failed to extract features for session %s: %s", session.id, exc
                )
        return all_vectors

    @staticmethod
    def _fit_isolation_forest(
        features: list[BehaviorFeatures],
    ) -> tuple[IsolationForest, float, float]:
        X = [f.to_vector() for f in features]
        model = IsolationForest(
            contamination=ISOLATION_FOREST_CONTAMINATION,
            random_state=RANDOM_STATE,
            n_estimators=100,
        )
        model.fit(X)
        scores = [-model.score_samples([x])[0] for x in X]
        score_mean = float(mean(scores))
        score_std = float(pstdev(scores)) if len(scores) > 1 else 0.0
        return model, score_mean, score_std

    @staticmethod
    def _serialize_model(model: IsolationForest) -> bytes:
        """Serialize sklearn model to bytes via joblib for DB storage."""
        buffer = io.BytesIO()
        joblib.dump(model, buffer)
        return buffer.getvalue()

    @staticmethod
    def deserialize_model(model_blob: bytes | memoryview) -> IsolationForest:
        """Load IsolationForest back from blob (used by detector)."""
        buffer = io.BytesIO(bytes(model_blob))
        return joblib.load(buffer)
