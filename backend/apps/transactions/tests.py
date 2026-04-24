from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.behavior.models import BehaviorSession
from apps.ml_engine.behavior_detectors import BehaviorAnomalyResult
from apps.ml_engine.behavior_features import BehaviorFeatures
from apps.transactions.models import RiskAssessment, RiskDecision, TransactionAttempt


def _url() -> str:
    return reverse("transactions:attempt-list-create")


def _payload(**overrides) -> dict:
    payload = {
        "amount": "150.00",
        "currency": "MDL",
        "recipient": "Test Recipient",
        "target_url": "",
    }
    payload.update(overrides)
    return payload


def _user(username: str = "transaction-user"):
    return get_user_model().objects.create_user(
        username=username,
        password="unused-test-password",
    )


def _phishing_prediction(decision: str, probability: float = 0.7):
    return SimpleNamespace(
        decision=decision,
        probability_phishing=probability,
        probability_legitimate=1 - probability,
    )


@pytest.mark.django_db
def test_unauthenticated_transaction_attempt_rejected() -> None:
    response = APIClient().post(_url(), _payload(), format="json")

    assert response.status_code in {401, 403}
    assert TransactionAttempt.objects.count() == 0


@pytest.mark.django_db
def test_authenticated_user_can_create_transaction_attempt() -> None:
    client = APIClient()
    user = _user()
    client.force_authenticate(user=user)

    response = client.post(_url(), _payload(), format="json")

    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == "150.00"
    assert data["currency"] == "MDL"
    assert data["recipient"] == "Test Recipient"
    assert data["decision"] == "ALLOW"
    attempt = TransactionAttempt.objects.get()
    assert attempt.user == user
    assert attempt.decision == RiskDecision.ALLOW
    assert attempt.assessments.count() == 1


@pytest.mark.django_db
def test_user_cannot_attach_another_users_behavior_session() -> None:
    client = APIClient()
    user = _user("owner")
    other_user = _user("other")
    session = BehaviorSession.objects.create(user=other_user, context={})
    client.force_authenticate(user=user)

    response = client.post(
        _url(),
        _payload(behavior_session_id=str(session.id)),
        format="json",
    )

    assert response.status_code == 403
    assert TransactionAttempt.objects.count() == 0


@pytest.mark.django_db
def test_list_returns_only_current_users_attempts() -> None:
    client = APIClient()
    user = _user("current")
    other_user = _user("other")
    current_attempt = TransactionAttempt.objects.create(
        user=user,
        amount="10.00",
        recipient_account="Current Recipient",
        risk_score=0.0,
        decision=RiskDecision.ALLOW,
    )
    RiskAssessment.objects.create(
        attempt=current_attempt,
        combined_score=0.0,
        decision=RiskDecision.ALLOW,
        model_versions={"currency": "MDL", "target_url": ""},
    )
    TransactionAttempt.objects.create(
        user=other_user,
        amount="99.00",
        recipient_account="Other Recipient",
        risk_score=1.0,
        decision=RiskDecision.DENY,
    )
    client.force_authenticate(user=user)

    response = client.get(_url())

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(current_attempt.id)
    assert data[0]["recipient"] == "Current Recipient"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("phishing_decision", "expected_decision"),
    [("suspicious", "CHALLENGE"), ("phishing", "DENY")],
)
def test_phishing_url_maps_to_challenge_or_deny(
    phishing_decision: str,
    expected_decision: str,
) -> None:
    client = APIClient()
    user = _user()
    client.force_authenticate(user=user)
    phishing_service = Mock()
    phishing_service.check_url.return_value = _phishing_prediction(phishing_decision, 0.82)

    with patch(
        "apps.transactions.services.get_phishing_check_service",
        return_value=phishing_service,
    ):
        response = client.post(
            _url(),
            _payload(target_url="https://example.com/payment"),
            format="json",
        )

    assert response.status_code == 201
    assert response.json()["decision"] == expected_decision
    assert response.json()["phishing"]["decision"] == phishing_decision
    phishing_service.check_url.assert_called_once_with("https://example.com/payment")


@pytest.mark.django_db
def test_phishing_service_exception_handled_safely() -> None:
    client = APIClient()
    user = _user()
    client.force_authenticate(user=user)
    phishing_service = Mock()
    phishing_service.check_url.side_effect = RuntimeError("model unavailable")

    with patch(
        "apps.transactions.services.get_phishing_check_service",
        return_value=phishing_service,
    ):
        response = client.post(
            _url(),
            _payload(target_url="https://example.com/payment"),
            format="json",
        )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "CHALLENGE"
    assert data["phishing"]["available"] is False
    assert "phishing check was unavailable" in data["explanation"].lower()


@pytest.mark.django_db
def test_transaction_with_own_behavior_session_includes_behavior_result() -> None:
    client = APIClient()
    user = _user()
    session = BehaviorSession.objects.create(user=user, context={"page": "transaction"})
    client.force_authenticate(user=user)

    response = client.post(
        _url(),
        _payload(behavior_session_id=str(session.id)),
        format="json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["behavior_session_id"] == str(session.id)
    assert data["behavior"]["decision"] == "suspicious"
    assert data["behavior"]["anomaly_score"] == 0.0
    assert isinstance(data["behavior"]["features"], dict)
    assessment = RiskAssessment.objects.get()
    assert assessment.behavior_score == 0.0
    assert assessment.model_versions["behavior_decision"] == "suspicious"


@pytest.mark.django_db
def test_anomalous_behavior_maps_to_challenge() -> None:
    client = APIClient()
    user = _user()
    session = BehaviorSession.objects.create(user=user, context={})
    client.force_authenticate(user=user)

    with patch(
        "apps.transactions.services.BehaviorFeatureExtractor.extract",
        return_value=BehaviorFeatures(keystroke_count=10),
    ), patch(
        "apps.transactions.services.BehaviorAnomalyDetector.predict",
        return_value=BehaviorAnomalyResult(
            anomaly_score=0.91,
            is_anomaly=True,
            decision="anomalous",
        ),
    ):
        response = client.post(
            _url(),
            _payload(behavior_session_id=str(session.id)),
            format="json",
        )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "CHALLENGE"
    assert data["behavior"]["decision"] == "anomalous"
    assert data["behavior"]["anomaly_score"] == 0.91
    assert "behavior session looks anomalous" in data["reasons"][0].lower()


@pytest.mark.django_db
def test_phishing_deny_overrides_behavior() -> None:
    client = APIClient()
    user = _user()
    session = BehaviorSession.objects.create(user=user, context={})
    client.force_authenticate(user=user)
    phishing_service = Mock()
    phishing_service.check_url.return_value = _phishing_prediction("phishing", 0.95)

    with patch(
        "apps.transactions.services.get_phishing_check_service",
        return_value=phishing_service,
    ), patch(
        "apps.transactions.services.BehaviorFeatureExtractor.extract",
        return_value=BehaviorFeatures(keystroke_count=10),
    ), patch(
        "apps.transactions.services.BehaviorAnomalyDetector.predict",
        return_value=BehaviorAnomalyResult(
            anomaly_score=0.0,
            is_anomaly=False,
            decision="legitimate",
        ),
    ):
        response = client.post(
            _url(),
            _payload(
                behavior_session_id=str(session.id),
                target_url="https://example.com/payment",
            ),
            format="json",
        )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "DENY"
    assert data["phishing"]["decision"] == "phishing"
    assert data["behavior"]["decision"] == "legitimate"
    assert "phishing" in data["reasons"][0].lower()


@pytest.mark.django_db
def test_high_amount_with_suspicious_behavior_maps_to_challenge() -> None:
    client = APIClient()
    user = _user()
    session = BehaviorSession.objects.create(user=user, context={})
    client.force_authenticate(user=user)

    response = client.post(
        _url(),
        _payload(amount="1000.00", behavior_session_id=str(session.id)),
        format="json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "CHALLENGE"
    assert data["behavior"]["decision"] == "suspicious"
    assert "high-value transaction" in data["reasons"][0].lower()


@pytest.mark.django_db
def test_response_includes_behavior_block() -> None:
    client = APIClient()
    user = _user()
    client.force_authenticate(user=user)

    response = client.post(_url(), _payload(), format="json")

    assert response.status_code == 201
    data = response.json()
    assert data["behavior"] == {
        "available": False,
        "decision": "not_available",
        "anomaly_score": None,
        "features": {},
    }


@pytest.mark.django_db
def test_behavior_extraction_failure_handled_safely() -> None:
    client = APIClient()
    user = _user()
    session = BehaviorSession.objects.create(user=user, context={})
    client.force_authenticate(user=user)

    with patch(
        "apps.transactions.services.BehaviorFeatureExtractor.extract",
        side_effect=RuntimeError("feature extraction failed"),
    ):
        response = client.post(
            _url(),
            _payload(behavior_session_id=str(session.id)),
            format="json",
        )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "CHALLENGE"
    assert data["behavior"]["available"] is False
    assert data["behavior"]["decision"] == "suspicious"
    assert "behavior analysis was unavailable" in data["reasons"][0].lower()
