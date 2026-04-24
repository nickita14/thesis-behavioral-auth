from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import PhishingCheckRequestSerializer, PhishingPredictionSerializer
from .services import get_phishing_check_service

logger = logging.getLogger(__name__)


class PhishingCheckView(APIView):
    """POST /api/phishing/check/ validates and classifies one URL."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = PhishingCheckRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]
        try:
            prediction = get_phishing_check_service().check_url(url)
        except Exception:
            logger.exception("Phishing check failed for url=%r", url)
            return Response(
                {"detail": "Phishing detector is temporarily unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_data = PhishingPredictionSerializer(prediction).data
        return Response(response_data, status=status.HTTP_200_OK)
