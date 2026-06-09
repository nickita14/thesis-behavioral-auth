from __future__ import annotations

from django.urls import path

from .views import BehaviorProfileDeleteView, BehaviorProfileStatusView, BehaviorProfileTrainView

app_name = "ml_engine"

urlpatterns = [
    path(
        "behavior-profile/train/",
        BehaviorProfileTrainView.as_view(),
        name="train-profile",
    ),
    path(
        "behavior-profile/status/",
        BehaviorProfileStatusView.as_view(),
        name="profile-status",
    ),
    path(
        "behavior-profile/",
        BehaviorProfileDeleteView.as_view(),
        name="delete-profile",
    ),
]
