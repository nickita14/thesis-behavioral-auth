from __future__ import annotations

import logging
from typing import Any

from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BehaviorSession, KeystrokeEvent, MouseEvent
from .permissions import IsSessionOwner
from .serializers import (
    KEYSTROKE_FIELDS,
    MOUSE_FIELDS,
    EventBatchSerializer,
    SessionDetailSerializer,
    SessionStartResponseSerializer,
    SessionStartSerializer,
)

logger = logging.getLogger(__name__)


class SessionStartView(APIView):
    """POST /api/behavior/sessions/start/

    Creates a new BehaviorSession for the authenticated user.
    ip_address is always taken from the request, never from the body.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SessionStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = BehaviorSession.objects.create(
            user=request.user,
            is_enrollment=serializer.validated_data["is_enrollment"],
            user_agent=serializer.validated_data.get("user_agent", ""),
            ip_address=request.META.get("REMOTE_ADDR", "127.0.0.1"),
        )

        response_data = SessionStartResponseSerializer(session).data
        return Response(response_data, status=status.HTTP_201_CREATED)


class SessionEndView(APIView):
    """POST /api/behavior/sessions/{token}/end/

    Closes the session by setting ended_at. Idempotent: calling it on an
    already-closed session still returns 204.
    """

    permission_classes = [IsAuthenticated, IsSessionOwner]

    def post(self, request: Request, token: str) -> Response:
        session: BehaviorSession = request.behavior_session  # type: ignore[attr-defined]
        if session.ended_at is None:
            session.ended_at = timezone.now()
            session.save(update_fields=["ended_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventBatchView(APIView):
    """POST /api/behavior/sessions/{token}/events/

    Accepts a columnar batch of keystroke and mouse events.
    Uses bulk_create with ignore_conflicts=True for idempotent ingestion.
    Duplicate detection is done via a pre-query on client_event_id.
    """

    permission_classes = [IsAuthenticated, IsSessionOwner]

    def post(self, request: Request, token: str) -> Response:
        session: BehaviorSession = request.behavior_session  # type: ignore[attr-defined]

        if session.ended_at is not None:
            logger.warning(
                "EventBatchView: attempt to post events to closed session %s by user %s",
                token,
                request.user.pk,
            )
            return Response(
                {"error": "session is already closed"},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = EventBatchSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "EventBatchView: invalid payload from user %s: %s",
                request.user.pk,
                serializer.errors,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        ks_result = self._ingest_keystrokes(session, data.get("keystrokes"))
        ms_result = self._ingest_mouse(session, data.get("mouse"))

        return Response(
            {
                "accepted": {
                    "keystrokes": ks_result["accepted"],
                    "mouse": ms_result["accepted"],
                },
                "duplicates": {
                    "keystrokes": ks_result["duplicates"],
                    "mouse": ms_result["duplicates"],
                },
            },
            status=status.HTTP_200_OK,
        )

    def _ingest_keystrokes(
        self, session: BehaviorSession, block: dict | None
    ) -> dict[str, int]:
        if not block:
            return {"accepted": 0, "duplicates": 0}

        rows = block["data"]
        total = len(rows)
        objects: list[KeystrokeEvent] = []
        incoming_ids: list[Any] = []

        for row in rows:
            mapped = dict(zip(KEYSTROKE_FIELDS, row))
            client_id = mapped["client_id"]
            down = float(mapped["down"])
            up = float(mapped["up"])
            incoming_ids.append(client_id)
            objects.append(
                KeystrokeEvent(
                    session=session,
                    client_event_id=client_id,
                    key_category=mapped["cat"],
                    key_down_at=down,
                    key_up_at=up,
                    dwell_time_ms=up - down,  # save() not called by bulk_create
                    flight_time_ms=mapped["flight"],
                )
            )

        existing_ids = set(
            KeystrokeEvent.objects.filter(
                client_event_id__in=incoming_ids
            ).values_list("client_event_id", flat=True)
        )
        duplicates = len(existing_ids)
        KeystrokeEvent.objects.bulk_create(objects, ignore_conflicts=True)
        return {"accepted": total - duplicates, "duplicates": duplicates}

    def _ingest_mouse(
        self, session: BehaviorSession, block: dict | None
    ) -> dict[str, int]:
        if not block:
            return {"accepted": 0, "duplicates": 0}

        rows = block["data"]
        total = len(rows)
        objects: list[MouseEvent] = []
        incoming_ids: list[Any] = []

        for row in rows:
            mapped = dict(zip(MOUSE_FIELDS, row))
            client_id = mapped["client_id"]
            incoming_ids.append(client_id)
            objects.append(
                MouseEvent(
                    session=session,
                    client_event_id=client_id,
                    event_type=mapped["type"],
                    timestamp_ms=float(mapped["t"]),
                    x=int(mapped["x"]),
                    y=int(mapped["y"]),
                    button=mapped["btn"],
                    delta_x=mapped["dx"],
                    delta_y=mapped["dy"],
                )
            )

        existing_ids = set(
            MouseEvent.objects.filter(
                client_event_id__in=incoming_ids
            ).values_list("client_event_id", flat=True)
        )
        duplicates = len(existing_ids)
        MouseEvent.objects.bulk_create(objects, ignore_conflicts=True)
        return {"accepted": total - duplicates, "duplicates": duplicates}


class SessionDetailView(APIView):
    """GET /api/behavior/sessions/{token}/

    Returns session metadata and event counts aggregated in a single query.
    """

    permission_classes = [IsAuthenticated, IsSessionOwner]

    def get(self, request: Request, token: str) -> Response:
        # IsSessionOwner already fetched the session; re-fetch with annotations
        # for counts (one query with two LEFT OUTER JOINs).
        session = (
            BehaviorSession.objects.annotate(
                keystroke_count=Count("keystrokes", distinct=True),
                mouse_event_count=Count("mouse_events", distinct=True),
            ).get(session_token=token)
        )
        return Response(SessionDetailSerializer(session).data)
