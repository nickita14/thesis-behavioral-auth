from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from unittest.mock import Mock

import pytest
from django.core.cache import cache as django_cache

from apps.phishing.cache import FeatureCache
from apps.phishing.detectors import (
    DECISION_LEGITIMATE,
    DECISION_PHISHING,
    DECISION_SUSPICIOUS,
    XGBoostPhishingDetector,
)
from apps.phishing.extractors.base import URLFeatures


class FakeModel:
    def __init__(self, proba: list[list[float]], classes=None) -> None:
        self.proba = proba
        self.predict_inputs: list[list[list[int]]] = []
        if classes is not None:
            self.classes_ = classes

    def predict_proba(self, matrix: list[list[int]]) -> list[list[float]]:
        self.predict_inputs.append(matrix)
        return self.proba


class FakeCache:
    def __init__(self, cached: URLFeatures | None = None) -> None:
        self.cached = cached
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, URLFeatures]] = []

    def get(self, url: str) -> URLFeatures | None:
        self.get_calls.append(url)
        return self.cached

    def set(self, url: str, features: URLFeatures) -> None:
        self.set_calls.append((url, features))


class FakeExtractor:
    def __init__(self, features: URLFeatures) -> None:
        self.features = features
        self.calls: list[str] = []

    def extract(self, url: str) -> URLFeatures:
        self.calls.append(url)
        return self.features


def make_detector(
    model: FakeModel,
    cache: FakeCache | FeatureCache | None = None,
    extractor: FakeExtractor | None = None,
) -> XGBoostPhishingDetector:
    return XGBoostPhishingDetector(
        model_path=Path("/tmp/model.joblib"),
        threshold=0.8,
        feature_cache=cache or FakeCache(),
        feature_extractor=extractor or FakeExtractor(URLFeatures(url_length=1)),
        joblib_loader=Mock(return_value={"model": model}),
    )


def test_model_loaded_once():
    model = FakeModel([[0.9, 0.1]], classes=[0, 1])
    loader = Mock(return_value={"model": model})
    detector = XGBoostPhishingDetector(
        model_path=Path("/tmp/model.joblib"),
        feature_cache=FakeCache(),
        feature_extractor=FakeExtractor(URLFeatures(url_length=1)),
        joblib_loader=loader,
    )

    detector.predict("https://one.example")
    detector.predict("https://two.example")

    loader.assert_called_once_with(Path("/tmp/model.joblib"))


def test_cache_hit_skips_pipeline():
    cached = URLFeatures(having_ip_address=1)
    extractor = FakeExtractor(URLFeatures(url_length=-1))

    prediction = make_detector(
        FakeModel([[0.7, 0.3]], classes=[0, 1]),
        cache=FakeCache(cached=cached),
        extractor=extractor,
    ).predict("https://example.com")

    assert extractor.calls == []
    assert prediction.from_cache is True
    assert prediction.features == cached


def test_cache_miss_triggers_pipeline_then_cache_set():
    cache = FakeCache()
    extracted = URLFeatures(url_length=1)
    extractor = FakeExtractor(extracted)

    prediction = make_detector(
        FakeModel([[0.7, 0.3]], classes=[0, 1]),
        cache=cache,
        extractor=extractor,
    ).predict("https://example.com")

    assert extractor.calls == ["https://example.com"]
    assert cache.set_calls == [("https://example.com", extracted)]
    assert prediction.from_cache is False


def test_probability_phishing_uses_first_predict_proba_column():
    prediction = make_detector(
        FakeModel([[0.91, 0.09]], classes=[0, 1]),
    ).predict("https://example.com")

    assert prediction.probability_phishing == 0.91
    assert prediction.probability_legitimate == 0.09


def test_classes_validation_rejects_wrong_order():
    with pytest.raises(ValueError, match=r"classes_ must be \[0, 1\]"):
        make_detector(FakeModel([[0.5, 0.5]], classes=[1, 0]))


@pytest.mark.parametrize(
    "probability,expected_decision",
    [
        (0.19, DECISION_LEGITIMATE),
        (0.50, DECISION_SUSPICIOUS),
        (0.80, DECISION_PHISHING),
    ],
)
def test_threshold_semantics(probability, expected_decision):
    prediction = make_detector(
        FakeModel([[probability, 1 - probability]], classes=[0, 1]),
    ).predict("https://example.com")

    assert prediction.decision == expected_decision


def test_feature_vector_order_matches_urlfeatures_dataclass_order():
    values = {
        field.name: index
        for index, field in enumerate(fields(URLFeatures), start=1)
    }
    features = URLFeatures(**values)
    model = FakeModel([[0.9, 0.1]], classes=[0, 1])

    make_detector(
        model,
        extractor=FakeExtractor(features),
    ).predict("https://example.com")

    assert model.predict_inputs[0][0] == list(values.values())


def test_detector_survives_malformed_cache_entry_by_recomputing():
    django_cache.clear()
    feature_cache = FeatureCache()
    django_cache.set(feature_cache.make_key("https://example.com"), "{bad-json")
    extracted = URLFeatures(url_length=1)
    extractor = FakeExtractor(extracted)

    prediction = make_detector(
        FakeModel([[0.9, 0.1]], classes=[0, 1]),
        cache=feature_cache,
        extractor=extractor,
    ).predict("https://example.com")

    assert extractor.calls == ["https://example.com"]
    assert prediction.features == extracted
    assert prediction.from_cache is False


def test_detector_returns_features_in_response():
    features = URLFeatures(having_at_symbol=-1)

    prediction = make_detector(
        FakeModel([[0.9, 0.1]], classes=[0, 1]),
        extractor=FakeExtractor(features),
    ).predict("https://example.com")

    assert prediction.features == features
