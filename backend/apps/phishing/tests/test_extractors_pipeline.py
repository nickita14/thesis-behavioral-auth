from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from apps.phishing.extractors.base import BaseFeatureExtractor, URLFeatures
from apps.phishing.extractors.pipeline import URLFeatureExtractor


class StubExtractor(BaseFeatureExtractor):
    def __init__(
        self,
        feature_names: list[str],
        result: dict[str, int] | None = None,
        delay_seconds: float = 0,
        should_fail: bool = False,
    ) -> None:
        self._feature_names = feature_names
        self.result = result or {}
        self.delay_seconds = delay_seconds
        self.should_fail = should_fail
        self.calls: list[tuple[str, dict]] = []

    @property
    def feature_names(self) -> list[str]:
        return self._feature_names

    def extract(self, url: str, parsed_context: dict) -> dict[str, int]:
        self.calls.append((url, parsed_context))
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        if self.should_fail:
            raise RuntimeError("extractor failed")
        parsed_context.setdefault("seen_by", []).append(self.__class__.__name__)
        return self.result


def test_happy_path_all_extractors_successful():
    lexical = StubExtractor(
        ["having_ip_address"],
        {"having_ip_address": 1, "url_length": 1},
    )
    whois = StubExtractor(["dnsrecord"], {"dnsrecord": 1})
    ssl = StubExtractor(["sslfinal_state"], {"sslfinal_state": 1})
    html = StubExtractor(["iframe"], {"iframe": -1})
    external = StubExtractor(["web_traffic"], {"web_traffic": 1})

    features = URLFeatureExtractor(
        lexical_extractor=lexical,
        parallel_extractors=[whois, ssl, html, external],
    ).extract("https://example.com")

    assert features.having_ip_address == 1
    assert features.url_length == 1
    assert features.dnsrecord == 1
    assert features.sslfinal_state == 1
    assert features.iframe == -1
    assert features.web_traffic == 1


def test_lexical_failure_other_extractors_still_work():
    lexical = StubExtractor(["having_ip_address"], should_fail=True)
    ssl = StubExtractor(["sslfinal_state"], {"sslfinal_state": 1})

    features = URLFeatureExtractor(
        lexical_extractor=lexical,
        parallel_extractors=[ssl],
    ).extract("https://example.com")

    assert features.having_ip_address == 0
    assert features.sslfinal_state == 1


def test_whois_failure_does_not_break_other_extractors():
    lexical = StubExtractor(["url_length"], {"url_length": 1})
    whois = StubExtractor(["dnsrecord"], should_fail=True)
    ssl = StubExtractor(["sslfinal_state"], {"sslfinal_state": 1})

    features = URLFeatureExtractor(
        lexical_extractor=lexical,
        parallel_extractors=[whois, ssl],
    ).extract("https://example.com")

    assert features.url_length == 1
    assert features.dnsrecord == 0
    assert features.sslfinal_state == 1


def test_all_extractors_fail_returns_all_zero_features():
    features = URLFeatureExtractor(
        lexical_extractor=StubExtractor(["url_length"], should_fail=True),
        parallel_extractors=[
            StubExtractor(["dnsrecord"], should_fail=True),
            StubExtractor(["sslfinal_state"], should_fail=True),
        ],
    ).extract("https://example.com")

    assert all(value == 0 for value in asdict(features).values())


def test_timeout_one_extractor_leaves_its_features_zero():
    slow = StubExtractor(["dnsrecord"], {"dnsrecord": 1}, delay_seconds=0.05)
    fast = StubExtractor(["sslfinal_state"], {"sslfinal_state": 1})

    features = URLFeatureExtractor(
        lexical_extractor=StubExtractor(["url_length"], {"url_length": 1}),
        parallel_extractors=[slow, fast],
        timeout_seconds=0.01,
    ).extract("https://example.com")

    assert features.url_length == 1
    assert features.sslfinal_state == 1
    assert features.dnsrecord == 0


def test_unknown_keys_ignored():
    features = URLFeatureExtractor(
        lexical_extractor=StubExtractor(
            ["url_length"],
            {"url_length": 1, "unknown_feature": -1},
        ),
        parallel_extractors=[],
    ).extract("https://example.com")

    assert features.url_length == 1
    assert not hasattr(features, "unknown_feature")


def test_partial_results_on_timeout():
    quick_one = StubExtractor(["request_url"], {"request_url": 1})
    quick_two = StubExtractor(["web_traffic"], {"web_traffic": -1})
    slow = StubExtractor(["age_of_domain"], {"age_of_domain": 1}, delay_seconds=0.05)

    features = URLFeatureExtractor(
        lexical_extractor=StubExtractor(["having_at_symbol"], {"having_at_symbol": 1}),
        parallel_extractors=[quick_one, slow, quick_two],
        timeout_seconds=0.01,
    ).extract("https://example.com")

    assert features.having_at_symbol == 1
    assert features.request_url == 1
    assert features.web_traffic == -1
    assert features.age_of_domain == 0


def test_empty_url_graceful_degradation():
    features = URLFeatureExtractor(
        lexical_extractor=StubExtractor(["url_length"], {}),
        parallel_extractors=[StubExtractor(["dnsrecord"], should_fail=True)],
    ).extract("")

    assert isinstance(features, URLFeatures)
    assert all(value == 0 for value in asdict(features).values())


def test_tranco_file_passed_to_external():
    tranco_file = Path("/tmp/tranco.csv")

    with patch("apps.phishing.extractors.pipeline.ExternalExtractor") as external_cls:
        URLFeatureExtractor(tranco_file=tranco_file)

    external_cls.assert_called_once_with(tranco_file=tranco_file)
