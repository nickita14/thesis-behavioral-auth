from __future__ import annotations

from rest_framework import serializers

from .models import BehaviorSession

# ── columnar payload field names ────────────────────────────────────────────

KEYSTROKE_FIELDS = ["client_id", "cat", "down", "up", "flight"]
MOUSE_FIELDS = ["client_id", "type", "t", "x", "y", "btn", "dx", "dy"]

VALID_KEY_CATEGORIES = {"letter", "digit", "special", "modifier"}
VALID_EVENT_TYPES = {"move", "click", "scroll"}

MAX_BATCH_EVENTS = 500


# ── session serializers ──────────────────────────────────────────────────────


class SessionStartSerializer(serializers.Serializer):
    """Validates the body of POST /api/behavior/sessions/start/."""

    is_enrollment = serializers.BooleanField(default=False)
    user_agent = serializers.CharField(default="", allow_blank=True)
    # Reserved for future client-server clock correction; ignored for now.
    client_started_at = serializers.DateTimeField(required=False)


class SessionStartResponseSerializer(serializers.ModelSerializer):
    """Shapes the 201 response of POST /api/behavior/sessions/start/."""

    class Meta:
        model = BehaviorSession
        fields = ["session_token", "started_at"]


class SessionDetailSerializer(serializers.ModelSerializer):
    """Shapes the 200 response of GET /api/behavior/sessions/{token}/."""

    counts = serializers.SerializerMethodField()

    class Meta:
        model = BehaviorSession
        fields = [
            "session_token",
            "started_at",
            "ended_at",
            "is_enrollment",
            "ip_address",
            "counts",
        ]

    def get_counts(self, obj: BehaviorSession) -> dict[str, int]:
        return {
            "keystrokes": getattr(obj, "keystroke_count", 0),
            "mouse_events": getattr(obj, "mouse_event_count", 0),
        }


# ── columnar event batch serializer ─────────────────────────────────────────


class ColumnarBlockSerializer(serializers.Serializer):
    """Validates one columnar block (keystrokes or mouse)."""

    fields = serializers.ListField(child=serializers.CharField())
    data = serializers.ListField(child=serializers.ListField())


class EventBatchSerializer(serializers.Serializer):
    """Validates POST /api/behavior/sessions/{token}/events/ body."""

    schema_version = serializers.IntegerField()
    client_time = serializers.DateTimeField(required=False)
    keystrokes = ColumnarBlockSerializer(required=False)
    mouse = ColumnarBlockSerializer(required=False)

    def validate_schema_version(self, value: int) -> int:
        if value != 1:
            raise serializers.ValidationError("unsupported schema version")
        return value

    def validate_keystrokes(self, value: dict) -> dict:
        if value["fields"] != KEYSTROKE_FIELDS:
            raise serializers.ValidationError(
                f"fields must be exactly {KEYSTROKE_FIELDS} in that order"
            )
        self._validate_rows(value["data"], len(KEYSTROKE_FIELDS), "keystrokes")
        return value

    def validate_mouse(self, value: dict) -> dict:
        if value["fields"] != MOUSE_FIELDS:
            raise serializers.ValidationError(
                f"fields must be exactly {MOUSE_FIELDS} in that order"
            )
        self._validate_rows(value["data"], len(MOUSE_FIELDS), "mouse")
        return value

    def validate(self, attrs: dict) -> dict:
        ks_count = len((attrs.get("keystrokes") or {}).get("data", []))
        ms_count = len((attrs.get("mouse") or {}).get("data", []))
        if ks_count + ms_count == 0:
            raise serializers.ValidationError(
                "at least one of keystrokes or mouse must be non-empty"
            )
        if ks_count + ms_count > MAX_BATCH_EVENTS:
            raise serializers.ValidationError(
                f"batch exceeds maximum of {MAX_BATCH_EVENTS} events"
            )
        return attrs

    @staticmethod
    def _validate_rows(data: list, expected_width: int, block: str) -> None:
        for i, row in enumerate(data):
            if len(row) != expected_width:
                raise serializers.ValidationError(
                    f"{block} row {i}: expected {expected_width} columns, got {len(row)}"
                )
