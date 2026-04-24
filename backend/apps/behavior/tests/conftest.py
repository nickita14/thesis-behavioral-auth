from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.behavior.models import BehaviorSession


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def behavior_session(db) -> BehaviorSession:
    return BehaviorSession.objects.create(
        session_key=str(uuid.uuid4()),
        context={"page": "login"},
        ip_address="127.0.0.1",
        user_agent="pytest",
        is_enrollment=False,
    )
