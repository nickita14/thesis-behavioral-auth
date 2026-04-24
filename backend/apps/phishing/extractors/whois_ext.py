from __future__ import annotations

import logging
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import whois as whois_lib
from whois.parser import PywhoisError

from .base import BaseFeatureExtractor

logger = logging.getLogger(__name__)

WHOIS_TIMEOUT_SECONDS = 5.0
STANDARD_PORTS = {80, 443}
AGE_THRESHOLD_DAYS = 182          # ~6 months
REGISTRATION_THRESHOLD_DAYS = 365  # 1 year


class WhoisExtractor(BaseFeatureExtractor):
    """Extracts 5 features via WHOIS lookup and DNS check.

    DNS check (dnsrecord) and port are fast and independent.
    WHOIS is slow (up to WHOIS_TIMEOUT_SECONDS) and may fail; in that case
    age_of_domain, domain_registration_length, and abnormal_url default to 0.
    """

    _FEATURE_NAMES = [
        "age_of_domain",
        "domain_registration_length",
        "dnsrecord",
        "abnormal_url",
        "port",
    ]

    @property
    def feature_names(self) -> list[str]:
        return self._FEATURE_NAMES

    def extract(self, url: str, parsed_context: dict) -> dict[str, int]:
        features: dict[str, int] = {name: 0 for name in self._FEATURE_NAMES}

        domain = parsed_context.get("domain") or self._domain_from_url(url)
        if not domain:
            return features

        features["dnsrecord"] = self._check_dns(domain)
        features["port"] = self._check_port(url)

        whois_data = self._fetch_whois(domain)
        if whois_data is not None:
            features["age_of_domain"] = self._compute_age(whois_data)
            features["domain_registration_length"] = self._compute_reg_length(whois_data)
            features["abnormal_url"] = self._compute_abnormal_url(whois_data)

        return features

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _domain_from_url(url: str) -> str | None:
        try:
            return urlparse(url).hostname
        except Exception:
            return None

    def _check_dns(self, domain: str) -> int:
        try:
            socket.gethostbyname(domain)
            return 1
        except (socket.gaierror, socket.timeout, UnicodeError):
            return -1
        except Exception as exc:
            logger.warning("Unexpected DNS error for %s: %s", domain, exc)
            return 0

    @staticmethod
    def _check_port(url: str) -> int:
        # Architecturally this is a lexical feature. Extracted here for
        # convenience since WhoisExtractor has parsed URL access.
        try:
            port = urlparse(url).port  # None when not specified
            if port is None or port in STANDARD_PORTS:
                return 1
            return -1
        except (ValueError, Exception):
            return 0

    def _fetch_whois(self, domain: str):
        old = socket.getdefaulttimeout()
        socket.setdefaulttimeout(WHOIS_TIMEOUT_SECONDS)
        try:
            return whois_lib.whois(domain)
        except (PywhoisError, ConnectionError, socket.timeout, socket.gaierror) as exc:
            logger.info("WHOIS lookup failed for %s: %s", domain, exc)
            return None
        except Exception as exc:
            logger.warning("Unexpected WHOIS error for %s: %s", domain, exc)
            return None
        finally:
            socket.setdefaulttimeout(old)

    @staticmethod
    def _as_datetime(value) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, datetime):
            return value
        return None  # str or other unexpected types

    def _compute_age(self, whois_data) -> int:
        creation = self._as_datetime(getattr(whois_data, "creation_date", None))
        if creation is None:
            return 0
        if creation.tzinfo is None:
            creation = creation.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - creation).days
        return 1 if age_days > AGE_THRESHOLD_DAYS else -1

    def _compute_reg_length(self, whois_data) -> int:
        expiration = self._as_datetime(getattr(whois_data, "expiration_date", None))
        if expiration is None:
            return 0
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)
        remaining = (expiration - datetime.now(timezone.utc)).days
        return 1 if remaining > REGISTRATION_THRESHOLD_DAYS else -1

    def _compute_abnormal_url(self, whois_data) -> int:
        # Simplified implementation: original UCI feature compares URL host to
        # WHOIS registrant name, which is unreliable due to WHOIS privacy
        # services and shared hosting. This version checks WHOIS availability
        # as a proxy.
        creation = self._as_datetime(getattr(whois_data, "creation_date", None))
        return 1 if creation is not None else -1
