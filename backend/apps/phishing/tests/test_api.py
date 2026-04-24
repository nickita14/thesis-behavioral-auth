from __future__ import annotations

from unittest.mock import Mock, patch

from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.phishing.detectors import PhishingPrediction
from apps.phishing.extractors.base import URLFeatures
from apps.phishing.services import PhishingCheckService, get_phishing_check_service


def _url() -> str:
    return reverse("phishing:check")


def _prediction(
    from_cache: bool = False,
    decision: str = "phishing",
    features: URLFeatures | None = None,
) -> PhishingPrediction:
    return PhishingPrediction(
        url="https://example.com/login",
        probability_phishing=0.91,
        probability_legitimate=0.09,
        decision=decision,
        features=features or URLFeatures(url_length=1, sslfinal_state=1),
        from_cache=from_cache,
    )


class FakeService:
    def __init__(self, prediction: PhishingPrediction | None = None) -> None:
        self.prediction = prediction or _prediction()
        self.calls: list[str] = []

    def check_url(self, url: str) -> PhishingPrediction:
        self.calls.append(url)
        return self.prediction


def test_valid_url_returns_200_and_structured_response() -> None:
    service = FakeService(_prediction(decision="phishing"))

    with patch("apps.phishing.views.get_phishing_check_service", return_value=service):
        response = APIClient().post(
            _url(),
            {"url": "https://example.com/login"},
            format="json",
        )

    assert response.status_code == 200
    assert service.calls == ["https://example.com/login"]
    data = response.json()
    assert data["url"] == "https://example.com/login"
    assert data["probability_phishing"] == 0.91
    assert data["probability_legitimate"] == 0.09
    assert data["decision"] == "phishing"
    assert data["from_cache"] is False
    assert isinstance(data["features"], dict)


def test_invalid_url_returns_400() -> None:
    response = APIClient().post(_url(), {"url": "not-a-url"}, format="json")

    assert response.status_code == 400
    assert "url" in response.json()


def test_cache_hit_path() -> None:
    service = FakeService(_prediction(from_cache=True, decision="legitimate"))

    with patch("apps.phishing.views.get_phishing_check_service", return_value=service):
        response = APIClient().post(
            _url(),
            {"url": "https://example.com/login"},
            format="json",
        )

    assert response.status_code == 200
    assert response.json()["from_cache"] is True


def test_cache_miss_path() -> None:
    service = FakeService(_prediction(from_cache=False, decision="suspicious"))

    with patch("apps.phishing.views.get_phishing_check_service", return_value=service):
        response = APIClient().post(
            _url(),
            {"url": "https://example.com/login"},
            format="json",
        )

    assert response.status_code == 200
    assert response.json()["from_cache"] is False
    assert response.json()["decision"] == "suspicious"


def test_detector_exception_handled_gracefully() -> None:
    service = Mock()
    service.check_url.side_effect = RuntimeError("model unavailable")

    with patch("apps.phishing.views.get_phishing_check_service", return_value=service):
        response = APIClient().post(
            _url(),
            {"url": "https://example.com/login"},
            format="json",
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Phishing detector is temporarily unavailable"
    }


def test_response_includes_features() -> None:
    features = URLFeatures(having_ip_address=-1, url_length=1)
    service = FakeService(_prediction(features=features))

    with patch("apps.phishing.views.get_phishing_check_service", return_value=service):
        response = APIClient().post(
            _url(),
            {"url": "https://example.com/login"},
            format="json",
        )

    assert response.status_code == 200
    assert response.json()["features"]["having_ip_address"] == -1
    assert response.json()["features"]["url_length"] == 1


def test_endpoint_wired_in_urls_correctly() -> None:
    service = FakeService(_prediction())

    with patch("apps.phishing.views.get_phishing_check_service", return_value=service):
        response = APIClient().post(
            reverse("phishing:check"),
            {"url": "https://example.com/login"},
            format="json",
        )

    assert response.status_code == 200


def test_service_persists_phishing_event_without_schema_changes() -> None:
    detector = Mock()
    detector.predict.return_value = _prediction(
        decision="phishing",
        features=URLFeatures(url_length=1, web_traffic=-1),
    )
    service = PhishingCheckService(detector=detector)

    with patch("apps.phishing.services.PhishingEvent.objects.create") as create:
        prediction = service.check_url("https://example.com/login")

    create.assert_called_once_with(
        url=prediction.url,
        url_features={
            **{name: 0 for name in URLFeatures.__dataclass_fields__},
            "url_length": 1,
            "web_traffic": -1,
        },
        is_phishing_predicted=True,
        confidence=0.91,
    )


def test_default_service_uses_settings_model_path() -> None:
    get_phishing_check_service.cache_clear()
    configured_path = "/tmp/custom-phishing-model.joblib"

    with override_settings(PHISHING_MODEL_PATH=configured_path):
        with patch("apps.phishing.services.XGBoostPhishingDetector") as detector_cls:
            detector_cls.return_value = Mock()
            service = get_phishing_check_service()

    detector_cls.assert_called_once_with(model_path=configured_path)
    assert isinstance(service, PhishingCheckService)
    get_phishing_check_service.cache_clear()
