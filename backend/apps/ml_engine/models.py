from __future__ import annotations

from django.conf import settings
from django.db import models


class BehaviorProfile(models.Model):
    """Per-user trained behavioral biometric model.

    The model is trained on N enrollment sessions split into
    per-repetition feature vectors. The serialized sklearn
    IsolationForest is stored as a binary blob in the database.

    A user has at most one active profile. Retraining replaces it.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='behavior_profile',
    )

    # Serialized model artifact (joblib + pickle inside)
    model_blob = models.BinaryField()

    # Versioning — bump when feature vector schema or algorithm changes.
    # On mismatch, detector falls back to "suspicious".
    feature_schema_version = models.CharField(
        max_length=32,
        help_text=(
            "Version of BehaviorFeatures dataclass schema. "
            "Bump when feature list changes."
        ),
    )
    detector_version = models.CharField(
        max_length=32,
        help_text=(
            "Version of detector algorithm + hyperparameters. "
            "Bump when IsolationForest contamination or other params change."
        ),
    )

    # Training metadata
    trained_at = models.DateTimeField(auto_now=True)
    n_training_sessions = models.IntegerField(
        help_text="Number of enrollment sessions used for training",
    )
    n_training_samples = models.IntegerField(
        help_text="Number of feature vectors (after per-repetition split)",
    )

    # Quality metrics computed at training time (for diagnostics)
    training_score_mean = models.FloatField(
        null=True,
        help_text="Mean anomaly score on training data",
    )
    training_score_std = models.FloatField(
        null=True,
        help_text="Std anomaly score on training data",
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "If False, detector falls back to suspicious. Useful for "
            "disabling stale models without deletion."
        ),
    )

    class Meta:
        verbose_name = 'Behavior Profile'
        verbose_name_plural = 'Behavior Profiles'

    def __str__(self) -> str:
        return (
            f"BehaviorProfile(user={self.user.username}, "
            f"schema={self.feature_schema_version}, "
            f"detector={self.detector_version}, "
            f"samples={self.n_training_samples})"
        )


class EvaluationDataset(models.Model):
    """Benchmark dataset for cross-user evaluation.

    Examples: CMU Keystroke Dynamics Benchmark, our own collection.
    Separate from production User/BehaviorSession — never mixed.
    """

    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    source_url = models.CharField(max_length=255, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evaluation Dataset'
        verbose_name_plural = 'Evaluation Datasets'

    def __str__(self) -> str:
        return f"EvaluationDataset({self.name})"


class EvaluationSubject(models.Model):
    """Virtual subject in evaluation dataset.

    NOT a Django User — just a labeled set of feature vectors.
    feature_vectors stored as JSON list of dicts matching
    BehaviorFeatures dataclass schema (16 fields).
    """

    dataset = models.ForeignKey(
        EvaluationDataset,
        on_delete=models.CASCADE,
        related_name='subjects',
    )
    subject_id = models.CharField(max_length=64)
    feature_vectors = models.JSONField(
        help_text="List of feature vectors as dicts matching BehaviorFeatures",
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Source-specific data: n_sessions, n_repetitions, etc.",
    )

    class Meta:
        unique_together = [["dataset", "subject_id"]]
        ordering = ["dataset", "subject_id"]
        verbose_name = 'Evaluation Subject'
        verbose_name_plural = 'Evaluation Subjects'

    def n_vectors(self) -> int:
        return len(self.feature_vectors)

    def __str__(self) -> str:
        return f"EvaluationSubject({self.dataset.name}/{self.subject_id})"
