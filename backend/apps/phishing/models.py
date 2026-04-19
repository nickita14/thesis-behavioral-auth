from __future__ import annotations

import uuid

from django.db import models


class PhishingEvent(models.Model):
    """Result of a phishing URL classification for a URL seen in a session.

    url_features stores the raw extracted feature vector as JSON so that
    the record is self-contained for later audit and model retraining.
    session is nullable: URLs can be checked via direct API without an
    active browser session (e.g. from a browser extension or batch job).
    """

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["is_phishing_predicted"]),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        "behavior.BehaviorSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="phishing_events",
    )
    url = models.URLField(max_length=2048)
    url_features = models.JSONField(default=dict)
    is_phishing_predicted = models.BooleanField()
    confidence = models.FloatField(help_text="Model confidence in [0, 1]")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        verdict = "PHISHING" if self.is_phishing_predicted else "clean"
        return f"[{verdict}] {self.url[:60]} (conf={self.confidence:.2f})"
