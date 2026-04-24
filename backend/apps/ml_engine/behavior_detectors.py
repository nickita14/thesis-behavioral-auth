from __future__ import annotations

from dataclasses import dataclass

from sklearn.ensemble import IsolationForest

from .behavior_features import BehaviorFeatures

DECISION_LEGITIMATE = "legitimate"
DECISION_SUSPICIOUS = "suspicious"
DECISION_ANOMALOUS = "anomalous"


@dataclass(frozen=True)
class BehaviorAnomalyResult:
    anomaly_score: float
    is_anomaly: bool
    decision: str


class BehaviorAnomalyDetector:
    """Baseline IsolationForest detector for behavior feature vectors.

    This class is intentionally artifact-ready: a preloaded sklearn-compatible
    model can be injected later, while the current demo can fit an in-memory
    baseline for experiments.
    """

    def __init__(
        self,
        model: IsolationForest | None = None,
        contamination: float = 0.1,
        random_state: int = 42,
    ) -> None:
        self.model = model or IsolationForest(
            contamination=contamination,
            random_state=random_state,
        )
        self._is_fitted = model is not None

    def fit(self, features_list: list[BehaviorFeatures]) -> "BehaviorAnomalyDetector":
        if not features_list:
            self._is_fitted = False
            return self
        self.model.fit([features.to_vector() for features in features_list])
        self._is_fitted = True
        return self

    def score(self, features: BehaviorFeatures) -> float:
        if not self._is_fitted:
            return 0.0
        return float(-self.model.score_samples([features.to_vector()])[0])

    def predict(self, features: BehaviorFeatures) -> BehaviorAnomalyResult:
        if not self._is_fitted:
            return BehaviorAnomalyResult(
                anomaly_score=0.0,
                is_anomaly=False,
                decision=DECISION_SUSPICIOUS,
            )

        prediction = int(self.model.predict([features.to_vector()])[0])
        is_anomaly = prediction == -1
        return BehaviorAnomalyResult(
            anomaly_score=self.score(features),
            is_anomaly=is_anomaly,
            decision=DECISION_ANOMALOUS if is_anomaly else DECISION_LEGITIMATE,
        )
