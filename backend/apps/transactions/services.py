from __future__ import annotations

import logging
from dataclasses import asdict
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.behavior.models import BehaviorSession
from apps.ml_engine.behavior_detectors import (
    DECISION_ANOMALOUS as BEHAVIOR_DECISION_ANOMALOUS,
)
from apps.ml_engine.behavior_detectors import (
    DECISION_SUSPICIOUS as BEHAVIOR_DECISION_SUSPICIOUS,
)
from apps.ml_engine.behavior_detectors import BehaviorAnomalyDetector
from apps.ml_engine.behavior_features import BehaviorFeatureExtractor
from apps.phishing.detectors import (
    DECISION_LEGITIMATE,
    DECISION_PHISHING,
    DECISION_SUSPICIOUS,
)
from apps.phishing.services import get_phishing_check_service

from .models import RiskAssessment, RiskDecision, TransactionAttempt

logger = logging.getLogger(__name__)

HIGH_VALUE_TRANSACTION_THRESHOLD = Decimal("1000.00")
BEHAVIOR_DECISION_NOT_AVAILABLE = "not_available"


@dataclass(frozen=True)
class SkeletonRiskResult:
    decision: str
    risk_score: float
    phishing_score: float | None
    behavior_score: float | None
    metadata: dict
    reasons: list[str]


@dataclass(frozen=True)
class PhishingRisk:
    score: float | None
    decision: str
    metadata: dict


@dataclass(frozen=True)
class BehaviorRisk:
    score: float | None
    decision: str
    metadata: dict


class TransactionAttemptService:
    """Creates transaction attempts with demo skeleton risk decisions."""

    def create_attempt(
        self,
        *,
        user,
        amount: Decimal,
        currency: str,
        recipient: str,
        behavior_session_id: UUID | None,
        target_url: str,
    ) -> TransactionAttempt:
        session = self._resolve_session(user, behavior_session_id)
        risk = self._evaluate_skeleton_risk(
            amount=amount,
            session=session,
            target_url=target_url,
        )

        with transaction.atomic():
            attempt = TransactionAttempt.objects.create(
                user=user,
                session=session,
                amount=amount,
                recipient_account=recipient,
                risk_score=risk.risk_score,
                decision=risk.decision,
            )
            RiskAssessment.objects.create(
                attempt=attempt,
                behavior_score=risk.behavior_score,
                phishing_score=risk.phishing_score,
                combined_score=risk.risk_score,
                decision=risk.decision,
                model_versions={
                    "risk_engine": "skeleton-v1",
                    "currency": currency,
                    "target_url": target_url,
                    "reasons": risk.reasons,
                    **risk.metadata,
                },
            )
        return attempt

    @staticmethod
    def _resolve_session(user, behavior_session_id: UUID | None) -> BehaviorSession | None:
        if behavior_session_id is None:
            return None
        session = BehaviorSession.objects.filter(id=behavior_session_id, user=user).first()
        if session is None:
            raise PermissionDenied("Behavior session not found or not owned by user.")
        return session

    def _evaluate_skeleton_risk(
        self,
        *,
        amount: Decimal,
        session: BehaviorSession | None,
        target_url: str,
    ) -> SkeletonRiskResult:
        phishing = self._evaluate_phishing(target_url)
        behavior = self._evaluate_behavior(session)
        decision, reasons = self._final_decision(
            amount=amount,
            phishing=phishing,
            behavior=behavior,
            target_url=target_url,
        )
        risk_score = max(
            score for score in [phishing.score, behavior.score, 0.0] if score is not None
        )
        return SkeletonRiskResult(
            decision=decision,
            risk_score=risk_score,
            phishing_score=phishing.score,
            behavior_score=behavior.score,
            metadata={
                **phishing.metadata,
                **behavior.metadata,
            },
            reasons=reasons,
        )

    def _evaluate_phishing(self, target_url: str) -> PhishingRisk:
        if not target_url:
            return PhishingRisk(
                score=None,
                decision="not_checked",
                metadata={
                    "phishing_available": False,
                    "phishing_decision": "not_checked",
                    "probability_phishing": None,
                    "probability_legitimate": None,
                },
            )

        try:
            prediction = get_phishing_check_service().check_url(target_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Transaction phishing check failed for %s: %s", target_url, exc)
            return PhishingRisk(
                score=None,
                decision="unknown",
                metadata={
                    "phishing_available": False,
                    "phishing_decision": "unknown",
                    "probability_phishing": None,
                    "probability_legitimate": None,
                },
            )

        phishing_score = float(prediction.probability_phishing)
        return PhishingRisk(
            score=phishing_score,
            decision=prediction.decision,
            metadata={
                "phishing_available": True,
                "phishing_decision": prediction.decision,
                "probability_phishing": phishing_score,
                "probability_legitimate": float(prediction.probability_legitimate),
            },
        )

    def _evaluate_behavior(self, session: BehaviorSession | None) -> BehaviorRisk:
        if session is None:
            return BehaviorRisk(
                score=None,
                decision=BEHAVIOR_DECISION_NOT_AVAILABLE,
                metadata={
                    "behavior_available": False,
                    "behavior_decision": BEHAVIOR_DECISION_NOT_AVAILABLE,
                    "behavior_anomaly_score": None,
                    "behavior_features": {},
                },
            )

        try:
            features = BehaviorFeatureExtractor().extract(session)
            result = BehaviorAnomalyDetector().predict(features)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Transaction behavior analysis failed for %s: %s", session.id, exc)
            return BehaviorRisk(
                score=None,
                decision=BEHAVIOR_DECISION_SUSPICIOUS,
                metadata={
                    "behavior_available": False,
                    "behavior_decision": BEHAVIOR_DECISION_SUSPICIOUS,
                    "behavior_anomaly_score": None,
                    "behavior_features": {},
                    "behavior_error": "analysis_failed",
                },
            )

        return BehaviorRisk(
            score=float(result.anomaly_score),
            decision=result.decision,
            metadata={
                "behavior_available": True,
                "behavior_decision": result.decision,
                "behavior_anomaly_score": float(result.anomaly_score),
                "behavior_features": asdict(features),
            },
        )

    @staticmethod
    def _final_decision(
        *,
        amount: Decimal,
        phishing: PhishingRisk,
        behavior: BehaviorRisk,
        target_url: str,
    ) -> tuple[str, list[str]]:
        reasons: list[str] = []
        if phishing.decision == DECISION_PHISHING:
            reasons.append("Target URL was classified as phishing.")
            return RiskDecision.DENY, reasons
        if phishing.decision == DECISION_SUSPICIOUS:
            reasons.append("Target URL is suspicious.")
            return RiskDecision.CHALLENGE, reasons
        if target_url and phishing.decision == "unknown":
            reasons.append("Phishing check was unavailable.")
            return RiskDecision.CHALLENGE, reasons
        if behavior.decision == BEHAVIOR_DECISION_ANOMALOUS:
            reasons.append("Behavior session looks anomalous.")
            return RiskDecision.CHALLENGE, reasons
        if behavior.metadata.get("behavior_error"):
            reasons.append("Behavior analysis was unavailable.")
            return RiskDecision.CHALLENGE, reasons
        if (
            behavior.decision == BEHAVIOR_DECISION_SUSPICIOUS
            and amount >= HIGH_VALUE_TRANSACTION_THRESHOLD
        ):
            reasons.append("High-value transaction with suspicious behavior baseline.")
            return RiskDecision.CHALLENGE, reasons
        if phishing.decision == DECISION_LEGITIMATE:
            reasons.append("Target URL appears legitimate.")
        if behavior.decision == BEHAVIOR_DECISION_NOT_AVAILABLE:
            reasons.append("No behavior session was attached.")
        elif behavior.decision == BEHAVIOR_DECISION_SUSPICIOUS:
            reasons.append("Behavior baseline is suspicious but below high-value threshold.")
        else:
            reasons.append("Behavior baseline did not flag an anomaly.")
        return RiskDecision.ALLOW, reasons
