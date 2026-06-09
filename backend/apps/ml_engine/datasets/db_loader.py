from __future__ import annotations

import logging

from django.contrib.auth import get_user_model

from apps.behavior.models import BehaviorSession
from apps.ml_engine.behavior_features import BehaviorFeatureExtractor, BehaviorFeatures

logger = logging.getLogger(__name__)

User = get_user_model()


def load_user_features(
    username: str,
    enrollment_only: bool = True,
) -> list[BehaviorFeatures]:
    """Load per-repetition feature vectors for a real DB user.

    Parameters
    ----------
    username : str
        Django username of the target user.
    enrollment_only : bool
        If True, only enrollment sessions are used (default). Set to False
        to include non-enrollment sessions (e.g. transaction challenge sessions).

    Returns
    -------
    list of BehaviorFeatures — one per detected repetition across all sessions.
    Returns an empty list when the user does not exist or has no data.
    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.warning("User '%s' not found in DB — skipping.", username)
        return []

    qs = BehaviorSession.objects.filter(user=user).exclude(ended_at=None)
    if enrollment_only:
        qs = qs.filter(is_enrollment=True)
    sessions = list(qs.order_by("started_at"))

    if not sessions:
        logger.warning("User '%s' has no completed sessions — skipping.", username)
        return []

    extractor = BehaviorFeatureExtractor()
    all_vectors: list[BehaviorFeatures] = []
    for session in sessions:
        try:
            reps = extractor.extract_repetitions(session)
            all_vectors.extend(reps)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Feature extraction failed for session %s: %s", session.id, exc)

    logger.info(
        "Loaded %d feature vectors from %d sessions for user '%s'.",
        len(all_vectors),
        len(sessions),
        username,
    )
    return all_vectors


def load_users_features(
    usernames: list[str],
    enrollment_only: bool = True,
) -> dict[str, list[BehaviorFeatures]]:
    """Load feature vectors for multiple real users.

    Parameters
    ----------
    usernames : list[str]
        List of Django usernames to include.
    enrollment_only : bool
        Passed through to load_user_features.

    Returns
    -------
    dict mapping username → list[BehaviorFeatures].
    Subjects with zero feature vectors are excluded.
    """
    result: dict[str, list[BehaviorFeatures]] = {}
    for username in usernames:
        vectors = load_user_features(username, enrollment_only=enrollment_only)
        if vectors:
            result[username] = vectors
    return result
