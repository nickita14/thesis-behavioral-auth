from __future__ import annotations

from django.contrib import admin

from .models import BehaviorSession, KeystrokeEvent, MouseEvent


class KeystrokeEventInline(admin.TabularInline):
    model = KeystrokeEvent
    extra = 0
    fields = ("event_type", "key_code", "timestamp_ms", "relative_time_ms")
    readonly_fields = ("key_value_hash", "created_at")


class MouseEventInline(admin.TabularInline):
    model = MouseEvent
    extra = 0
    fields = ("event_type", "x", "y", "button", "timestamp_ms", "relative_time_ms")
    readonly_fields = ("created_at",)


@admin.register(BehaviorSession)
class BehaviorSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_enrollment", "ip_address", "started_at", "ended_at")
    list_filter = ("is_enrollment",)
    search_fields = ("id", "session_key", "user__username", "ip_address")
    readonly_fields = ("id", "started_at")
    inlines = [KeystrokeEventInline, MouseEventInline]


@admin.register(KeystrokeEvent)
class KeystrokeEventAdmin(admin.ModelAdmin):
    list_display = ("id", "behavior_session", "event_type", "key_code", "timestamp_ms")
    list_filter = ("event_type",)
    search_fields = ("behavior_session__id", "key_code")
    readonly_fields = ("key_value_hash", "created_at")


@admin.register(MouseEvent)
class MouseEventAdmin(admin.ModelAdmin):
    list_display = ("id", "behavior_session", "event_type", "x", "y", "timestamp_ms")
    list_filter = ("event_type",)
    search_fields = ("behavior_session__id",)
