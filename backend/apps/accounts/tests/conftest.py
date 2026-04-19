from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="SecurePass123!",
    )


@pytest.fixture
def valid_register_payload() -> dict:
    return {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "SecurePass123!",
    }
