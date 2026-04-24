from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from apps.phishing.extractors.whois_ext import WhoisExtractor

# Patch targets — always patch where the name is used, not where it's defined
_WHOIS = "apps.phishing.extractors.whois_ext.whois_lib.whois"
_GETHOSTBYNAME = "apps.phishing.extractors.whois_ext.socket.gethostbyname"
_SETDEFAULTTIMEOUT = "apps.phishing.extractors.whois_ext.socket.setdefaulttimeout"
_GETDEFAULTTIMEOUT = "apps.phishing.extractors.whois_ext.socket.getdefaulttimeout"

_NOW = datetime.now(timezone.utc)


@pytest.fixture
def ext() -> WhoisExtractor:
    return WhoisExtractor()


def _whois_mock(creation_date=None, expiration_date=None) -> MagicMock:
    m = MagicMock()
    m.creation_date = creation_date
    m.expiration_date = expiration_date
    return m


def _patch_socket():
    """Return a stack of socket patches that disables network side-effects."""
    return [
        patch(_SETDEFAULTTIMEOUT),
        patch(_GETDEFAULTTIMEOUT, return_value=None),
    ]


# ── feature_names contract ────────────────────────────────────────────────────

def test_feature_names_contract(ext):
    assert ext.feature_names == [
        "age_of_domain",
        "domain_registration_length",
        "dnsrecord",
        "abnormal_url",
        "port",
    ]


def test_extract_returns_all_feature_keys(ext):
    with patch(_WHOIS, return_value=None), \
         patch(_GETHOSTBYNAME, return_value="1.2.3.4"), \
         patch(_SETDEFAULTTIMEOUT), patch(_GETDEFAULTTIMEOUT, return_value=None):
        result = ext.extract("http://example.com", {"domain": "example.com"})
    assert set(result.keys()) == set(ext.feature_names)


# ── age_of_domain ─────────────────────────────────────────────────────────────

@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_age_old_domain(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(
        creation_date=datetime(2010, 1, 1, tzinfo=timezone.utc),
        expiration_date=_NOW + timedelta(days=400),
    )
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["age_of_domain"] == 1


@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_age_young_domain(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(
        creation_date=_NOW - timedelta(days=10),
        expiration_date=_NOW + timedelta(days=400),
    )
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["age_of_domain"] == -1


@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_age_creation_date_none(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(creation_date=None)
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["age_of_domain"] == 0


@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_age_creation_date_as_list(_, __, ___, mock_whois, ext):
    """_as_datetime must unwrap a list[datetime] returned by some registrars."""
    mock_whois.return_value = _whois_mock(
        creation_date=[datetime(2010, 6, 1, tzinfo=timezone.utc)],
        expiration_date=_NOW + timedelta(days=400),
    )
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["age_of_domain"] == 1


@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_age_creation_date_as_string(_, __, ___, mock_whois, ext):
    """String dates (parse failures in python-whois) must return 0."""
    mock_whois.return_value = _whois_mock(creation_date="2010-01-01")
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["age_of_domain"] == 0


# ── domain_registration_length ────────────────────────────────────────────────

@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_reg_length_long(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(
        creation_date=datetime(2015, 1, 1, tzinfo=timezone.utc),
        expiration_date=_NOW + timedelta(days=400),
    )
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["domain_registration_length"] == 1


@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_reg_length_short(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(
        creation_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        expiration_date=_NOW + timedelta(days=30),
    )
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["domain_registration_length"] == -1


@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_reg_length_expiration_none(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(
        creation_date=datetime(2010, 1, 1, tzinfo=timezone.utc),
        expiration_date=None,
    )
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["domain_registration_length"] == 0


# ── dnsrecord ─────────────────────────────────────────────────────────────────

@patch(_WHOIS, return_value=None)
@patch(_GETHOSTBYNAME, return_value="142.250.80.46")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_dnsrecord_resolves(_, __, mock_dns, ___, ext):
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["dnsrecord"] == 1
    mock_dns.assert_called_once_with("example.com")


@patch(_WHOIS, return_value=None)
@patch(_GETHOSTBYNAME, side_effect=socket.gaierror("Name not found"))
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_dnsrecord_gaierror(_, __, mock_dns, ___, ext):
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["dnsrecord"] == -1


@patch(_WHOIS, return_value=None)
@patch(_GETHOSTBYNAME, side_effect=socket.timeout())
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_dnsrecord_timeout(_, __, ___, ____, ext):
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["dnsrecord"] == -1


@patch(_WHOIS, return_value=None)
@patch(_GETHOSTBYNAME, side_effect=UnicodeError("invalid label"))
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_dnsrecord_unicode_error(_, __, ___, ____, ext):
    r = ext.extract("http://xn--bad\udce2.com", {"domain": "xn--bad\udce2.com"})
    assert r["dnsrecord"] == -1


# ── port ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("http://example.com/path", 1),         # no port → standard
    ("http://example.com:80/path", 1),      # explicit 80 → standard
    ("https://example.com:443/path", 1),    # explicit 443 → standard
    ("http://example.com:8080/path", -1),   # non-standard
    ("http://example.com:22/ssh", -1),      # non-standard
])
@patch(_WHOIS, return_value=None)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_port(_, __, ___, ____, url, expected, ext):
    r = ext.extract(url, {"domain": "example.com"})
    assert r["port"] == expected


# ── abnormal_url ──────────────────────────────────────────────────────────────

@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_abnormal_url_whois_available(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(
        creation_date=datetime(2015, 1, 1, tzinfo=timezone.utc),
    )
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["abnormal_url"] == 1


@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_abnormal_url_no_creation_date(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(creation_date=None)
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["abnormal_url"] == -1


# ── graceful degradation ──────────────────────────────────────────────────────

@patch(_WHOIS, side_effect=Exception("network error"))
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_whois_exception_whois_features_zero(_, __, ___, ____, ext):
    """WHOIS failure must not affect dnsrecord and port."""
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["age_of_domain"] == 0
    assert r["domain_registration_length"] == 0
    assert r["abnormal_url"] == 0
    assert r["dnsrecord"] == 1   # DNS worked
    assert r["port"] == 1        # port worked


@patch(_WHOIS, return_value=None)
@patch(_GETHOSTBYNAME, side_effect=socket.gaierror())
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_dns_failure_does_not_break_other_features(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(
        creation_date=datetime(2010, 1, 1, tzinfo=timezone.utc),
        expiration_date=_NOW + timedelta(days=400),
    )
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["dnsrecord"] == -1
    assert r["age_of_domain"] == 1   # still computed from WHOIS


# ── parsed_context integration ────────────────────────────────────────────────

@patch(_WHOIS, return_value=None)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_uses_domain_from_parsed_context(_, __, mock_dns, ___, ext):
    """domain must be read from parsed_context, not re-extracted from URL."""
    ctx = {"domain": "contextdomain.com"}
    ext.extract("http://different-url.com", ctx)
    mock_dns.assert_called_once_with("contextdomain.com")


@patch(_WHOIS, return_value=None)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_fallback_domain_from_url_when_context_empty(_, __, mock_dns, ___, ext):
    """When parsed_context has no domain key, fall back to URL hostname."""
    ext.extract("http://fallback.example.com/path", {})
    mock_dns.assert_called_once_with("fallback.example.com")


# ── naive datetime handling ───────────────────────────────────────────────────

@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="1.2.3.4")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_naive_creation_date_handled(_, __, ___, mock_whois, ext):
    """Naive datetime (no tzinfo) from WHOIS must not raise."""
    mock_whois.return_value = _whois_mock(
        creation_date=datetime(2010, 1, 1),          # naive
        expiration_date=datetime(2030, 1, 1),        # naive
    )
    r = ext.extract("http://example.com", {"domain": "example.com"})
    assert r["age_of_domain"] == 1
    assert r["domain_registration_length"] == 1


# ── full happy path ───────────────────────────────────────────────────────────

@patch(_WHOIS)
@patch(_GETHOSTBYNAME, return_value="142.250.80.46")
@patch(_SETDEFAULTTIMEOUT)
@patch(_GETDEFAULTTIMEOUT, return_value=None)
def test_all_legitimate_signals(_, __, ___, mock_whois, ext):
    mock_whois.return_value = _whois_mock(
        creation_date=datetime(2010, 1, 1, tzinfo=timezone.utc),
        expiration_date=_NOW + timedelta(days=400),
    )
    r = ext.extract("https://www.google.com", {"domain": "google.com"})
    assert r == {
        "age_of_domain": 1,
        "domain_registration_length": 1,
        "dnsrecord": 1,
        "abnormal_url": 1,
        "port": 1,
    }
