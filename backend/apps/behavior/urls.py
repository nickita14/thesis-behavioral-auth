from __future__ import annotations

from django.urls import path

from .views import EventBatchView, SessionDetailView, SessionEndView, SessionStartView

app_name = "behavior"

urlpatterns = [
    path("sessions/start/", SessionStartView.as_view(), name="session-start"),
    path("sessions/<uuid:token>/end/", SessionEndView.as_view(), name="session-end"),
    path("sessions/<uuid:token>/events/", EventBatchView.as_view(), name="session-events"),
    path("sessions/<uuid:token>/", SessionDetailView.as_view(), name="session-detail"),
]
