from __future__ import annotations

from django.contrib import admin

from .models import RiskAssessment, TransactionAttempt


class RiskAssessmentInline(admin.TabularInline):
    model = RiskAssessment
    extra = 0
    readonly_fields = ("created_at",)
    fields = (
        "behavior_score",
        "phishing_score",
        "combined_score",
        "decision",
        "model_versions",
        "created_at",
    )


@admin.register(TransactionAttempt)
class TransactionAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "recipient_account", "decision", "risk_score", "created_at")
    list_filter = ("decision",)
    search_fields = ("user__username", "recipient_account", "id")
    readonly_fields = ("id", "created_at")
    inlines = [RiskAssessmentInline]


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "behavior_score", "phishing_score", "combined_score", "decision", "created_at")
    list_filter = ("decision",)
    search_fields = ("attempt__id",)
    readonly_fields = ("created_at",)
