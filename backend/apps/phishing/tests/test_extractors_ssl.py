from __future__ import annotations

import socket
import ssl
from unittest.mock import MagicMock, patch

import pytest

from apps.phishing.extractors.ssl_ext import SslExtractor

_CREATE_CONN = "apps.phishing.extractors.ssl_ext.socket.create_connection"
_CREATE_CTX = "apps.phishing.extractors.ssl_ext.ssl.create_default_context"


@pytest.fixture
def ext() -> SslExtractor:
    return SslExtractor()


_UNSET = object()  # sentinel: "caller did not pass cert"


def _make_ssl_mocks(cert=_UNSET):
    """Return (mock_conn, mock_ctx) configured for a successful TLS handshake.

    mock_conn  — replaces socket.create_connection (context manager)
    mock_ctx   — replaces ssl.create_default_context

    Pass cert=None to simulate getpeercert() returning None.
    Omit cert (or use _UNSET) to get a default non-empty certificate dict.
    """
    if cert is _UNSET:
        cert = {"subject": ((("commonName", "example.com"),),)}

    mock_raw_sock = MagicMock()

    mock_conn = MagicMock()
    mock_conn.return_value.__enter__.return_value = mock_raw_sock
    mock_conn.return_value.__exit__.return_value = False

    mock_ssock = MagicMock()
    mock_ssock.getpeercert.return_value = cert

    mock_wrapped = MagicMock()
    mock_wrapped.__enter__.return_value = mock_ssock
    mock_wrapped.__exit__.return_value = False

    mock_ctx = MagicMock()
    mock_ctx.return_value.wrap_socket.return_value = mock_wrapped

    return mock_conn, mock_ctx


# ── feature_names contract ────────────────────────────────────────────────────

def test_feature_names_contract(ext):
    assert ext.feature_names == ["sslfinal_state"]


# ── http scheme → -1 (no socket call) ────────────────────────────────────────

@patch(_CREATE_CONN)
def test_http_scheme_returns_minus_one(mock_conn, ext):
    result = ext.extract("http://example.com/", {})
    assert result["sslfinal_state"] == -1
    mock_conn.assert_not_called()


@patch(_CREATE_CONN)
def test_http_scheme_with_path_returns_minus_one(mock_conn, ext):
    result = ext.extract("http://example.com/login?user=x", {})
    assert result["sslfinal_state"] == -1
    mock_conn.assert_not_called()


# ── missing hostname → -1 ────────────────────────────────────────────────────

@patch(_CREATE_CONN)
def test_empty_hostname_returns_minus_one(mock_conn, ext):
    result = ext.extract("https://", {})
    assert result["sslfinal_state"] == -1
    mock_conn.assert_not_called()


# ── successful TLS handshake → +1 ────────────────────────────────────────────

def test_https_trusted_cert_returns_plus_one(ext):
    mock_conn, mock_ctx = _make_ssl_mocks()
    with patch(_CREATE_CONN, mock_conn), patch(_CREATE_CTX, mock_ctx):
        result = ext.extract("https://example.com/", {})
    assert result["sslfinal_state"] == 1


def test_https_trusted_cert_uses_parsed_context(ext):
    """parsed_context['parsed_url'] must be reused instead of re-parsing."""
    from urllib.parse import urlparse
    mock_conn, mock_ctx = _make_ssl_mocks()
    ctx = {"parsed_url": urlparse("https://context-host.example.com/")}
    with patch(_CREATE_CONN, mock_conn), patch(_CREATE_CTX, mock_ctx):
        ext.extract("https://ignored-url.com/", ctx)
    # socket.create_connection must have been called with the context hostname
    call_args = mock_conn.call_args[0][0]  # first positional arg: (host, port)
    assert call_args[0] == "context-host.example.com"


# ── non-standard port is forwarded ───────────────────────────────────────────

def test_non_standard_https_port(ext):
    mock_conn, mock_ctx = _make_ssl_mocks()
    with patch(_CREATE_CONN, mock_conn), patch(_CREATE_CTX, mock_ctx):
        ext.extract("https://example.com:8443/", {})
    host, port = mock_conn.call_args[0][0]
    assert port == 8443


def test_default_https_port_443_used_when_absent(ext):
    mock_conn, mock_ctx = _make_ssl_mocks()
    with patch(_CREATE_CONN, mock_conn), patch(_CREATE_CTX, mock_ctx):
        ext.extract("https://example.com/", {})
    host, port = mock_conn.call_args[0][0]
    assert port == 443


# ── cert failures → -1 ───────────────────────────────────────────────────────

def test_https_untrusted_cert_returns_minus_one(ext):
    mock_conn, mock_ctx = _make_ssl_mocks()
    mock_ctx.return_value.wrap_socket.side_effect = ssl.SSLCertVerificationError(
        1, "certificate verify failed"
    )
    with patch(_CREATE_CONN, mock_conn), patch(_CREATE_CTX, mock_ctx):
        result = ext.extract("https://self-signed.example.com/", {})
    assert result["sslfinal_state"] == -1


def test_https_ssl_error_returns_minus_one(ext):
    mock_conn, mock_ctx = _make_ssl_mocks()
    mock_ctx.return_value.wrap_socket.side_effect = ssl.SSLError("generic ssl error")
    with patch(_CREATE_CONN, mock_conn), patch(_CREATE_CTX, mock_ctx):
        result = ext.extract("https://bad-tls.example.com/", {})
    assert result["sslfinal_state"] == -1


def test_getpeercert_none_returns_minus_one(ext):
    mock_conn, mock_ctx = _make_ssl_mocks(cert=None)
    with patch(_CREATE_CONN, mock_conn), patch(_CREATE_CTX, mock_ctx):
        result = ext.extract("https://example.com/", {})
    assert result["sslfinal_state"] == -1


def test_getpeercert_empty_dict_returns_minus_one(ext):
    mock_conn, mock_ctx = _make_ssl_mocks(cert={})
    with patch(_CREATE_CONN, mock_conn), patch(_CREATE_CTX, mock_ctx):
        result = ext.extract("https://example.com/", {})
    assert result["sslfinal_state"] == -1


# ── connection errors → -1 ───────────────────────────────────────────────────

@patch(_CREATE_CTX)
@patch(_CREATE_CONN, side_effect=socket.timeout())
def test_connection_timeout_returns_minus_one(mock_conn, mock_ctx, ext):
    result = ext.extract("https://slow.example.com/", {})
    assert result["sslfinal_state"] == -1


@patch(_CREATE_CTX)
@patch(_CREATE_CONN, side_effect=ConnectionRefusedError())
def test_connection_refused_returns_minus_one(mock_conn, mock_ctx, ext):
    result = ext.extract("https://closed.example.com/", {})
    assert result["sslfinal_state"] == -1


@patch(_CREATE_CTX)
@patch(_CREATE_CONN, side_effect=socket.gaierror("Name or service not known"))
def test_gaierror_returns_minus_one(mock_conn, mock_ctx, ext):
    result = ext.extract("https://nonexistent.example.com/", {})
    assert result["sslfinal_state"] == -1


# ── unexpected exception → 0 ─────────────────────────────────────────────────

@patch(_CREATE_CTX)
@patch(_CREATE_CONN, side_effect=RuntimeError("unexpected"))
def test_unexpected_exception_returns_zero(mock_conn, mock_ctx, ext):
    result = ext.extract("https://example.com/", {})
    assert result["sslfinal_state"] == 0
