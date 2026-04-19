from __future__ import annotations

from django.contrib import admin

from .models import PhishingEvent


@admin.register(PhishingEvent)
class PhishingEventAdmin(admin.ModelAdmin):
    list_display = ("id", "short_url", "is_phishing_predicted", "confidence", "session", "created_at")
    list_filter = ("is_phishing_predicted",)
    search_fields = ("url",)
    readonly_fields = ("id", "created_at")

    @admin.display(description="URL")
    def short_url(self, obj: PhishingEvent) -> str:
        return obj.url[:60] + ("…" if len(obj.url) > 60 else "")
