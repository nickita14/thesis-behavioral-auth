from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import RiskAssessment, RiskDecision, TransactionAttempt


class TransactionAttemptCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    currency = serializers.CharField(max_length=3, default="MDL")
    recipient = serializers.CharField(max_length=64)
    behavior_session_id = serializers.UUIDField(required=False, allow_null=True)
    target_url = serializers.URLField(required=False, allow_blank=True)

    def validate_currency(self, value: str) -> str:
        normalized = value.upper()
        if len(normalized) != 3:
            raise serializers.ValidationError("Currency must be a 3-letter ISO code.")
        return normalized


class TransactionAttemptSerializer(serializers.ModelSerializer):
    recipient = serializers.CharField(source="recipient_account")
    decision = serializers.SerializerMethodField()
    behavior_session_id = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    target_url = serializers.SerializerMethodField()
    phishing = serializers.SerializerMethodField()
    behavior = serializers.SerializerMethodField()
    reasons = serializers.SerializerMethodField()
    explanation = serializers.SerializerMethodField()

    class Meta:
        model = TransactionAttempt
        fields = [
            "id",
            "amount",
            "currency",
            "recipient",
            "decision",
            "risk_score",
            "created_at",
            "behavior_session_id",
            "target_url",
            "phishing",
            "behavior",
            "reasons",
            "explanation",
        ]

    def get_decision(self, obj: TransactionAttempt) -> str:
        return obj.decision.upper()

    def get_behavior_session_id(self, obj: TransactionAttempt) -> str | None:
        return str(obj.session_id) if obj.session_id else None

    def get_currency(self, obj: TransactionAttempt) -> str:
        return self._metadata(obj).get("currency", "MDL")

    def get_target_url(self, obj: TransactionAttempt) -> str:
        return self._metadata(obj).get("target_url", "")

    def get_phishing(self, obj: TransactionAttempt) -> dict | None:
        metadata = self._metadata(obj)
        if not metadata.get("target_url"):
            return None
        return {
            "available": metadata.get("phishing_available", False),
            "decision": metadata.get("phishing_decision", "unknown"),
            "probability_phishing": metadata.get("probability_phishing"),
            "probability_legitimate": metadata.get("probability_legitimate"),
        }

    def get_behavior(self, obj: TransactionAttempt) -> dict:
        metadata = self._metadata(obj)
        return {
            "available": metadata.get("behavior_available", False),
            "decision": metadata.get("behavior_decision", "not_available"),
            "anomaly_score": metadata.get("behavior_anomaly_score"),
            "features": metadata.get("behavior_features", {}),
        }

    def get_reasons(self, obj: TransactionAttempt) -> list[str]:
        reasons = self._metadata(obj).get("reasons", [])
        return reasons if isinstance(reasons, list) else []

    def get_explanation(self, obj: TransactionAttempt) -> str:
        reasons = self.get_reasons(obj)
        if reasons:
            return " ".join(reasons)
        if obj.decision == RiskDecision.DENY:
            return "Transaction denied because the target URL was classified as phishing."
        if obj.decision == RiskDecision.CHALLENGE:
            metadata = self._metadata(obj)
            if metadata.get("phishing_available") is False:
                return "Phishing check was unavailable; transaction requires additional verification."
            return "Transaction requires additional verification because the URL is suspicious."
        return "Transaction allowed by the current skeleton decision policy."

    @staticmethod
    def _metadata(obj: TransactionAttempt) -> dict:
        assessment = getattr(obj, "latest_assessment", None)
        if assessment is None:
            assessment = obj.assessments.order_by("-created_at").first()
        if not isinstance(assessment, RiskAssessment):
            return {}
        return assessment.model_versions or {}
