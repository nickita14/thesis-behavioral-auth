from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass


@dataclass
class URLFeatures:
    """Container for all 30 UCI Phishing features.

    Field names match the artifact's feature_names exactly (snake_case).
    Values: -1 (phishing signal), 0 (suspicious/unknown), 1 (legitimate signal).
    Default 0 is returned when extraction fails or times out.
    """

    # Lexical (8)
    having_ip_address: int = 0
    url_length: int = 0
    shortining_service: int = 0
    having_at_symbol: int = 0
    double_slash_redirecting: int = 0
    prefix_suffix: int = 0
    having_sub_domain: int = 0
    https_token: int = 0
    # SSL/HTTPS (1)
    sslfinal_state: int = 0
    # Domain (3)
    domain_registration_length: int = 0
    favicon: int = 0
    port: int = 0
    # HTML/JS (11)
    request_url: int = 0
    url_of_anchor: int = 0
    links_in_tags: int = 0
    sfh: int = 0
    submitting_to_email: int = 0
    abnormal_url: int = 0
    redirect: int = 0
    on_mouseover: int = 0
    rightclick: int = 0
    popupwindow: int = 0
    iframe: int = 0
    # Domain age (2)
    age_of_domain: int = 0
    dnsrecord: int = 0
    # External services (5)
    web_traffic: int = 0
    page_rank: int = 0
    google_index: int = 0
    links_pointing_to_page: int = 0
    statistical_report: int = 0

    def to_vector(self, feature_order: list[str]) -> list[int]:
        """Return feature values in the specified order (for model input).

        Parameters
        ----------
        feature_order : list[str]
            Ordered list of feature names matching the model's training columns.

        Returns
        -------
        list[int]
            Feature values in the same order as feature_order.
        """
        d = asdict(self)
        return [d[name] for name in feature_order]


class BaseFeatureExtractor(ABC):
    """Base interface for all URL feature extractors."""

    @property
    @abstractmethod
    def feature_names(self) -> list[str]:
        """Names of features this extractor produces."""

    @abstractmethod
    def extract(self, url: str, parsed_context: dict) -> dict[str, int]:
        """Extract features from URL and shared context.

        Parameters
        ----------
        url : str
            The full URL to analyse.
        parsed_context : dict
            Mutable dict shared across extractors in the pipeline.
            Lexical extractor populates it first; subsequent extractors
            may read pre-computed values (parsed URL, fetched HTML, etc.).

        Returns
        -------
        dict[str, int]
            Mapping of feature_name -> value (-1, 0, or 1).
            On any error or timeout returns all own features as 0.
        """
