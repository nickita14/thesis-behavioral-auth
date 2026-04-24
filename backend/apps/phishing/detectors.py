from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import joblib

from .cache import FeatureCache
from .extractors.base import URLFeatures
from .extractors.pipeline import URLFeatureExtractor

DECISION_LEGITIMATE = "legitimate"
DECISION_PHISHING = "phishing"
DECISION_SUSPICIOUS = "suspicious"
DEFAULT_THRESHOLD = 0.80


@dataclass(frozen=True)
class PhishingPrediction:
    """Prediction result returned by XGBoostPhishingDetector."""

    url: str
    probability_phishing: float
    probability_legitimate: float
    decision: str
    features: URLFeatures
    from_cache: bool


class XGBoostPhishingDetector:
    """Thin wrapper around a persisted phishing model artifact."""

    def __init__(
        self,
        model_path: str | Path,
        threshold: float = DEFAULT_THRESHOLD,
        feature_cache: FeatureCache | None = None,
        feature_extractor: URLFeatureExtractor | None = None,
        joblib_loader: Any = joblib.load,
    ) -> None:
        self.threshold = self._validate_threshold(threshold)
        self.feature_cache = feature_cache or FeatureCache()
        self.feature_extractor = feature_extractor or URLFeatureExtractor()
        self.feature_order = [field.name for field in fields(URLFeatures)]

        self.artifact = joblib_loader(model_path)
        self.model = self._extract_model(self.artifact)
        self._validate_classes()

    def predict(self, url: str) -> PhishingPrediction:
        """Predict phishing risk for URL using cached or freshly extracted features."""
        features, from_cache = self._get_features(url)
        probability_phishing, probability_legitimate = self._predict_probabilities(features)
        decision = self._decision(probability_phishing)

        return PhishingPrediction(
            url=url,
            probability_phishing=probability_phishing,
            probability_legitimate=probability_legitimate,
            decision=decision,
            features=features,
            from_cache=from_cache,
        )

    def _get_features(self, url: str) -> tuple[URLFeatures, bool]:
        cached = self.feature_cache.get(url)
        if cached is not None:
            return cached, True

        features = self.feature_extractor.extract(url)
        self.feature_cache.set(url, features)
        return features, False

    def _predict_probabilities(self, features: URLFeatures) -> tuple[float, float]:
        vector = features.to_vector(self.feature_order)
        proba = self.model.predict_proba([vector])
        row = proba[0]
        return float(row[0]), float(row[1])

    def _decision(self, probability_phishing: float) -> str:
        if probability_phishing < (1 - self.threshold):
            return DECISION_LEGITIMATE
        if probability_phishing >= self.threshold:
            return DECISION_PHISHING
        return DECISION_SUSPICIOUS

    def _validate_classes(self) -> None:
        classes = getattr(self.model, "classes_", None)
        if classes is not None and list(classes) != [0, 1]:
            raise ValueError("Phishing model classes_ must be [0, 1]")

    @staticmethod
    def _extract_model(artifact: Any) -> Any:
        if isinstance(artifact, dict):
            try:
                return artifact["model"]
            except KeyError as exc:
                raise ValueError("Model artifact dictionary must contain 'model'") from exc
        return artifact

    @staticmethod
    def _validate_threshold(threshold: float) -> float:
        if threshold <= 0.5 or threshold > 1:
            raise ValueError("threshold must be > 0.5 and <= 1.0")
        return threshold
