from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class BehaviorSession(models.Model):
    """One browser/user interaction session used for behavioral collection."""

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["session_key"]),
            models.Index(fields=["started_at"]),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="behavior_sessions",
    )
    session_key = models.CharField(max_length=128, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    context = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_enrollment = models.BooleanField(default=False)

    @property
    def duration_ms(self) -> int | None:
        if self.ended_at is None:
            return None
        return int((self.ended_at - self.started_at).total_seconds() * 1000)

    def __str__(self) -> str:
        kind = "enrollment" if self.is_enrollment else "session"
        return f"{kind} {self.id} @ {self.started_at:%Y-%m-%d %H:%M}"


class KeystrokeEvent(models.Model):
    """Privacy-safe keystroke event.

    Raw typed values are intentionally not stored. If the API receives
    key_value, only a one-way hash is persisted so passwords or typed text
    cannot be reconstructed from the behavioral dataset.
    """

    class EventType(models.TextChoices):
        KEYDOWN = "keydown", "Key down"
        KEYUP = "keyup", "Key up"

    class Meta:
        ordering = ["timestamp_ms", "id"]
        indexes = [
            models.Index(fields=["behavior_session", "timestamp_ms"]),
            models.Index(fields=["event_type"]),
        ]

    behavior_session = models.ForeignKey(
        BehaviorSession,
        on_delete=models.CASCADE,
        related_name="keystroke_events",
    )
    event_type = models.CharField(max_length=16, choices=EventType)
    key_code = models.CharField(max_length=64, blank=True)
    key_value_hash = models.CharField(max_length=128, blank=True)
    timestamp_ms = models.BigIntegerField()
    relative_time_ms = models.IntegerField()
    dwell_time_ms = models.IntegerField(null=True, blank=True)
    flight_time_ms = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.event_type} {self.key_code or '<unknown>'} @ {self.timestamp_ms}ms"


class MouseEvent(models.Model):
    """Mouse movement, click, or scroll event captured in a behavior session."""

    class EventType(models.TextChoices):
        MOVE = "move", "Move"
        CLICK = "click", "Click"
        SCROLL = "scroll", "Scroll"

    class Meta:
        ordering = ["timestamp_ms", "id"]
        indexes = [
            models.Index(fields=["behavior_session", "timestamp_ms"]),
            models.Index(fields=["event_type"]),
        ]

    behavior_session = models.ForeignKey(
        BehaviorSession,
        on_delete=models.CASCADE,
        related_name="mouse_events",
    )
    event_type = models.CharField(max_length=16, choices=EventType)
    x = models.IntegerField(null=True, blank=True)
    y = models.IntegerField(null=True, blank=True)
    button = models.CharField(max_length=32, blank=True)
    scroll_delta_x = models.FloatField(null=True, blank=True)
    scroll_delta_y = models.FloatField(null=True, blank=True)
    timestamp_ms = models.BigIntegerField()
    relative_time_ms = models.IntegerField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.timestamp_ms}ms"
