from __future__ import annotations

from django.urls import path

from .views import TransactionAttemptListCreateView

app_name = "transactions"

urlpatterns = [
    path("attempts/", TransactionAttemptListCreateView.as_view(), name="attempt-list-create"),
]
