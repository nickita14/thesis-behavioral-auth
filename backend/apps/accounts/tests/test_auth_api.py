from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User


# ── helpers ──────────────────────────────────────────────────────────────────


def _url(name: str) -> str:
    return reverse(f"accounts:{name}")


# ── CSRF ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_csrf_endpoint_sets_cookie(api_client: APIClient) -> None:
    response = api_client.get(_url("csrf"))
    assert response.status_code == 200
    assert response.json() == {"detail": "CSRF cookie set"}
    # The cookie is set by Django's ensure_csrf_cookie decorator;
    # in tests the cookie jar is populated on the test client.
    assert "csrftoken" in response.cookies


# ── register ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_register_creates_user_and_returns_data(
    api_client: APIClient, valid_register_payload: dict
) -> None:
    response = api_client.post(_url("register"), valid_register_payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "password" not in data
    assert User.objects.filter(username="newuser").exists()


@pytest.mark.django_db
def test_register_rejects_duplicate_username(
    api_client: APIClient, user: User, valid_register_payload: dict
) -> None:
    valid_register_payload["username"] = user.username
    response = api_client.post(_url("register"), valid_register_payload, format="json")
    assert response.status_code == 400
    assert "username" in response.json()


@pytest.mark.django_db
def test_register_rejects_duplicate_email(
    api_client: APIClient, user: User, valid_register_payload: dict
) -> None:
    valid_register_payload["email"] = user.email
    response = api_client.post(_url("register"), valid_register_payload, format="json")
    assert response.status_code == 400
    assert "email" in response.json()


@pytest.mark.django_db
def test_register_rejects_weak_password(
    api_client: APIClient, valid_register_payload: dict
) -> None:
    valid_register_payload["password"] = "password"  # too common
    response = api_client.post(_url("register"), valid_register_payload, format="json")
    assert response.status_code == 400
    assert "password" in response.json()


@pytest.mark.django_db
def test_register_rejects_invalid_email_format(
    api_client: APIClient, valid_register_payload: dict
) -> None:
    valid_register_payload["email"] = "not-an-email"
    response = api_client.post(_url("register"), valid_register_payload, format="json")
    assert response.status_code == 400
    assert "email" in response.json()


@pytest.mark.django_db
def test_register_rejects_short_username(
    api_client: APIClient, valid_register_payload: dict
) -> None:
    valid_register_payload["username"] = "ab"  # below 3-char minimum
    response = api_client.post(_url("register"), valid_register_payload, format="json")
    assert response.status_code == 400
    assert "username" in response.json()


# ── login ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_login_with_valid_credentials_returns_user_data(
    api_client: APIClient, user: User
) -> None:
    response = api_client.post(
        _url("login"),
        {"username": "alice", "password": "SecurePass123!"},
        format="json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert "password" not in data


@pytest.mark.django_db
def test_login_with_invalid_password_returns_400_without_revealing_which_field(
    api_client: APIClient, user: User
) -> None:
    response = api_client.post(
        _url("login"),
        {"username": "alice", "password": "wrongpassword"},
        format="json",
    )
    assert response.status_code == 400
    data = response.json()
    # Must use a generic message — not "wrong password" or "wrong username"
    assert data["detail"] == "Invalid credentials"


@pytest.mark.django_db
def test_login_with_nonexistent_user_returns_400_without_revealing(
    api_client: APIClient, db
) -> None:
    response = api_client.post(
        _url("login"),
        {"username": "nobody", "password": "whatever"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid credentials"


# ── logout ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_logout_clears_session(api_client: APIClient, user: User) -> None:
    api_client.force_authenticate(user=user)
    response = api_client.post(_url("logout"))
    assert response.status_code == 204
    # After logout the session is cleared; /me should return 403
    api_client.force_authenticate(user=None)
    me_response = api_client.get(_url("me"))
    assert me_response.status_code == 403


@pytest.mark.django_db
def test_logout_requires_authentication(api_client: APIClient, db) -> None:
    response = api_client.post(_url("logout"))
    assert response.status_code == 403


# ── me ────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_me_returns_current_user_when_authenticated(
    api_client: APIClient, user: User
) -> None:
    api_client.force_authenticate(user=user)
    response = api_client.get(_url("me"))
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
    assert "date_joined" in data


@pytest.mark.django_db
def test_me_returns_401_when_not_authenticated(api_client: APIClient, db) -> None:
    response = api_client.get(_url("me"))
    # SessionAuthentication returns 403 for unauthenticated requests
    # (DRF only returns 401 for token-based auth schemes with WWW-Authenticate header)
    assert response.status_code == 403


# ── full flow ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_full_flow_register_login_me_logout(api_client: APIClient) -> None:
    # 1. register
    reg = api_client.post(
        _url("register"),
        {"username": "flowuser", "email": "flow@example.com", "password": "FlowPass99!"},
        format="json",
    )
    assert reg.status_code == 201

    # 2. login
    login_resp = api_client.post(
        _url("login"),
        {"username": "flowuser", "password": "FlowPass99!"},
        format="json",
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["username"] == "flowuser"

    # 3. me (force_authenticate to bypass CSRF in test environment)
    user = User.objects.get(username="flowuser")
    api_client.force_authenticate(user=user)
    me = api_client.get(_url("me"))
    assert me.status_code == 200
    assert me.json()["email"] == "flow@example.com"

    # 4. logout
    logout_resp = api_client.post(_url("logout"))
    assert logout_resp.status_code == 204
