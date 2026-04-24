from __future__ import annotations

from django.urls import path

from .views import (
    BehaviorDashboardView,
    BehaviorSessionCreateView,
    BehaviorSessionEndView,
    BehaviorSummaryView,
    KeystrokeBatchView,
    MouseBatchView,
)

app_name = "behavior"

urlpatterns = [
    path("dashboard/", BehaviorDashboardView.as_view(), name="dashboard"),
    path("sessions/", BehaviorSessionCreateView.as_view(), name="session-create"),
    path("sessions/<uuid:session_id>/end/", BehaviorSessionEndView.as_view(), name="session-end"),
    path(
        "sessions/<uuid:session_id>/keystrokes/",
        KeystrokeBatchView.as_view(),
        name="session-keystrokes",
    ),
    path(
        "sessions/<uuid:session_id>/mouse/",
        MouseBatchView.as_view(),
        name="session-mouse",
    ),
    path(
        "sessions/<uuid:session_id>/summary/",
        BehaviorSummaryView.as_view(),
        name="session-summary",
    ),
]
