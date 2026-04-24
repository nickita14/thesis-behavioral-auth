from __future__ import annotations

from rest_framework import serializers

from .models import BehaviorSession, KeystrokeEvent, MouseEvent

MAX_BATCH_EVENTS = 500


class BehaviorSessionCreateSerializer(serializers.Serializer):
    """Validates POST /api/behavior/sessions/."""

    is_enrollment = serializers.BooleanField(default=False)
    context = serializers.JSONField(default=dict)


class BehaviorSessionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorSession
        fields = ["id", "started_at", "is_enrollment", "context"]


class KeystrokeEventInputSerializer(serializers.Serializer):
    """Validates one keystroke event.

    key_value is accepted only as write-only input and is never returned or
    saved directly. The service stores key_value_hash instead.
    """

    event_type = serializers.ChoiceField(choices=KeystrokeEvent.EventType.choices)
    key_code = serializers.CharField(max_length=64, allow_blank=True, required=False)
    key_value = serializers.CharField(
        allow_blank=True,
        required=False,
        write_only=True,
        trim_whitespace=False,
    )
    timestamp_ms = serializers.IntegerField(min_value=0)
    relative_time_ms = serializers.IntegerField(min_value=0)
    dwell_time_ms = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    flight_time_ms = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    metadata = serializers.JSONField(default=dict, required=False)


class KeystrokeBatchSerializer(serializers.Serializer):
    events = KeystrokeEventInputSerializer(many=True)

    def validate_events(self, value: list[dict]) -> list[dict]:
        return _validate_batch_size(value)


class MouseEventInputSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(choices=MouseEvent.EventType.choices)
    x = serializers.IntegerField(required=False, allow_null=True)
    y = serializers.IntegerField(required=False, allow_null=True)
    button = serializers.CharField(max_length=32, allow_blank=True, required=False)
    scroll_delta_x = serializers.FloatField(required=False, allow_null=True)
    scroll_delta_y = serializers.FloatField(required=False, allow_null=True)
    timestamp_ms = serializers.IntegerField(min_value=0)
    relative_time_ms = serializers.IntegerField(min_value=0)
    metadata = serializers.JSONField(default=dict, required=False)


class MouseBatchSerializer(serializers.Serializer):
    events = MouseEventInputSerializer(many=True)

    def validate_events(self, value: list[dict]) -> list[dict]:
        return _validate_batch_size(value)


class BehaviorSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    duration_ms = serializers.IntegerField(allow_null=True)
    keystroke_count = serializers.IntegerField()
    mouse_count = serializers.IntegerField()
    is_enrollment = serializers.BooleanField()


def _validate_batch_size(events: list[dict]) -> list[dict]:
    if not events:
        raise serializers.ValidationError("events must be non-empty")
    if len(events) > MAX_BATCH_EVENTS:
        raise serializers.ValidationError(
            f"batch exceeds maximum of {MAX_BATCH_EVENTS} events"
        )
    return events
