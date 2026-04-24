from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urlparse

import requests
import tldextract
from bs4 import BeautifulSoup

from .base import BaseFeatureExtractor

logger = logging.getLogger(__name__)

HTML_TIMEOUT_SECONDS = 4.0
MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class HtmlExtractor(BaseFeatureExtractor):
    """Extracts 11 HTML-based phishing features by fetching and parsing the page."""

    _FEATURE_NAMES = [
        "request_url", "url_of_anchor", "links_in_tags", "sfh",
        "submitting_to_email", "redirect", "on_mouseover", "rightclick",
        "popupwindow", "iframe", "favicon",
    ]

    @property
    def feature_names(self) -> list[str]:
        return self._FEATURE_NAMES

    def extract(self, url: str, parsed_context: dict) -> dict[str, int]:
        features: dict[str, int] = {name: 0 for name in self._FEATURE_NAMES}

        fetch_result = self._fetch(url)
        if fetch_result is None:
            return features

        soup, redirect_count, final_url = fetch_result
        base_domain = self._registered_domain(final_url)

        features["request_url"] = self._compute_request_url(soup, base_domain)
        features["url_of_anchor"] = self._compute_url_of_anchor(soup, base_domain)
        features["links_in_tags"] = self._compute_links_in_tags(soup, base_domain)
        features["sfh"] = self._compute_sfh(soup, base_domain)
        features["submitting_to_email"] = self._compute_submitting_to_email(soup)
        features["redirect"] = self._compute_redirect(redirect_count)
        features["on_mouseover"] = self._compute_on_mouseover(soup)
        features["rightclick"] = self._compute_rightclick(soup)
        features["popupwindow"] = self._compute_popupwindow(soup)
        features["iframe"] = self._compute_iframe(soup)
        features["favicon"] = self._compute_favicon(soup, base_domain)

        return features

    # ── fetch ─────────────────────────────────────────────────────────────────

    def _fetch(self, url: str) -> Optional[tuple[BeautifulSoup, int, str]]:
        """Fetch URL, return (soup, redirect_count, final_url). None on failure."""
        try:
            response = requests.get(
                url,
                timeout=HTML_TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                stream=True,
            )
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_CONTENT_LENGTH:
                logger.info("HTML too large for %s: %s bytes", url, content_length)
                return None

            content = response.raw.read(MAX_CONTENT_LENGTH, decode_content=True)
            soup = BeautifulSoup(content, "html.parser")
            redirect_count = len(response.history)
            return soup, redirect_count, response.url

        except requests.exceptions.RequestException as exc:
            logger.info("HTML fetch failed for %s: %s", url, exc)
            return None
        except Exception as exc:
            logger.warning("Unexpected fetch error for %s: %s", url, exc)
            return None

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _registered_domain(url: str) -> str:
        ext = tldextract.extract(url)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}".lower()
        return ""

    def _is_external(self, target_url: str, base_domain: str) -> Optional[bool]:
        """True if target_url belongs to a different registered domain.

        Returns None for relative URLs, non-HTTP schemes, or parse failures.
        """
        if not base_domain or not target_url:
            return None
        if not target_url.lower().startswith(("http://", "https://")):
            return None
        target_domain = self._registered_domain(target_url)
        if not target_domain:
            return None
        return target_domain != base_domain

    @staticmethod
    def _ratio_to_feature(ratio: float, low: float, high: float) -> int:
        if ratio < low:
            return 1
        if ratio <= high:
            return 0
        return -1

    @staticmethod
    def _script_text(soup: BeautifulSoup) -> str:
        return " ".join(s.get_text() for s in soup.find_all("script"))

    # ── per-feature compute methods ───────────────────────────────────────────

    def _compute_request_url(self, soup: BeautifulSoup, base_domain: str) -> int:
        """Ratio of external <img/video/audio src> to all resolved media src."""
        tags = soup.find_all(["img", "video", "audio"])
        total = external = 0
        for tag in tags:
            src = (tag.get("src") or "").strip()
            is_ext = self._is_external(src, base_domain)
            if is_ext is None:
                continue
            total += 1
            if is_ext:
                external += 1
        if total == 0:
            return 1
        return self._ratio_to_feature(external / total, 0.22, 0.61)

    def _compute_url_of_anchor(self, soup: BeautifulSoup, base_domain: str) -> int:
        """Ratio of external absolute <a href> to all resolved anchor hrefs."""
        total = external = 0
        for a in soup.find_all("a"):
            href = (a.get("href") or "").strip()
            is_ext = self._is_external(href, base_domain)
            if is_ext is None:
                continue
            total += 1
            if is_ext:
                external += 1
        if total == 0:
            return 1
        return self._ratio_to_feature(external / total, 0.31, 0.67)

    def _compute_links_in_tags(self, soup: BeautifulSoup, base_domain: str) -> int:
        """Ratio of external URLs in <meta>, <script src>, <link href>."""
        total = external = 0
        for tag in soup.find_all(["meta", "script", "link"]):
            raw = tag.get("href") or tag.get("src") or tag.get("content") or ""
            url = raw.strip() if isinstance(raw, str) else ""
            is_ext = self._is_external(url, base_domain)
            if is_ext is None:
                continue
            total += 1
            if is_ext:
                external += 1
        if total == 0:
            return 1
        return self._ratio_to_feature(external / total, 0.17, 0.81)

    def _compute_sfh(self, soup: BeautifulSoup, base_domain: str) -> int:
        """Server Form Handler: analyse <form action> values (worst-case wins)."""
        forms = soup.find_all("form")
        if not forms:
            return 1
        has_invalid = has_external = False
        for form in forms:
            action = (form.get("action") or "").strip().lower()
            if action in ("", "#", "about:blank"):
                has_invalid = True
            elif action.startswith(("http://", "https://")):
                if self._is_external(action, base_domain):
                    has_external = True
        if has_invalid:
            return -1
        if has_external:
            return 0
        return 1

    def _compute_submitting_to_email(self, soup: BeautifulSoup) -> int:
        for form in soup.find_all("form"):
            if "mailto:" in (form.get("action") or "").lower():
                return -1
        return 1

    @staticmethod
    def _compute_redirect(redirect_count: int) -> int:
        return 1 if redirect_count <= 2 else -1

    def _compute_on_mouseover(self, soup: BeautifulSoup) -> int:
        if soup.find_all(attrs={"onmouseover": True}):
            return -1
        if "window.status" in self._script_text(soup):
            return -1
        return 1

    def _compute_rightclick(self, soup: BeautifulSoup) -> int:
        if soup.find_all(attrs={"oncontextmenu": True}):
            return -1
        text = self._script_text(soup)
        for pat in (r"event\.button\s*={1,3}\s*2", r"contextmenu"):
            if re.search(pat, text):
                return -1
        return 1

    def _compute_popupwindow(self, soup: BeautifulSoup) -> int:
        if "window.open(" in self._script_text(soup):
            return -1
        return 1

    @staticmethod
    def _compute_iframe(soup: BeautifulSoup) -> int:
        if soup.find_all(["iframe", "frameset", "frame"]):
            return -1
        return 1

    def _compute_favicon(self, soup: BeautifulSoup, base_domain: str) -> int:
        icon = soup.find("link", rel=lambda v: v and any(
            "icon" in r.lower() for r in (v if isinstance(v, list) else [v])
        ))
        if icon is None:
            return 0
        href = (icon.get("href") or "").strip()
        if not href:
            return 0
        if href.startswith(("http://", "https://")):
            return -1 if self._is_external(href, base_domain) else 1
        return 1  # relative path → same domain
