from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class BehaviorSession(models.Model):
    """One continuous interaction session for a user.

    Created when the user opens a page that collects behavioral signals.
    Enrollment sessions (is_enrollment=True) are used to train the
    per-user anomaly detector; subsequent sessions are scored against it.
    """

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["session_token"]),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="behavior_sessions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    is_enrollment = models.BooleanField(default=False)
    session_token = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self) -> str:
        kind = "enrollment" if self.is_enrollment else "session"
        return f"{self.user} — {kind} @ {self.started_at:%Y-%m-%d %H:%M}"


class KeystrokeEvent(models.Model):
    """Single key press/release event captured in a behavior session.

    Timestamps are stored as milliseconds from session start so that
    absolute wall-clock time is not needed for feature extraction.
    dwell_time_ms is computed on save() from key_up_at − key_down_at
    and stored in the DB to allow indexed queries and aggregation.
    """

    class KeyCategory(models.TextChoices):
        LETTER = "letter", "Letter"
        DIGIT = "digit", "Digit"
        SPECIAL = "special", "Special"
        MODIFIER = "modifier", "Modifier"

    class Meta:
        ordering = ["key_down_at"]
        indexes = [
            models.Index(fields=["session", "key_down_at"]),
        ]

    session = models.ForeignKey(
        BehaviorSession,
        on_delete=models.CASCADE,
        related_name="keystrokes",
    )
    key_category = models.CharField(max_length=16, choices=KeyCategory)
    key_down_at = models.FloatField(help_text="ms from session start")
    key_up_at = models.FloatField(help_text="ms from session start")
    dwell_time_ms = models.FloatField(
        editable=False,
        help_text="key_up_at − key_down_at, stored for indexing",
    )
    flight_time_ms = models.FloatField(
        null=True,
        blank=True,
        help_text="Gap between previous key_up and this key_down",
    )

    def save(self, *args, **kwargs) -> None:
        self.dwell_time_ms = self.key_up_at - self.key_down_at
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"[{self.key_category}] dwell={self.dwell_time_ms:.1f}ms @ {self.key_down_at:.0f}ms"


class MouseEvent(models.Model):
    """Single mouse/touch/scroll event captured in a behavior session.

    Coordinates are in CSS pixels relative to the viewport.
    button and delta_* fields are type-specific: button is set for
    click events, delta_* for scroll events, both null otherwise.
    """

    class EventType(models.TextChoices):
        MOVE = "move", "Move"
        CLICK = "click", "Click"
        SCROLL = "scroll", "Scroll"

    class Meta:
        ordering = ["timestamp_ms"]
        indexes = [
            models.Index(fields=["session", "timestamp_ms"]),
        ]

    session = models.ForeignKey(
        BehaviorSession,
        on_delete=models.CASCADE,
        related_name="mouse_events",
    )
    event_type = models.CharField(max_length=8, choices=EventType)
    timestamp_ms = models.FloatField(help_text="ms from session start")
    x = models.IntegerField()
    y = models.IntegerField()
    button = models.CharField(max_length=16, null=True, blank=True)
    delta_x = models.IntegerField(null=True, blank=True)
    delta_y = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return f"[{self.event_type}] ({self.x}, {self.y}) @ {self.timestamp_ms:.0f}ms"
