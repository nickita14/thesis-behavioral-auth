from __future__ import annotations

from django.urls import path

from .views import PhishingCheckView

app_name = "phishing"

urlpatterns = [
    path("check/", PhishingCheckView.as_view(), name="check"),
]
