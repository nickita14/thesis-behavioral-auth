from __future__ import annotations

from django.db.models import Prefetch
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RiskAssessment, TransactionAttempt
from .serializers import TransactionAttemptCreateSerializer, TransactionAttemptSerializer
from .services import TransactionAttemptService


class TransactionAttemptListCreateView(APIView):
    """GET/POST /api/transactions/attempts/ for the current user."""

    permission_classes = [IsAuthenticated]
    service = TransactionAttemptService()

    def get(self, request: Request) -> Response:
        attempts = (
            TransactionAttempt.objects.filter(user=request.user)
            .prefetch_related(
                Prefetch(
                    "assessments",
                    queryset=RiskAssessment.objects.order_by("-created_at"),
                    to_attr="ordered_assessments",
                )
            )
            .order_by("-created_at")[:20]
        )
        for attempt in attempts:
            attempt.latest_assessment = (
                attempt.ordered_assessments[0]
                if getattr(attempt, "ordered_assessments", [])
                else None
            )
        return Response(TransactionAttemptSerializer(attempts, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = TransactionAttemptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = self.service.create_attempt(
            user=request.user,
            amount=serializer.validated_data["amount"],
            currency=serializer.validated_data["currency"],
            recipient=serializer.validated_data["recipient"],
            behavior_session_id=serializer.validated_data.get("behavior_session_id"),
            target_url=serializer.validated_data.get("target_url", ""),
        )
        return Response(
            TransactionAttemptSerializer(attempt).data,
            status=status.HTTP_201_CREATED,
        )
