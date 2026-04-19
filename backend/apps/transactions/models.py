from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class RiskDecision(models.TextChoices):
    """Shared decision vocabulary across TransactionAttempt and RiskAssessment."""

    ALLOW = "allow", "Allow"
    CHALLENGE = "challenge", "Challenge (2FA)"
    DENY = "deny", "Deny"
    PENDING = "pending", "Pending"


class TransactionAttempt(models.Model):
    """A user's attempt to execute a financial transaction.

    risk_score and decision are initially null/pending and are filled in
    by RiskDecisionEngine after behavioral and phishing scores are computed.
    session may be null if the transaction was initiated outside a
    tracked browser session (e.g. API call).
    """

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["decision"]),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transaction_attempts",
    )
    session = models.ForeignKey(
        "behavior.BehaviorSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction_attempts",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    recipient_account = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    risk_score = models.FloatField(null=True, blank=True)
    decision = models.CharField(
        max_length=16,
        choices=RiskDecision,
        default=RiskDecision.PENDING,
    )

    def __str__(self) -> str:
        return f"{self.user} → {self.recipient_account} {self.amount} [{self.decision}]"


class RiskAssessment(models.Model):
    """Detailed ML scores for a single TransactionAttempt.

    One attempt may have multiple assessments if re-evaluated (e.g. after
    user completes a 2FA challenge). model_versions records the exact
    joblib artifact versions used, enabling reproducibility audits.
    """

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["attempt", "created_at"]),
        ]

    attempt = models.ForeignKey(
        TransactionAttempt,
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    behavior_score = models.FloatField(null=True, blank=True)
    phishing_score = models.FloatField(null=True, blank=True)
    combined_score = models.FloatField()
    decision = models.CharField(max_length=16, choices=RiskDecision)
    created_at = models.DateTimeField(auto_now_add=True)
    model_versions = models.JSONField(default=dict)

    def __str__(self) -> str:
        return (
            f"Assessment({self.attempt_id}) "
            f"combined={self.combined_score:.3f} [{self.decision}]"
        )
