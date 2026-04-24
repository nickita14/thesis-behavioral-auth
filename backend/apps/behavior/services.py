from __future__ import annotations

import hashlib
from typing import Iterable

from django.conf import settings
from django.utils import timezone

from .models import BehaviorSession, KeystrokeEvent, MouseEvent


class AnonymousBehaviorSessionRejected(Exception):
    """Raised when anonymous behavior collection is disabled by settings."""


class BehaviorSessionService:
    """Creates and closes behavior sessions."""

    def create_session(
        self,
        *,
        user,
        session_key: str | None,
        is_enrollment: bool,
        context: dict,
        ip_address: str | None,
        user_agent: str,
    ) -> BehaviorSession:
        session_user = self._resolve_session_user(user)
        return BehaviorSession.objects.create(
            user=session_user,
            session_key=session_key or "",
            is_enrollment=is_enrollment,
            context=context,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def end_session(self, session: BehaviorSession) -> BehaviorSession:
        if session.ended_at is None:
            session.ended_at = timezone.now()
            session.save(update_fields=["ended_at"])
        return session

    @staticmethod
    def _resolve_session_user(user):
        if getattr(user, "is_authenticated", False):
            return user
        if settings.BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS:
            return None
        raise AnonymousBehaviorSessionRejected(
            "Anonymous behavior sessions are disabled."
        )


class BehaviorEventService:
    """Stores validated behavior events for a session."""

    def create_keystrokes(
        self,
        session: BehaviorSession,
        events: Iterable[dict],
    ) -> list[KeystrokeEvent]:
        objects = [
            KeystrokeEvent(
                behavior_session=session,
                event_type=event["event_type"],
                key_code=event.get("key_code", ""),
                key_value_hash=self.hash_key_value(event.get("key_value", "")),
                timestamp_ms=event["timestamp_ms"],
                relative_time_ms=event["relative_time_ms"],
                dwell_time_ms=event.get("dwell_time_ms"),
                flight_time_ms=event.get("flight_time_ms"),
                metadata=event.get("metadata", {}),
            )
            for event in events
        ]
        return KeystrokeEvent.objects.bulk_create(objects)

    def create_mouse_events(
        self,
        session: BehaviorSession,
        events: Iterable[dict],
    ) -> list[MouseEvent]:
        objects = [
            MouseEvent(
                behavior_session=session,
                event_type=event["event_type"],
                x=event.get("x"),
                y=event.get("y"),
                button=event.get("button", ""),
                scroll_delta_x=event.get("scroll_delta_x"),
                scroll_delta_y=event.get("scroll_delta_y"),
                timestamp_ms=event["timestamp_ms"],
                relative_time_ms=event["relative_time_ms"],
                metadata=event.get("metadata", {}),
            )
            for event in events
        ]
        return MouseEvent.objects.bulk_create(objects)

    @staticmethod
    def hash_key_value(key_value: str) -> str:
        """Hash raw key values; never persist typed characters directly."""
        if key_value == "":
            return ""
        return hashlib.sha256(key_value.encode("utf-8")).hexdigest()
