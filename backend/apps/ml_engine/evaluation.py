from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import auc, roc_curve

from .behavior_features import BehaviorFeatures
from .models import EvaluationSubject

logger = logging.getLogger(__name__)

DEFAULT_TRAIN_FRACTION = 0.8
DEFAULT_CONTAMINATION = 0.1
DEFAULT_RANDOM_STATE = 42


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubjectData:
    """Subject data prepared for evaluation."""

    subject_id: str
    train_features: list[BehaviorFeatures]
    test_features: list[BehaviorFeatures]
    source_dataset: str  # e.g. 'cmu_keystroke' or 'our_collection'


@dataclass(frozen=True)
class EvaluationMetrics:
    """Metrics computed from genuine + impostor score distributions."""

    eer: float
    eer_threshold: float
    far: float   # false acceptance rate at EER threshold
    frr: float   # false rejection rate at EER threshold
    auc: float
    n_genuine: int
    n_impostor: int


@dataclass(frozen=True)
class PerSubjectResult:
    """Evaluation result for one subject in the LOSO matrix."""

    subject_id: str
    source_dataset: str
    n_train: int
    n_test_genuine: int
    n_test_impostor: int
    metrics: EvaluationMetrics


@dataclass(frozen=True)
class CrossUserMatrixResult:
    """Full cross-user evaluation results."""

    scope_name: str  # 'cmu_only', 'hybrid', etc.
    n_subjects: int
    per_subject_results: list[PerSubjectResult]
    overall_eer: float   # mean across subjects
    overall_auc: float
    # (model_subject_id, test_subject_id) → list of anomaly scores
    cross_user_scores: dict[tuple[str, str], list[float]]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def prepare_subjects_data(
    subject_ids: list[str] | None = None,
    dataset_names: list[str] | None = None,
    train_fraction: float = DEFAULT_TRAIN_FRACTION,
    seed: int = DEFAULT_RANDOM_STATE,
) -> list[SubjectData]:
    """Load EvaluationSubjects from the DB and split into train/test.

    Parameters
    ----------
    subject_ids : list[str] | None
        Filter by specific subject IDs. None → all subjects.
    dataset_names : list[str] | None
        Filter by dataset name (e.g. ['cmu_keystroke']). None → all datasets.
    train_fraction : float
        Fraction of vectors used for training (default 0.8).
    seed : int
        Random seed for reproducible shuffling before split.

    Returns
    -------
    list[SubjectData] — one entry per subject.
    """
    qs = EvaluationSubject.objects.select_related('dataset').all()
    if dataset_names is not None:
        qs = qs.filter(dataset__name__in=dataset_names)
    if subject_ids is not None:
        qs = qs.filter(subject_id__in=subject_ids)

    rng = random.Random(seed)
    subjects: list[SubjectData] = []

    for evaluation_subject in qs:
        all_features = [
            BehaviorFeatures(**fv) for fv in evaluation_subject.feature_vectors
        ]
        shuffled = all_features.copy()
        rng.shuffle(shuffled)
        n_train = int(len(shuffled) * train_fraction)

        subjects.append(
            SubjectData(
                subject_id=evaluation_subject.subject_id,
                train_features=shuffled[:n_train],
                test_features=shuffled[n_train:],
                source_dataset=evaluation_subject.dataset.name,
            )
        )

    logger.info(
        "Prepared %d subjects (datasets=%s, train_fraction=%.0f%%)",
        len(subjects),
        dataset_names,
        train_fraction * 100,
    )
    return subjects


def train_subject_model(
    features: list[BehaviorFeatures],
    contamination: float = DEFAULT_CONTAMINATION,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> IsolationForest:
    """Train IsolationForest on a subject's training feature vectors.

    Parameters
    ----------
    features : list[BehaviorFeatures]
        Training samples (one per password repetition).
    contamination : float
        IsolationForest contamination parameter.
    random_state : int
        Reproducibility seed.

    Returns
    -------
    Fitted IsolationForest.
    """
    X = np.array([f.to_vector() for f in features])
    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=100,
    )
    model.fit(X)
    return model


def score_features(
    model: IsolationForest,
    features: list[BehaviorFeatures],
) -> list[float]:
    """Score feature vectors against a trained model.

    Returns negated ``score_samples()`` values so that a higher score means
    more anomalous (easier to threshold for impostor detection).

    Parameters
    ----------
    model : IsolationForest
        Fitted model for one subject.
    features : list[BehaviorFeatures]
        Vectors to score (genuine or impostor).

    Returns
    -------
    list[float] — one anomaly score per feature vector. Empty list when
    input is empty.
    """
    if not features:
        return []
    X = np.array([f.to_vector() for f in features])
    return [float(-s) for s in model.score_samples(X)]


def compute_metrics(
    genuine_scores: list[float],
    impostor_scores: list[float],
) -> EvaluationMetrics:
    """Compute EER, FAR, FRR, AUC from genuine and impostor score lists.

    Convention: higher anomaly score → more likely impostor.
    Genuine samples should cluster at low scores; impostors at high scores.

    Parameters
    ----------
    genuine_scores : list[float]
        Anomaly scores for the genuine subject (lower = more normal).
    impostor_scores : list[float]
        Anomaly scores for all other subjects (higher = more anomalous).

    Returns
    -------
    EvaluationMetrics with EER, FAR, FRR, AUC, threshold, and sample counts.
    """
    y_true = [0] * len(genuine_scores) + [1] * len(impostor_scores)
    y_scores = list(genuine_scores) + list(impostor_scores)

    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    fnr = 1 - tpr

    # EER: threshold where |FPR − FNR| is minimised
    eer_idx = int(np.argmin(np.abs(fpr - fnr)))
    eer = float((fpr[eer_idx] + fnr[eer_idx]) / 2)
    eer_threshold = float(thresholds[eer_idx])
    far = float(fpr[eer_idx])
    frr = float(fnr[eer_idx])

    roc_auc = float(auc(fpr, tpr))

    return EvaluationMetrics(
        eer=eer,
        eer_threshold=eer_threshold,
        far=far,
        frr=frr,
        auc=roc_auc,
        n_genuine=len(genuine_scores),
        n_impostor=len(impostor_scores),
    )


def evaluate_cross_user(
    subjects: list[SubjectData],
    scope_name: str = "default",
    contamination: float = DEFAULT_CONTAMINATION,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> CrossUserMatrixResult:
    """Run leave-one-subject-out (LOSO) cross-user evaluation.

    For each subject S (model subject):
    1. Train IsolationForest on S's training features.
    2. Score S's test features → genuine scores.
    3. Score every other subject's test features → impostor scores.
    4. Compute EER / AUC / FAR / FRR for S.

    All (model_subject, test_subject) score pairs are stored in
    ``cross_user_scores`` for notebook visualisation.

    Parameters
    ----------
    subjects : list[SubjectData]
        Pre-split subject data from ``prepare_subjects_data()``.
    scope_name : str
        Label for this evaluation run (e.g. 'cmu_only', 'hybrid').
    contamination : float
        IsolationForest contamination parameter.
    random_state : int
        Reproducibility seed passed to IsolationForest.

    Returns
    -------
    CrossUserMatrixResult with per-subject results and aggregate metrics.
    """
    cross_user_scores: dict[tuple[str, str], list[float]] = {}
    per_subject_results: list[PerSubjectResult] = []

    # Train one model per subject up-front.
    models: dict[str, IsolationForest] = {}
    for sd in subjects:
        models[sd.subject_id] = train_subject_model(
            sd.train_features, contamination, random_state
        )
        logger.debug("Trained model for %s (%d samples)", sd.subject_id, len(sd.train_features))

    # Score all (model, test) pairs.
    for model_subject in subjects:
        model = models[model_subject.subject_id]

        genuine_scores = score_features(model, model_subject.test_features)
        cross_user_scores[(model_subject.subject_id, model_subject.subject_id)] = genuine_scores

        impostor_scores: list[float] = []
        for test_subject in subjects:
            if test_subject.subject_id == model_subject.subject_id:
                continue
            imp = score_features(model, test_subject.test_features)
            cross_user_scores[(model_subject.subject_id, test_subject.subject_id)] = imp
            impostor_scores.extend(imp)

        metrics = compute_metrics(genuine_scores, impostor_scores)
        per_subject_results.append(
            PerSubjectResult(
                subject_id=model_subject.subject_id,
                source_dataset=model_subject.source_dataset,
                n_train=len(model_subject.train_features),
                n_test_genuine=len(genuine_scores),
                n_test_impostor=len(impostor_scores),
                metrics=metrics,
            )
        )
        logger.debug(
            "%s: EER=%.3f AUC=%.3f (genuine=%d impostor=%d)",
            model_subject.subject_id,
            metrics.eer,
            metrics.auc,
            metrics.n_genuine,
            metrics.n_impostor,
        )

    overall_eer = float(np.mean([r.metrics.eer for r in per_subject_results]))
    overall_auc = float(np.mean([r.metrics.auc for r in per_subject_results]))

    logger.info(
        "evaluate_cross_user(%s): subjects=%d, overall EER=%.3f, overall AUC=%.3f",
        scope_name,
        len(subjects),
        overall_eer,
        overall_auc,
    )

    return CrossUserMatrixResult(
        scope_name=scope_name,
        n_subjects=len(subjects),
        per_subject_results=per_subject_results,
        overall_eer=overall_eer,
        overall_auc=overall_auc,
        cross_user_scores=cross_user_scores,
    )
