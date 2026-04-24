from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache

from django.conf import settings

from .detectors import DECISION_PHISHING, PhishingPrediction, XGBoostPhishingDetector
from .models import PhishingEvent


class PhishingCheckService:
    """Application service for URL phishing checks and audit persistence."""

    def __init__(self, detector: XGBoostPhishingDetector) -> None:
        self.detector = detector

    def check_url(self, url: str) -> PhishingPrediction:
        prediction = self.detector.predict(url)
        self._persist(prediction)
        return prediction

    def _persist(self, prediction: PhishingPrediction) -> None:
        PhishingEvent.objects.create(
            url=prediction.url,
            url_features=asdict(prediction.features),
            is_phishing_predicted=prediction.decision == DECISION_PHISHING,
            confidence=max(
                prediction.probability_phishing,
                prediction.probability_legitimate,
            ),
        )


@lru_cache(maxsize=1)
def get_phishing_check_service() -> PhishingCheckService:
    """Build the default service lazily so imports do not load ML artifacts."""
    return PhishingCheckService(
        detector=XGBoostPhishingDetector(model_path=settings.PHISHING_MODEL_PATH)
    )
