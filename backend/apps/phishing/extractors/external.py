from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

import tldextract

from .base import BaseFeatureExtractor

logger = logging.getLogger(__name__)

TOP_100K_LIMIT = 100_000
TOP_1M_LIMIT = 1_000_000


class ExternalExtractor(BaseFeatureExtractor):
    """Extract features that would normally require external services.

    Only web_traffic works — uses local Tranco top-1M CSV. Other features
    return 0 (unknown) because the required APIs are deprecated (PageRank),
    paid (Ahrefs), or blocked (Google). See thesis Section 3.4 for discussion.
    """

    # Class-level cache — loaded once, shared across instances
    _tranco_top_100k: Optional[set[str]] = None
    _tranco_top_1m: Optional[set[str]] = None
    _tranco_loaded_from: Optional[Path] = None

    def __init__(self, tranco_file: Optional[Path] = None) -> None:
        self.tranco_file = tranco_file
        if tranco_file is not None:
            self._load_tranco(tranco_file)

    @classmethod
    def _load_tranco(cls, tranco_file: Path) -> None:
        """Load Tranco CSV into class-level sets. Idempotent for the same path."""
        if cls._tranco_loaded_from == tranco_file:
            return

        if not tranco_file.exists():
            logger.warning("Tranco file not found at %s", tranco_file)
            cls._tranco_top_100k = None
            cls._tranco_top_1m = None
            cls._tranco_loaded_from = None
            return

        try:
            top_100k: set[str] = set()
            top_1m: set[str] = set()
            with open(tranco_file, encoding="utf-8") as f:
                for row in csv.reader(f):
                    if len(row) < 2:
                        continue
                    try:
                        rank = int(row[0])
                    except ValueError:
                        continue
                    domain = row[1].strip().lower()
                    if not domain:
                        continue
                    if rank <= TOP_100K_LIMIT:
                        top_100k.add(domain)
                    if rank <= TOP_1M_LIMIT:
                        top_1m.add(domain)

            cls._tranco_top_100k = top_100k
            cls._tranco_top_1m = top_1m
            cls._tranco_loaded_from = tranco_file
            logger.info(
                "Loaded Tranco: %s top-100k, %s top-1M domains",
                f"{len(top_100k):,}", f"{len(top_1m):,}",
            )
        except (OSError, csv.Error) as exc:
            logger.warning("Failed to load Tranco from %s: %s", tranco_file, exc)
            cls._tranco_top_100k = None
            cls._tranco_top_1m = None

    @property
    def feature_names(self) -> list[str]:
        return [
            "web_traffic",
            "page_rank",
            "google_index",
            "links_pointing_to_page",
            "statistical_report",
        ]

    def extract(self, url: str, parsed_context: dict) -> dict[str, int]:
        return {
            "web_traffic": self._compute_web_traffic(url, parsed_context),
            "page_rank": self._compute_page_rank(),
            "google_index": self._compute_google_index(),
            "links_pointing_to_page": self._compute_links_pointing_to_page(),
            "statistical_report": self._compute_statistical_report(),
        }

    def _compute_web_traffic(self, url: str, parsed_context: dict) -> int:
        """Check domain rank in local Tranco top-1M list.

        Returns
        -------
        int
            1 if domain in top-100k, 0 if in top-1M but not top-100k,
            -1 if not in top-1M, 0 if Tranco data unavailable.
        """
        if self._tranco_top_1m is None or self._tranco_top_100k is None:
            return 0

        domain: Optional[str] = parsed_context.get("domain")
        if not domain:
            try:
                ext = tldextract.extract(url)
                if ext.domain and ext.suffix:
                    domain = f"{ext.domain}.{ext.suffix}"
            except Exception:
                return 0

        if not domain:
            return 0

        domain = domain.lower()
        if domain in self._tranco_top_100k:
            return 1
        if domain in self._tranco_top_1m:
            return 0
        return -1

    def _compute_page_rank(self) -> int:
        """Always returns 0 (unknown).

        Google deprecated the public PageRank API in 2016. Alternative
        services (Domcop OpenPageRank) exist but are not integrated in v1.
        See thesis Section 3.4.
        """
        return 0

    def _compute_google_index(self) -> int:
        """Always returns 0 (unknown).

        Google blocks automated `site:domain.com` queries. Programmatic
        check requires paid Google Custom Search API. Deferred to v2.
        """
        return 0

    def _compute_links_pointing_to_page(self) -> int:
        """Always returns 0 (unknown).

        Backlink data requires paid APIs (Ahrefs, Moz, SEMrush).
        No free equivalent with reasonable coverage exists. Deferred to v2.
        """
        return 0

    def _compute_statistical_report(self) -> int:
        """Always returns 0 (unknown).

        PhishTank public dump requires registration and is rate-limited.
        Integration deferred to v2.
        """
        return 0
