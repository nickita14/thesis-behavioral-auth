from apps.phishing.extractors.lexical import LexicalExtractor

# URL из реального мира, для которых UCI-правило очевидно
EXPECTED_FROM_UCI_RULES = [
    ("http://www.google.com", {
        "having_ip_address": 1,       # domain, not IP
        "url_length": 1,              # short
        "having_at_symbol": 1,        # no @
        "prefix_suffix": 1,           # no dash in domain
    }),
    ("http://125.98.3.123/fake.html", {
        "having_ip_address": -1,      # IP
    }),
    ("http://bit.ly/suspicious", {
        "shortining_service": -1,     # known shortener
    }),
    ("http://very-long-subdomain.example-site.com/path/to/something/that/is/really/very/long", {
        "url_length": -1,             # > 75 chars
        "prefix_suffix": -1,          # dashes in domain
    }),
]


def test_lexical_extractor_matches_uci_rules():
    ext = LexicalExtractor()
    for url, expected in EXPECTED_FROM_UCI_RULES:
        result = ext.extract(url, {})
        for feature, expected_value in expected.items():
            assert result[feature] == expected_value, (
                f"URL={url}, feature={feature}: "
                f"got {result[feature]}, expected {expected_value}"
            )
