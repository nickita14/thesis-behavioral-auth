from __future__ import annotations

import pytest

from apps.phishing.extractors.lexical import LexicalExtractor


@pytest.fixture
def extractor() -> LexicalExtractor:
    return LexicalExtractor()


# ── having_ip_address ────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("http://125.98.3.123/fake.html", -1),        # IPv4 in host
    ("http://www.google.com/", 1),                # domain
    ("https://[2001:db8::1]/login", -1),          # IPv6 in brackets
    ("https://secure-bank.com/auth", 1),          # no IP
])
def test_having_ip_address(extractor, url, expected):
    result = extractor.extract(url, {})
    assert result["having_ip_address"] == expected


# ── url_length ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("http://go.co/x", 1),                        # 15 chars → short (< 54)
    ("http://www.example-site.com/some/moderate/path/extra/seg", 0),  # 56 chars → 54–75
    ("http://www.phishing-lookalike-secure-paypal-account.com/login/verify/now/xyz", -1),  # 76 chars → > 75
])
def test_url_length(extractor, url, expected):
    result = extractor.extract(url, {})
    assert result["url_length"] == expected


# ── shortining_service ───────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("http://bit.ly/3xYzAbc", -1),                # known shortener
    ("http://tinyurl.com/abc123", -1),            # known shortener
    ("https://www.wikipedia.org/wiki/Python", 1), # legitimate domain
])
def test_shortining_service(extractor, url, expected):
    result = extractor.extract(url, {})
    assert result["shortining_service"] == expected


# ── having_at_symbol ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("http://www.legitimate.com@evil.com/", -1),  # @ in URL
    ("https://www.google.com/search?q=hello", 1), # no @
])
def test_having_at_symbol(extractor, url, expected):
    result = extractor.extract(url, {})
    assert result["having_at_symbol"] == expected


# ── double_slash_redirecting ─────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("http://www.evil.com//redirect?url=http://bank.com", -1),  # extra //
    ("https://www.google.com/search", 1),                        # normal
])
def test_double_slash_redirecting(extractor, url, expected):
    result = extractor.extract(url, {})
    assert result["double_slash_redirecting"] == expected


# ── prefix_suffix ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("http://www.pay-pal-secure.com/", -1),       # hyphen in domain
    ("https://www.paypal.com/", 1),               # no hyphen
])
def test_prefix_suffix(extractor, url, expected):
    result = extractor.extract(url, {})
    assert result["prefix_suffix"] == expected


# ── having_sub_domain ────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("https://google.com/", 1),                           # no subdomain
    ("https://www.google.com/", 0),                       # one subdomain (www)
    ("https://mail.accounts.google.com/", -1),            # two subdomains
])
def test_having_sub_domain(extractor, url, expected):
    result = extractor.extract(url, {})
    assert result["having_sub_domain"] == expected


# ── https_token ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("http://https-secure-paypal.com/login", -1),  # 'https' in domain name
    ("https://www.paypal.com/login", 1),            # 'https' only in scheme
    ("http://bank-secure.com/", 1),                 # no 'https' in domain
])
def test_https_token(extractor, url, expected):
    result = extractor.extract(url, {})
    assert result["https_token"] == expected


# ── parsed_context population ────────────────────────────────────────────────

def test_populates_parsed_context(extractor):
    ctx: dict = {}
    extractor.extract("https://sub.example.com/path?q=1", ctx)
    assert "parsed_url" in ctx
    assert "tld_extract" in ctx
    assert ctx["domain"] == "example.com"


# ── feature_names contract ───────────────────────────────────────────────────

def test_feature_names_count(extractor):
    assert len(extractor.feature_names) == 8


def test_extract_returns_all_features(extractor):
    result = extractor.extract("https://www.example.com/", {})
    assert set(result.keys()) == set(extractor.feature_names)
