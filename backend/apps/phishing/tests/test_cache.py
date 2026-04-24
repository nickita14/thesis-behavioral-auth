from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from django.core.cache import cache

from apps.phishing.cache import FeatureCache
from apps.phishing.extractors.base import URLFeatures


@pytest.fixture(autouse=True)
def clear_django_cache():
    cache.clear()
    yield
    cache.clear()


def test_set_get_roundtrip():
    feature_cache = FeatureCache()
    features = URLFeatures(having_ip_address=1, sslfinal_state=-1)

    feature_cache.set("https://example.com/login", features)

    assert feature_cache.get("https://example.com/login") == features


def test_get_missing_returns_none():
    assert FeatureCache().get("https://missing.example") is None


def test_normalization_works():
    feature_cache = FeatureCache()
    features = URLFeatures(url_length=1)

    feature_cache.set(" HTTPS://Example.COM/Login/ ", features)

    assert feature_cache.get("https://example.com/login") == features


def test_delete_removes_entry():
    feature_cache = FeatureCache()
    url = "https://example.com"
    feature_cache.set(url, URLFeatures(web_traffic=1))

    feature_cache.delete(url)

    assert feature_cache.get(url) is None


def test_ttl_passed_to_cache_backend():
    backend = Mock()
    feature_cache = FeatureCache(cache_backend=backend)
    features = URLFeatures(url_length=1)

    feature_cache.set("https://example.com", features, ttl=123)

    backend.set.assert_called_once_with(
        feature_cache.make_key("https://example.com"),
        feature_cache._serialize(features),
        timeout=123,
    )


def test_corrupted_cache_entry_returns_none():
    feature_cache = FeatureCache()
    key = feature_cache.make_key("https://example.com")
    cache.set(key, "{not-valid-json")

    assert feature_cache.get("https://example.com") is None


def test_cache_exception_returns_none():
    backend = Mock()
    backend.get.side_effect = RuntimeError("cache unavailable")

    assert FeatureCache(cache_backend=backend).get("https://example.com") is None


def test_version_bump_invalidates_old_keys():
    old_cache = FeatureCache(version="v1")
    new_cache = FeatureCache(version="v2")
    old_cache.set("https://example.com", URLFeatures(url_length=1))

    assert new_cache.get("https://example.com") is None


def test_unknown_cached_keys_ignored():
    feature_cache = FeatureCache()
    key = feature_cache.make_key("https://example.com")
    cache.set(key, json.dumps({"url_length": 1, "unknown": -1}))

    assert feature_cache.get("https://example.com") == URLFeatures(url_length=1)
