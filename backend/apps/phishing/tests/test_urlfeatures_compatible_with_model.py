from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import joblib

from apps.phishing.extractors.base import URLFeatures

_ARTIFACT_PATH = (
    Path(__file__).resolve().parents[4] / "data/models/phishing_xgboost_v1.joblib"
)


def test_urlfeatures_matches_model_feature_names():
    """URLFeatures field names must match the model artifact's feature_names exactly.

    This test catches any future rename or typo before it reaches predict().
    Order does not have to match — to_vector(feature_order) handles that.
    """
    artifact = joblib.load(_ARTIFACT_PATH)
    model_features = set(artifact["feature_names"])
    our_features = {f.name for f in fields(URLFeatures)}

    assert our_features == model_features, (
        f"Name mismatch — "
        f"missing from URLFeatures: {model_features - our_features}, "
        f"extra in URLFeatures: {our_features - model_features}"
    )
