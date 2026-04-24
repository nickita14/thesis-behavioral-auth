from __future__ import annotations

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BehaviorSession
from .serializers import (
    BehaviorSessionCreateSerializer,
    BehaviorSessionResponseSerializer,
    BehaviorSummarySerializer,
    KeystrokeBatchSerializer,
    MouseBatchSerializer,
)
from .services import (
    AnonymousBehaviorSessionRejected,
    BehaviorEventService,
    BehaviorSessionService,
)

DASHBOARD_LIMIT = 5


class BehaviorSessionCreateView(APIView):
    """POST /api/behavior/sessions/ creates an anonymous or authenticated session."""

    permission_classes = [AllowAny]
    session_service = BehaviorSessionService()

    def post(self, request: Request) -> Response:
        serializer = BehaviorSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            session = self.session_service.create_session(
                user=request.user,
                session_key=getattr(request.session, "session_key", None),
                is_enrollment=serializer.validated_data["is_enrollment"],
                context=serializer.validated_data["context"],
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
        except AnonymousBehaviorSessionRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            BehaviorSessionResponseSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class BehaviorSessionEndView(APIView):
    """POST /api/behavior/sessions/{session_id}/end/ closes a session."""

    permission_classes = [AllowAny]
    session_service = BehaviorSessionService()

    def post(self, request: Request, session_id: str) -> Response:
        session = get_object_or_404(BehaviorSession, id=session_id)
        session = self.session_service.end_session(session)
        return Response(
            {"id": str(session.id), "ended_at": session.ended_at},
            status=status.HTTP_200_OK,
        )


class KeystrokeBatchView(APIView):
    """POST /api/behavior/sessions/{session_id}/keystrokes/ stores key events."""

    permission_classes = [AllowAny]
    event_service = BehaviorEventService()

    def post(self, request: Request, session_id: str) -> Response:
        session = get_object_or_404(BehaviorSession, id=session_id)
        serializer = KeystrokeBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = self.event_service.create_keystrokes(
            session,
            serializer.validated_data["events"],
        )
        return Response({"created": len(created)}, status=status.HTTP_201_CREATED)


class MouseBatchView(APIView):
    """POST /api/behavior/sessions/{session_id}/mouse/ stores mouse events."""

    permission_classes = [AllowAny]
    event_service = BehaviorEventService()

    def post(self, request: Request, session_id: str) -> Response:
        session = get_object_or_404(BehaviorSession, id=session_id)
        serializer = MouseBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = self.event_service.create_mouse_events(
            session,
            serializer.validated_data["events"],
        )
        return Response({"created": len(created)}, status=status.HTTP_201_CREATED)


class BehaviorSummaryView(APIView):
    """GET /api/behavior/sessions/{session_id}/summary/ returns event counts."""

    permission_classes = [AllowAny]

    def get(self, request: Request, session_id: str) -> Response:
        session = get_object_or_404(
            BehaviorSession.objects.annotate(
                keystroke_count=Count("keystroke_events", distinct=True),
                mouse_count=Count("mouse_events", distinct=True),
            ),
            id=session_id,
        )
        data = {
            "id": session.id,
            "duration_ms": session.duration_ms,
            "keystroke_count": session.keystroke_count,
            "mouse_count": session.mouse_count,
            "is_enrollment": session.is_enrollment,
        }
        return Response(BehaviorSummarySerializer(data).data)


class BehaviorDashboardView(APIView):
    """GET /api/behavior/dashboard/ returns demo dashboard telemetry."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        sessions = list(
            BehaviorSession.objects.filter(user=request.user)
            .annotate(
                keystroke_count=Count("keystroke_events", distinct=True),
                mouse_count=Count("mouse_events", distinct=True),
            )
            .order_by("-started_at")[:DASHBOARD_LIMIT]
        )
        all_sessions = BehaviorSession.objects.filter(user=request.user)
        totals = all_sessions.aggregate(
            session_count=Count("id", distinct=True),
            keystroke_count=Count("keystroke_events", distinct=True),
            mouse_count=Count("mouse_events", distinct=True),
        )
        active_sessions = all_sessions.filter(ended_at__isnull=True).count()

        from apps.phishing.models import PhishingEvent

        phishing_queryset = PhishingEvent.objects.filter(session__user=request.user)
        phishing_checks = phishing_queryset.order_by("-created_at")[:DASHBOARD_LIMIT]
        phishing_total = phishing_queryset.count()
        phishing_flagged = phishing_queryset.filter(is_phishing_predicted=True).count()
        event_total = totals["keystroke_count"] + totals["mouse_count"]
        status_level = "collecting" if active_sessions else "ready"

        return Response(
            {
                "behavior": {
                    "totals": {
                        "sessions": totals["session_count"],
                        "active_sessions": active_sessions,
                        "keystrokes": totals["keystroke_count"],
                        "mouse": totals["mouse_count"],
                    },
                    "sessions": [
                        {
                            "id": str(session.id),
                            "started_at": session.started_at,
                            "ended_at": session.ended_at,
                            "duration_ms": session.duration_ms,
                            "is_enrollment": session.is_enrollment,
                            "keystroke_count": session.keystroke_count,
                            "mouse_count": session.mouse_count,
                        }
                        for session in sessions
                    ],
                },
                "phishing": {
                    "totals": {
                        "checks": phishing_total,
                        "flagged": phishing_flagged,
                    },
                    "checks": [
                        {
                            "id": str(check.id),
                            "url": check.url,
                            "is_phishing_predicted": check.is_phishing_predicted,
                            "confidence": check.confidence,
                            "created_at": check.created_at,
                        }
                        for check in phishing_checks
                    ],
                },
                "security_status": {
                    "level": status_level,
                    "message": (
                        "Behavior collection is active; keystroke and mouse metadata is being stored."
                        if active_sessions
                        else "No active behavior session is open, but collected metadata remains available for audit."
                    ),
                    "privacy_note": (
                        "Raw typed characters are not stored. Keystroke collection stores timing metadata and hashes only."
                    ),
                    "event_total": event_total,
                },
            }
        )
