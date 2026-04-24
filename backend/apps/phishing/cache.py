from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from typing import Any

from django.core.cache import cache as django_cache

from .extractors.base import URLFeatures

logger = logging.getLogger(__name__)

CACHE_VERSION = "v1"
DEFAULT_TTL_SECONDS = 60 * 60
KEY_PREFIX = "phishing_features"


class FeatureCache:
    """Django-cache backed storage for serialized URLFeatures."""

    def __init__(
        self,
        cache_backend: Any | None = None,
        version: str = CACHE_VERSION,
    ) -> None:
        self.cache = cache_backend or django_cache
        self.version = version

    def get(self, url: str) -> URLFeatures | None:
        """Return cached URLFeatures or None on miss/corruption/cache errors."""
        key = self.make_key(url)
        try:
            payload = self.cache.get(key)
        except Exception as exc:
            logger.warning("Failed to read phishing feature cache key %s: %s", key, exc)
            return None

        if payload is None:
            return None

        try:
            return self._deserialize(payload)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Corrupted phishing feature cache key %s: %s", key, exc)
            return None

    def set(
        self,
        url: str,
        features: URLFeatures,
        ttl: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        """Serialize and store URLFeatures for url."""
        key = self.make_key(url)
        try:
            self.cache.set(key, self._serialize(features), timeout=ttl)
        except Exception as exc:
            logger.warning("Failed to write phishing feature cache key %s: %s", key, exc)

    def delete(self, url: str) -> None:
        """Delete cached URLFeatures for url."""
        key = self.make_key(url)
        try:
            self.cache.delete(key)
        except Exception as exc:
            logger.warning("Failed to delete phishing feature cache key %s: %s", key, exc)

    def make_key(self, url: str) -> str:
        normalized_url = self.normalize_url(url)
        digest = hashlib.md5(normalized_url.encode("utf-8")).hexdigest()
        return f"{KEY_PREFIX}:{self.version}:{digest}"

    @staticmethod
    def normalize_url(url: str) -> str:
        return url.strip().lower().rstrip("/")

    @staticmethod
    def _serialize(features: URLFeatures) -> str:
        return json.dumps(asdict(features), sort_keys=True)

    @staticmethod
    def _deserialize(payload: Any) -> URLFeatures:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        if not isinstance(payload, str):
            raise TypeError("cached payload must be a JSON string")

        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("cached payload must decode to an object")

        known_fields = {field.name for field in URLFeatures.__dataclass_fields__.values()}
        filtered = {name: value for name, value in data.items() if name in known_fields}
        return URLFeatures(**filtered)
