from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import fields
from pathlib import Path
from typing import Iterable

from .base import BaseFeatureExtractor, URLFeatures
from .external import ExternalExtractor
from .html_ext import HtmlExtractor
from .lexical import LexicalExtractor
from .ssl_ext import SslExtractor
from .whois_ext import WhoisExtractor

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 8.0


class URLFeatureExtractor:
    """Orchestrates URL feature extractors and returns a URLFeatures object."""

    def __init__(
        self,
        lexical_extractor: BaseFeatureExtractor | None = None,
        parallel_extractors: Iterable[BaseFeatureExtractor] | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        tranco_file: Path | None = None,
    ) -> None:
        self.lexical_extractor = lexical_extractor or LexicalExtractor()
        self.parallel_extractors = list(
            parallel_extractors
            if parallel_extractors is not None
            else self._default_parallel_extractors(tranco_file)
        )
        self.timeout_seconds = timeout_seconds
        self._known_feature_names = {field.name for field in fields(URLFeatures)}

    def extract(self, url: str) -> URLFeatures:
        """Extract all known URL features.

        Lexical features run first because they populate shared parsed_context.
        Slow or broken downstream extractors leave their own fields at 0.
        """
        parsed_context: dict = {}
        values: dict[str, int] = {}

        self._run_lexical(url, parsed_context, values)
        self._run_parallel(url, parsed_context, values)

        return URLFeatures(**values)

    def _run_lexical(
        self,
        url: str,
        parsed_context: dict,
        values: dict[str, int],
    ) -> None:
        try:
            result = self.lexical_extractor.extract(url, parsed_context)
        except Exception as exc:
            logger.warning("Lexical feature extraction failed for %s: %s", url, exc)
            return
        self._merge_known_features(values, result)

    def _run_parallel(
        self,
        url: str,
        parsed_context: dict,
        values: dict[str, int],
    ) -> None:
        if not self.parallel_extractors:
            return

        executor = ThreadPoolExecutor(max_workers=len(self.parallel_extractors))
        futures = {
            executor.submit(extractor.extract, url, parsed_context): extractor
            for extractor in self.parallel_extractors
        }
        done, pending = wait(futures, timeout=self.timeout_seconds)

        for future in done:
            extractor = futures[future]
            try:
                self._merge_known_features(values, future.result())
            except Exception as exc:
                logger.warning(
                    "%s feature extraction failed for %s: %s",
                    extractor.__class__.__name__,
                    url,
                    exc,
                )

        for future in pending:
            extractor = futures[future]
            logger.warning(
                "%s feature extraction timed out for %s",
                extractor.__class__.__name__,
                url,
            )
            future.cancel()

        executor.shutdown(wait=False, cancel_futures=True)

    def _merge_known_features(
        self,
        values: dict[str, int],
        result: dict[str, int] | None,
    ) -> None:
        if not result:
            return
        for name, value in result.items():
            if name in self._known_feature_names:
                values[name] = value

    @staticmethod
    def _default_parallel_extractors(
        tranco_file: Path | None,
    ) -> list[BaseFeatureExtractor]:
        return [
            WhoisExtractor(),
            SslExtractor(),
            HtmlExtractor(),
            ExternalExtractor(tranco_file=tranco_file),
        ]
