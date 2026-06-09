from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.behavior.models import BehaviorSession

from .models import BehaviorProfile
from .training import MIN_ENROLLMENT_SESSIONS, MIN_TRAINING_SAMPLES, BehaviorProfileTrainer

logger = logging.getLogger(__name__)


class BehaviorProfileTrainView(APIView):
    """POST /api/ml/behavior-profile/train/

    Triggers training of the current user's behavioral profile from
    completed enrollment sessions. Returns 201 with profile metadata
    on success, 400 with reason on insufficient data.

    Replaces any existing profile of the user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        trainer = BehaviorProfileTrainer()
        result = trainer.train(request.user)

        if not result.success:
            return Response(
                {
                    "success": False,
                    "error": result.error,
                    "n_sessions": result.n_sessions,
                    "n_samples": result.n_samples,
                    "required_sessions": MIN_ENROLLMENT_SESSIONS,
                    "required_samples": MIN_TRAINING_SAMPLES,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = result.profile
        return Response(
            {
                "success": True,
                "profile": {
                    "feature_schema_version": profile.feature_schema_version,
                    "detector_version": profile.detector_version,
                    "n_training_sessions": profile.n_training_sessions,
                    "n_training_samples": profile.n_training_samples,
                    "training_score_mean": profile.training_score_mean,
                    "training_score_std": profile.training_score_std,
                    "trained_at": profile.trained_at.isoformat(),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class BehaviorProfileStatusView(APIView):
    """GET /api/ml/behavior-profile/status/

    Returns the current user's profile status. Useful for the frontend
    to know whether enough enrollment data has been collected for training.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        completed_sessions = (
            BehaviorSession.objects.filter(user=request.user, is_enrollment=True)
            .exclude(ended_at=None)
            .count()
        )

        profile = BehaviorProfile.objects.filter(user=request.user).first()

        return Response(
            {
                "is_trained": profile is not None and profile.is_active,
                "enrollment_sessions_completed": completed_sessions,
                "enrollment_sessions_required": MIN_ENROLLMENT_SESSIONS,
                "ready_to_train": completed_sessions >= MIN_ENROLLMENT_SESSIONS,
                "profile": (
                    {
                        "feature_schema_version": profile.feature_schema_version,
                        "detector_version": profile.detector_version,
                        "n_training_samples": profile.n_training_samples,
                        "trained_at": profile.trained_at.isoformat(),
                    }
                    if profile
                    else None
                ),
            }
        )


class BehaviorProfileDeleteView(APIView):
    """DELETE /api/ml/behavior-profile/

    Removes the current user's trained profile. Subsequent transactions
    fall back to "suspicious" until the user retrains. Useful when the
    user wants to reset the model with fresh enrollment data.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request) -> Response:
        deleted_count, _ = BehaviorProfile.objects.filter(user=request.user).delete()
        if deleted_count:
            return Response({"deleted": True}, status=status.HTTP_204_NO_CONTENT)
        return Response({"deleted": False}, status=status.HTTP_404_NOT_FOUND)
