from __future__ import annotations

from django.contrib import admin

from .models import BehaviorSession, KeystrokeEvent, MouseEvent


class KeystrokeEventInline(admin.TabularInline):
    model = KeystrokeEvent
    extra = 0
    readonly_fields = ("dwell_time_ms",)
    fields = ("key_category", "key_down_at", "key_up_at", "dwell_time_ms", "flight_time_ms")


class MouseEventInline(admin.TabularInline):
    model = MouseEvent
    extra = 0
    fields = ("event_type", "timestamp_ms", "x", "y", "button", "delta_x", "delta_y")


@admin.register(BehaviorSession)
class BehaviorSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_enrollment", "ip_address", "started_at", "ended_at")
    list_filter = ("is_enrollment",)
    search_fields = ("user__username", "ip_address", "session_token")
    readonly_fields = ("id", "session_token", "started_at")
    inlines = [KeystrokeEventInline, MouseEventInline]


@admin.register(KeystrokeEvent)
class KeystrokeEventAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "key_category", "dwell_time_ms", "flight_time_ms", "key_down_at")
    list_filter = ("key_category",)
    search_fields = ("session__id",)
    readonly_fields = ("dwell_time_ms",)


@admin.register(MouseEvent)
class MouseEventAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "event_type", "x", "y", "timestamp_ms")
    list_filter = ("event_type",)
    search_fields = ("session__id",)
