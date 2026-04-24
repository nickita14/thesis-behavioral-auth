from __future__ import annotations

import logging
import socket
import ssl
from urllib.parse import urlparse

from .base import BaseFeatureExtractor

logger = logging.getLogger(__name__)

SSL_TIMEOUT_SECONDS = 3.0
DEFAULT_HTTPS_PORT = 443


class SslExtractor(BaseFeatureExtractor):
    """Extract sslfinal_state: whether the URL has a valid, trusted TLS cert.

    NOTE: Original UCI rule required certificate age >= 1 year. This is
    invalid for modern certificates (Let's Encrypt issues 90-day certs that
    legitimate sites rotate regularly). We use trusted handshake alone as
    legitimacy signal. See thesis Section 3.4 for discussion.
    """

    @property
    def feature_names(self) -> list[str]:
        return ["sslfinal_state"]

    def extract(self, url: str, parsed_context: dict) -> dict[str, int]:
        try:
            parsed = parsed_context.get("parsed_url") or urlparse(url)
        except Exception:
            return {"sslfinal_state": 0}

        scheme = (parsed.scheme or "").lower()

        if scheme != "https":
            return {"sslfinal_state": -1}

        hostname = parsed.hostname
        if not hostname:
            return {"sslfinal_state": -1}

        port = parsed.port or DEFAULT_HTTPS_PORT

        try:
            return {"sslfinal_state": 1 if self._verify_ssl(hostname, port) else -1}
        except Exception as exc:
            logger.warning("Unexpected SSL error for %s: %s", hostname, exc)
            return {"sslfinal_state": 0}

    def _verify_ssl(self, hostname: str, port: int) -> bool:
        """Return True if TLS handshake succeeds with a trusted certificate.

        ssl.create_default_context() already sets CERT_REQUIRED and
        check_hostname=True, so any validation failure raises an exception
        rather than returning silently.
        """
        context = ssl.create_default_context()
        try:
            with socket.create_connection((hostname, port), timeout=SSL_TIMEOUT_SECONDS) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    return cert is not None and len(cert) > 0
        except ssl.SSLCertVerificationError:
            logger.debug("SSL cert verification failed for %s", hostname)
            return False
        except ssl.SSLError:
            logger.debug("SSL handshake error for %s", hostname)
            return False
        except (socket.timeout, socket.gaierror, ConnectionRefusedError,
                ConnectionResetError, OSError):
            logger.debug("Connection error for %s:%s", hostname, port)
            return False
