from __future__ import annotations

import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.behavior.models import BehaviorSession


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username="alice", password="pass")


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(username="bob", password="pass")


@pytest.fixture
def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def session(user: User) -> BehaviorSession:
    return BehaviorSession.objects.create(
        user=user,
        ip_address="127.0.0.1",
        is_enrollment=False,
    )


@pytest.fixture
def closed_session(user: User) -> BehaviorSession:
    return BehaviorSession.objects.create(
        user=user,
        ip_address="127.0.0.1",
        ended_at=timezone.now(),
    )
