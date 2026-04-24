from __future__ import annotations

from pathlib import Path

import pytest

from apps.phishing.extractors.external import ExternalExtractor


@pytest.fixture(autouse=True)
def reset_tranco_cache():
    """Wipe class-level Tranco cache before every test to prevent state leakage."""
    ExternalExtractor._tranco_loaded_from = None
    ExternalExtractor._tranco_top_100k = None
    ExternalExtractor._tranco_top_1m = None
    yield
    ExternalExtractor._tranco_loaded_from = None
    ExternalExtractor._tranco_top_100k = None
    ExternalExtractor._tranco_top_1m = None


@pytest.fixture
def tranco_csv(tmp_path: Path) -> Path:
    """Small synthetic Tranco CSV for testing."""
    csv = tmp_path / "tranco.csv"
    csv.write_text(
        "1,google.com\n"
        "2,youtube.com\n"
        "50000,medium-site.com\n"
        "500000,rare-site.com\n",
        encoding="utf-8",
    )
    return csv


@pytest.fixture
def ext_with_tranco(tranco_csv: Path) -> ExternalExtractor:
    return ExternalExtractor(tranco_file=tranco_csv)


# ── feature_names contract ────────────────────────────────────────────────────

def test_feature_names_contract():
    ext = ExternalExtractor()
    assert ext.feature_names == [
        "web_traffic",
        "page_rank",
        "google_index",
        "links_pointing_to_page",
        "statistical_report",
    ]


def test_extract_returns_all_keys(ext_with_tranco):
    result = ext_with_tranco.extract("https://google.com/", {"domain": "google.com"})
    assert set(result.keys()) == set(ext_with_tranco.feature_names)


# ── web_traffic: Tranco not loaded ────────────────────────────────────────────

def test_tranco_not_loaded_returns_unknown():
    ext = ExternalExtractor(tranco_file=None)
    result = ext.extract("https://google.com/", {"domain": "google.com"})
    assert result["web_traffic"] == 0


def test_tranco_file_missing_returns_unknown(tmp_path: Path):
    missing = tmp_path / "nonexistent.csv"
    ext = ExternalExtractor(tranco_file=missing)
    result = ext.extract("https://google.com/", {"domain": "google.com"})
    assert result["web_traffic"] == 0


# ── web_traffic: Tranco tiers ─────────────────────────────────────────────────

def test_tranco_top_100k_returns_plus_one(ext_with_tranco):
    result = ext_with_tranco.extract("https://google.com/", {"domain": "google.com"})
    assert result["web_traffic"] == 1


def test_tranco_top_100k_second_entry(ext_with_tranco):
    result = ext_with_tranco.extract("https://youtube.com/", {"domain": "youtube.com"})
    assert result["web_traffic"] == 1


def test_tranco_top_1m_but_not_100k_returns_zero(ext_with_tranco):
    # rare-site.com is at rank 500_000 — in top-1M, not top-100k
    result = ext_with_tranco.extract("https://rare-site.com/", {"domain": "rare-site.com"})
    assert result["web_traffic"] == 0


def test_tranco_not_in_top_1m_returns_minus_one(ext_with_tranco):
    result = ext_with_tranco.extract("https://phishing-site.xyz/", {"domain": "phishing-site.xyz"})
    assert result["web_traffic"] == -1


# ── web_traffic: domain extraction ───────────────────────────────────────────

def test_domain_extraction_fallback_from_url(ext_with_tranco):
    """When parsed_context has no 'domain', extract it from the URL."""
    result = ext_with_tranco.extract("https://www.google.com/path", {})
    # tldextract strips www → google.com → top-100k
    assert result["web_traffic"] == 1


def test_domain_from_parsed_context_takes_priority(ext_with_tranco):
    """domain in parsed_context must be used, not re-extracted from URL."""
    result = ext_with_tranco.extract(
        "https://different-url.com/",
        {"domain": "google.com"},   # overrides URL
    )
    assert result["web_traffic"] == 1


def test_domain_case_insensitive(ext_with_tranco):
    result = ext_with_tranco.extract("https://GOOGLE.COM/", {"domain": "Google.COM"})
    assert result["web_traffic"] == 1


# ── web_traffic: malformed CSV ────────────────────────────────────────────────

def test_malformed_tranco_rows_skipped(tmp_path: Path):
    csv = tmp_path / "bad.csv"
    csv.write_text(
        "not_a_rank,google.com\n"   # non-integer rank
        "\n"                         # empty line
        "1\n"                        # only one column
        "2,\n"                       # empty domain
        "3,youtube.com\n",           # valid
        encoding="utf-8",
    )
    ext = ExternalExtractor(tranco_file=csv)
    result = ext.extract("https://youtube.com/", {"domain": "youtube.com"})
    # youtube.com is rank 3 → top-100k → 1
    assert result["web_traffic"] == 1


def test_tranco_idempotent_load(tranco_csv: Path):
    """Loading the same file twice must not cause errors or double-counting."""
    ext1 = ExternalExtractor(tranco_file=tranco_csv)
    ext2 = ExternalExtractor(tranco_file=tranco_csv)
    assert ext1._tranco_top_100k is ext2._tranco_top_100k  # same set object


# ── stub features always return 0 ────────────────────────────────────────────

def test_page_rank_always_zero():
    assert ExternalExtractor()._compute_page_rank() == 0


def test_google_index_always_zero():
    assert ExternalExtractor()._compute_google_index() == 0


def test_links_pointing_always_zero():
    assert ExternalExtractor()._compute_links_pointing_to_page() == 0


def test_statistical_report_always_zero():
    assert ExternalExtractor()._compute_statistical_report() == 0


def test_stub_features_in_full_extract(ext_with_tranco):
    result = ext_with_tranco.extract("https://google.com/", {"domain": "google.com"})
    assert result["page_rank"] == 0
    assert result["google_index"] == 0
    assert result["links_pointing_to_page"] == 0
    assert result["statistical_report"] == 0
