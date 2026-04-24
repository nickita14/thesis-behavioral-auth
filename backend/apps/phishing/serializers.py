from __future__ import annotations

from dataclasses import asdict

from rest_framework import serializers

from .detectors import PhishingPrediction


class PhishingCheckRequestSerializer(serializers.Serializer):
    """Validates POST /api/phishing/check/ request body."""

    url = serializers.URLField(max_length=2048)


class PhishingPredictionSerializer(serializers.Serializer):
    """Shapes phishing detector output for API clients."""

    url = serializers.URLField()
    probability_phishing = serializers.FloatField()
    probability_legitimate = serializers.FloatField()
    decision = serializers.ChoiceField(
        choices=["legitimate", "suspicious", "phishing"]
    )
    from_cache = serializers.BooleanField()
    features = serializers.SerializerMethodField()

    def get_features(self, obj: PhishingPrediction) -> dict[str, int]:
        return asdict(obj.features)
