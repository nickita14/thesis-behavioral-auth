from __future__ import annotations

import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.behavior.models import BehaviorSession, KeystrokeEvent, MouseEvent


# ── helpers ──────────────────────────────────────────────────────────────────


def _start_url() -> str:
    return reverse("behavior:session-start")


def _end_url(token: uuid.UUID) -> str:
    return reverse("behavior:session-end", kwargs={"token": token})


def _events_url(token: uuid.UUID) -> str:
    return reverse("behavior:session-events", kwargs={"token": token})


def _detail_url(token: uuid.UUID) -> str:
    return reverse("behavior:session-detail", kwargs={"token": token})


def _keystroke_batch(*pairs: tuple[str, float, float, float | None]) -> dict:
    """Build a minimal valid columnar event payload with only keystrokes."""
    return {
        "schema_version": 1,
        "keystrokes": {
            "fields": ["client_id", "cat", "down", "up", "flight"],
            "data": [
                [cid, "letter", down, up, flight]
                for cid, down, up, flight in pairs
            ],
        },
    }


# ── session start ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_start_session_creates_record_and_returns_token(authenticated_client: APIClient) -> None:
    response = authenticated_client.post(
        _start_url(),
        {"is_enrollment": False, "user_agent": "TestAgent/1.0"},
        format="json",
    )
    assert response.status_code == 201
    data = response.json()
    assert "session_token" in data
    assert "started_at" in data
    assert BehaviorSession.objects.filter(session_token=data["session_token"]).exists()


@pytest.mark.django_db
def test_start_session_requires_authentication() -> None:
    client = APIClient()
    response = client.post(_start_url(), {}, format="json")
    assert response.status_code == 403


# ── session end ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_end_session_sets_ended_at(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    assert session.ended_at is None
    response = authenticated_client.post(_end_url(session.session_token))
    assert response.status_code == 204
    session.refresh_from_db()
    assert session.ended_at is not None


@pytest.mark.django_db
def test_end_session_is_idempotent(
    authenticated_client: APIClient, closed_session: BehaviorSession
) -> None:
    first = authenticated_client.post(_end_url(closed_session.session_token))
    second = authenticated_client.post(_end_url(closed_session.session_token))
    assert first.status_code == 204
    assert second.status_code == 204


@pytest.mark.django_db
def test_end_session_other_user_returns_404(
    other_user: User, session: BehaviorSession
) -> None:
    client = APIClient()
    client.force_authenticate(user=other_user)
    response = client.post(_end_url(session.session_token))
    assert response.status_code == 404


# ── event batch ───────────────────────────────────────────────────────────────


def _valid_batch() -> dict:
    return {
        "schema_version": 1,
        "keystrokes": {
            "fields": ["client_id", "cat", "down", "up", "flight"],
            "data": [
                [str(uuid.uuid4()), "letter", 100.0, 180.0, None],
                [str(uuid.uuid4()), "digit", 200.0, 265.0, 20.0],
            ],
        },
        "mouse": {
            "fields": ["client_id", "type", "t", "x", "y", "btn", "dx", "dy"],
            "data": [
                [str(uuid.uuid4()), "move", 150.0, 300, 200, None, None, None],
            ],
        },
    }


@pytest.mark.django_db
def test_post_events_accepts_valid_batch(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    response = authenticated_client.post(
        _events_url(session.session_token), _valid_batch(), format="json"
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_post_events_returns_correct_counts(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    response = authenticated_client.post(
        _events_url(session.session_token), _valid_batch(), format="json"
    )
    data = response.json()
    assert data["accepted"]["keystrokes"] == 2
    assert data["accepted"]["mouse"] == 1
    assert data["duplicates"]["keystrokes"] == 0
    assert data["duplicates"]["mouse"] == 0


@pytest.mark.django_db
def test_post_events_idempotent_on_duplicate_client_ids(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    batch = _valid_batch()
    authenticated_client.post(_events_url(session.session_token), batch, format="json")
    response = authenticated_client.post(
        _events_url(session.session_token), batch, format="json"
    )
    data = response.json()
    assert data["duplicates"]["keystrokes"] == 2
    assert data["duplicates"]["mouse"] == 1
    assert data["accepted"]["keystrokes"] == 0
    assert data["accepted"]["mouse"] == 0


@pytest.mark.django_db
def test_post_events_rejects_unsupported_schema_version(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    payload = {"schema_version": 99}
    response = authenticated_client.post(
        _events_url(session.session_token), payload, format="json"
    )
    assert response.status_code == 400
    assert "unsupported schema version" in str(response.json())


@pytest.mark.django_db
def test_post_events_rejects_invalid_field_order(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    payload = {
        "schema_version": 1,
        "keystrokes": {
            "fields": ["client_id", "up", "down", "cat", "flight"],  # wrong order
            "data": [],
        },
    }
    response = authenticated_client.post(
        _events_url(session.session_token), payload, format="json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_post_events_rejects_closed_session(
    authenticated_client: APIClient, closed_session: BehaviorSession
) -> None:
    response = authenticated_client.post(
        _events_url(closed_session.session_token), _valid_batch(), format="json"
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_post_events_other_user_returns_404(
    other_user: User, session: BehaviorSession
) -> None:
    client = APIClient()
    client.force_authenticate(user=other_user)
    response = client.post(_events_url(session.session_token), _valid_batch(), format="json")
    assert response.status_code == 404


@pytest.mark.django_db
def test_post_events_rejects_oversized_batch(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    rows = [
        [str(uuid.uuid4()), "letter", float(i), float(i) + 80, None]
        for i in range(501)
    ]
    payload = {
        "schema_version": 1,
        "keystrokes": {
            "fields": ["client_id", "cat", "down", "up", "flight"],
            "data": rows,
        },
    }
    response = authenticated_client.post(
        _events_url(session.session_token), payload, format="json"
    )
    assert response.status_code == 400


# ── session detail ────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_session_returns_counts(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    KeystrokeEvent.objects.create(
        session=session,
        key_category="letter",
        key_down_at=100.0,
        key_up_at=180.0,
        dwell_time_ms=80.0,
    )
    MouseEvent.objects.create(
        session=session,
        event_type="move",
        timestamp_ms=150.0,
        x=100,
        y=200,
    )
    response = authenticated_client.get(_detail_url(session.session_token))
    assert response.status_code == 200
    data = response.json()
    assert data["counts"]["keystrokes"] == 1
    assert data["counts"]["mouse_events"] == 1
    assert str(session.session_token) == data["session_token"]


# ── dwell_time computed in bulk_create ────────────────────────────────────────


@pytest.mark.django_db
def test_dwell_time_is_computed_for_bulk_inserted_keystrokes(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    cid = str(uuid.uuid4())
    payload = {
        "schema_version": 1,
        "keystrokes": {
            "fields": ["client_id", "cat", "down", "up", "flight"],
            "data": [[cid, "letter", 1000.0, 1075.0, None]],
        },
    }
    authenticated_client.post(_events_url(session.session_token), payload, format="json")
    event = KeystrokeEvent.objects.get(client_event_id=cid)
    assert event.dwell_time_ms == pytest.approx(75.0)


# ── partial batch (one type absent) ──────────────────────────────────────────


@pytest.mark.django_db
def test_post_events_accepts_keystrokes_only(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    payload = {
        "schema_version": 1,
        "keystrokes": {
            "fields": ["client_id", "cat", "down", "up", "flight"],
            "data": [[str(uuid.uuid4()), "letter", 100.0, 180.0, None]],
        },
    }
    response = authenticated_client.post(
        _events_url(session.session_token), payload, format="json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"]["keystrokes"] == 1
    assert data["accepted"]["mouse"] == 0


@pytest.mark.django_db
def test_post_events_accepts_mouse_only(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    payload = {
        "schema_version": 1,
        "mouse": {
            "fields": ["client_id", "type", "t", "x", "y", "btn", "dx", "dy"],
            "data": [[str(uuid.uuid4()), "move", 150.0, 300, 200, None, None, None]],
        },
    }
    response = authenticated_client.post(
        _events_url(session.session_token), payload, format="json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"]["keystrokes"] == 0
    assert data["accepted"]["mouse"] == 1


@pytest.mark.django_db
def test_post_events_rejects_both_missing(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    payload = {"schema_version": 1}
    response = authenticated_client.post(
        _events_url(session.session_token), payload, format="json"
    )
    assert response.status_code == 400
    assert "non-empty" in str(response.json())


@pytest.mark.django_db
def test_post_events_rejects_both_empty(
    authenticated_client: APIClient, session: BehaviorSession
) -> None:
    payload = {
        "schema_version": 1,
        "keystrokes": {
            "fields": ["client_id", "cat", "down", "up", "flight"],
            "data": [],
        },
        "mouse": {
            "fields": ["client_id", "type", "t", "x", "y", "btn", "dx", "dy"],
            "data": [],
        },
    }
    response = authenticated_client.post(
        _events_url(session.session_token), payload, format="json"
    )
    assert response.status_code == 400
    assert "non-empty" in str(response.json())
