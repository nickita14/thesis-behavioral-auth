from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.behavior.models import BehaviorSession, KeystrokeEvent, MouseEvent
from apps.behavior.services import BehaviorEventService


def _session_create_url() -> str:
    return reverse("behavior:session-create")


def _session_end_url(session_id: uuid.UUID) -> str:
    return reverse("behavior:session-end", kwargs={"session_id": session_id})


def _keystrokes_url(session_id: uuid.UUID) -> str:
    return reverse("behavior:session-keystrokes", kwargs={"session_id": session_id})


def _mouse_url(session_id: uuid.UUID) -> str:
    return reverse("behavior:session-mouse", kwargs={"session_id": session_id})


def _summary_url(session_id: uuid.UUID) -> str:
    return reverse("behavior:session-summary", kwargs={"session_id": session_id})


def _keystroke_payload() -> dict:
    return {
        "events": [
            {
                "event_type": "keydown",
                "key_code": "KeyA",
                "key_value": "a",
                "timestamp_ms": 123456,
                "relative_time_ms": 120,
            },
            {
                "event_type": "keyup",
                "key_code": "KeyA",
                "key_value": "a",
                "timestamp_ms": 123536,
                "relative_time_ms": 200,
                "dwell_time_ms": 80,
                "flight_time_ms": 30,
            },
        ]
    }


def _mouse_payload() -> dict:
    return {
        "events": [
            {
                "event_type": "move",
                "x": 120,
                "y": 240,
                "timestamp_ms": 123456,
                "relative_time_ms": 150,
            },
            {
                "event_type": "scroll",
                "scroll_delta_x": 0.0,
                "scroll_delta_y": -12.5,
                "timestamp_ms": 123500,
                "relative_time_ms": 194,
            },
        ]
    }


@pytest.mark.django_db
def test_create_behavior_session_returns_201(api_client: APIClient) -> None:
    response = api_client.post(
        _session_create_url(),
        {"is_enrollment": True, "context": {"page": "login", "scenario": "demo"}},
        format="json",
        HTTP_USER_AGENT="pytest-agent",
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "started_at" in data
    assert data["is_enrollment"] is True
    assert data["context"] == {"page": "login", "scenario": "demo"}
    session = BehaviorSession.objects.get(id=data["id"])
    assert session.user is None
    assert session.user_agent == "pytest-agent"


@pytest.mark.django_db
def test_end_session_sets_ended_at(
    api_client: APIClient,
    behavior_session: BehaviorSession,
) -> None:
    response = api_client.post(_session_end_url(behavior_session.id), format="json")

    assert response.status_code == 200
    behavior_session.refresh_from_db()
    assert behavior_session.ended_at is not None


@pytest.mark.django_db
def test_keystroke_batch_insert_creates_events(
    api_client: APIClient,
    behavior_session: BehaviorSession,
) -> None:
    response = api_client.post(
        _keystrokes_url(behavior_session.id),
        _keystroke_payload(),
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["created"] == 2
    assert behavior_session.keystroke_events.count() == 2


@pytest.mark.django_db
def test_raw_key_value_is_not_stored(
    api_client: APIClient,
    behavior_session: BehaviorSession,
) -> None:
    api_client.post(
        _keystrokes_url(behavior_session.id),
        _keystroke_payload(),
        format="json",
    )

    event = KeystrokeEvent.objects.filter(key_code="KeyA").first()
    assert event is not None
    assert not hasattr(event, "key_value")
    assert event.key_value_hash != "a"


@pytest.mark.django_db
def test_key_value_hash_is_stored_when_key_value_provided(
    api_client: APIClient,
    behavior_session: BehaviorSession,
) -> None:
    api_client.post(
        _keystrokes_url(behavior_session.id),
        _keystroke_payload(),
        format="json",
    )

    event = KeystrokeEvent.objects.filter(event_type="keydown").get()
    assert event.key_value_hash == BehaviorEventService.hash_key_value("a")
    assert len(event.key_value_hash) == 64


@pytest.mark.django_db
def test_mouse_batch_insert_creates_events(
    api_client: APIClient,
    behavior_session: BehaviorSession,
) -> None:
    response = api_client.post(
        _mouse_url(behavior_session.id),
        _mouse_payload(),
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["created"] == 2
    assert behavior_session.mouse_events.count() == 2


@pytest.mark.django_db
def test_invalid_session_id_returns_404(api_client: APIClient) -> None:
    response = api_client.post(
        _keystrokes_url(uuid.uuid4()),
        _keystroke_payload(),
        format="json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_invalid_event_type_returns_400(
    api_client: APIClient,
    behavior_session: BehaviorSession,
) -> None:
    payload = _keystroke_payload()
    payload["events"][0]["event_type"] = "keypress"

    response = api_client.post(
        _keystrokes_url(behavior_session.id),
        payload,
        format="json",
    )

    assert response.status_code == 400
    assert "event_type" in str(response.json())


@pytest.mark.django_db
def test_summary_returns_correct_counts(
    api_client: APIClient,
    behavior_session: BehaviorSession,
) -> None:
    api_client.post(_keystrokes_url(behavior_session.id), _keystroke_payload(), format="json")
    api_client.post(_mouse_url(behavior_session.id), _mouse_payload(), format="json")
    behavior_session.ended_at = timezone.now()
    behavior_session.save(update_fields=["ended_at"])

    response = api_client.get(_summary_url(behavior_session.id))

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(behavior_session.id)
    assert data["duration_ms"] is not None
    assert data["keystroke_count"] == 2
    assert data["mouse_count"] == 2
    assert data["is_enrollment"] is False


@pytest.mark.django_db
@override_settings(BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS=True)
def test_anonymous_session_allowed(api_client: APIClient) -> None:
    response = api_client.post(
        _session_create_url(),
        {"is_enrollment": False, "context": {}},
        format="json",
    )

    assert response.status_code == 201
    session = BehaviorSession.objects.get(id=response.json()["id"])
    assert session.user is None


@pytest.mark.django_db
@override_settings(BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS=False)
def test_anonymous_session_rejected_when_disabled(api_client: APIClient) -> None:
    response = api_client.post(
        _session_create_url(),
        {"is_enrollment": False, "context": {}},
        format="json",
    )

    assert response.status_code == 403
    assert "anonymous behavior sessions are disabled" in response.json()["detail"].lower()
    assert BehaviorSession.objects.count() == 0


@pytest.mark.django_db
@override_settings(BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS=False)
def test_authenticated_user_is_attached_to_behavior_session(
    api_client: APIClient,
) -> None:
    user = get_user_model().objects.create_user(
        username="behavior-user",
        password="unused-test-password",
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _session_create_url(),
        {"is_enrollment": True, "context": {"page": "transaction"}},
        format="json",
    )

    assert response.status_code == 201
    session = BehaviorSession.objects.get(id=response.json()["id"])
    assert session.user == user


@pytest.mark.django_db
def test_api_routes_are_wired(api_client: APIClient) -> None:
    create_response = api_client.post(
        reverse("behavior:session-create"),
        {"is_enrollment": False, "context": {"page": "login"}},
        format="json",
    )
    session_id = create_response.json()["id"]

    assert create_response.status_code == 201
    assert api_client.post(reverse("behavior:session-end", kwargs={"session_id": session_id})).status_code == 200
    assert api_client.post(
        reverse("behavior:session-keystrokes", kwargs={"session_id": session_id}),
        _keystroke_payload(),
        format="json",
    ).status_code == 201
    assert api_client.post(
        reverse("behavior:session-mouse", kwargs={"session_id": session_id}),
        _mouse_payload(),
        format="json",
    ).status_code == 201
    assert api_client.get(
        reverse("behavior:session-summary", kwargs={"session_id": session_id})
    ).status_code == 200
