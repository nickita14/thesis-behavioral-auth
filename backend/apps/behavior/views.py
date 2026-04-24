from __future__ import annotations

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
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
