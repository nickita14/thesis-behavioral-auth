from __future__ import annotations

import re
from urllib.parse import urlparse

import tldextract

from .base import BaseFeatureExtractor

# Known URL shortening services (Mohammad et al. 2014, extended)
_SHORTENERS = {
    "bit.ly", "goo.gl", "shorte.st", "go2l.ink", "x.co", "ow.ly",
    "t.co", "tinyurl.com", "tr.im", "is.gd", "cli.gs", "yfrog.com",
    "migre.me", "ff.im", "tiny.cc", "url4.eu", "twit.ac", "su.pr",
    "twurl.nl", "snipurl.com", "short.to", "budurl.com", "ping.fm",
    "post.ly", "just.as", "bkite.com", "snipr.com", "fic.kr",
    "loopt.us", "doiop.com", "short.ie", "kl.am", "wp.me", "rubyurl.com",
    "om.ly", "to.ly", "bit.do", "lnkd.in", "db.tt", "qr.ae",
    "adf.ly", "bitly.com", "cur.lv", "tinyurl.com", "ity.im", "q.gs",
    "po.st", "bc.vc", "twitthis.com", "u.to", "j.mp", "buzurl.com",
    "cutt.us", "u.bb", "yourls.org", "prettylinkpro.com", "scrnch.me",
    "filoops.info", "vzturl.com", "qr.net", "1url.com", "tweez.me",
    "v.gd", "tr.im", "link.zip.net",
}

# IPv4 pattern
_IPV4_PATTERN = re.compile(
    r"(?:^|[^0-9])(\d{1,3}(?:\.\d{1,3}){3})(?:[^0-9]|$)"
)
# IPv6 pattern (simplified: hex groups separated by colons)
_IPV6_PATTERN = re.compile(r"\[?[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){2,7}\]?")


def _having_ip_address(url: str) -> int:
    """-1 if URL contains IPv4 or IPv6 address in the host, 1 otherwise."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if _IPV4_PATTERN.search(host):
        return -1
    if _IPV6_PATTERN.search(host):
        return -1
    return 1


def _url_length(url: str) -> int:
    """1 if len < 54, 0 if 54–75, -1 if > 75 (Mohammad et al. 2014)."""
    n = len(url)
    if n < 54:
        return 1
    if n <= 75:
        return 0
    return -1


def _shortining_service(url: str) -> int:
    """-1 if domain belongs to a known URL shortening service, 1 otherwise."""
    ext = tldextract.extract(url)
    domain = f"{ext.domain}.{ext.suffix}".lower() if ext.suffix else ext.domain.lower()
    return -1 if domain in _SHORTENERS else 1


def _having_at_symbol(url: str) -> int:
    """-1 if '@' appears in the URL (browser ignores everything before it), 1 otherwise."""
    return -1 if "@" in url else 1


def _double_slash_redirecting(url: str) -> int:
    """-1 if '//' appears after position 7 (i.e. not in 'http://'), 1 otherwise."""
    # Strip the scheme part before checking
    after_scheme = url.find("//")
    if after_scheme == -1:
        return 1
    # Check for another '//' after the scheme's '//'
    rest = url[after_scheme + 2:]
    return -1 if "//" in rest else 1


def _prefix_suffix(url: str) -> int:
    """-1 if the domain contains a hyphen (common in phishing spoofs), 1 otherwise."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return -1 if "-" in host else 1


def _having_sub_domain(url: str, ext: tldextract.tldextract.ExtractResult) -> int:
    """1 if no subdomain, 0 if one subdomain (e.g. www), -1 if two or more subdomains."""
    subdomain = ext.subdomain
    if not subdomain:
        return 1
    parts = [p for p in subdomain.split(".") if p]
    if len(parts) == 1:
        return 0
    return -1


def _https_token(url: str) -> int:
    """-1 if 'https' appears in the domain part of the URL (not the scheme), 1 otherwise.

    Phishers sometimes use domains like 'https-secure-login.com' to deceive users.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return -1 if "https" in host.lower() else 1


class LexicalExtractor(BaseFeatureExtractor):
    """Extracts 8 lexical features directly from the URL string.

    No network requests are made. Also populates parsed_context with
    'parsed_url' (urllib.parse.ParseResult) and 'tld_extract'
    (tldextract.ExtractResult) for downstream extractors.
    """

    _FEATURE_NAMES = [
        "having_ip_address",
        "url_length",
        "shortining_service",
        "having_at_symbol",
        "double_slash_redirecting",
        "prefix_suffix",
        "having_sub_domain",
        "https_token",
    ]

    @property
    def feature_names(self) -> list[str]:
        return self._FEATURE_NAMES

    def extract(self, url: str, parsed_context: dict) -> dict[str, int]:
        """Extract 8 lexical features and populate parsed_context.

        Parameters
        ----------
        url : str
            Full URL string.
        parsed_context : dict
            Will be populated with keys 'parsed_url', 'tld_extract', 'domain'.

        Returns
        -------
        dict[str, int]
            8 feature values, all defaulting to 0 on unexpected error.
        """
        try:
            parsed = urlparse(url)
            ext = tldextract.extract(url)

            parsed_context["parsed_url"] = parsed
            parsed_context["tld_extract"] = ext
            parsed_context["domain"] = (
                f"{ext.domain}.{ext.suffix}".lower() if ext.suffix else ext.domain.lower()
            )

            return {
                "having_ip_address": _having_ip_address(url),
                "url_length": _url_length(url),
                "shortining_service": _shortining_service(url),
                "having_at_symbol": _having_at_symbol(url),
                "double_slash_redirecting": _double_slash_redirecting(url),
                "prefix_suffix": _prefix_suffix(url),
                "having_sub_domain": _having_sub_domain(url, ext),
                "https_token": _https_token(url),
            }
        except Exception:
            return {name: 0 for name in self._FEATURE_NAMES}
