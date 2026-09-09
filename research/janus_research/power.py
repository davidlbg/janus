from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from scipy.stats import norm


@dataclass(frozen=True)
class PowerPlan:
    human_fpr_target: float
    expected_ai_tpr: float
    confidence: float
    desired_half_width: float
    human_sessions_zero_events: int
    human_sessions_precision: int
    ai_sessions_precision: int
    attrition_adjusted_human_sessions: int
    attrition_adjusted_ai_sessions: int
    caveat: str

    def to_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


def plan_power(
    human_fpr_target: float,
    expected_ai_tpr: float,
    *,
    confidence: float = 0.95,
    desired_half_width: float = 0.02,
    attrition: float = 0.1,
) -> PowerPlan:
    for name, value in {
        "human_fpr_target": human_fpr_target,
        "expected_ai_tpr": expected_ai_tpr,
        "confidence": confidence,
        "desired_half_width": desired_half_width,
    }.items():
        if not 0 < value < 1:
            raise ValueError(f"{name} must be strictly between 0 and 1")
    if not 0 <= attrition < 1:
        raise ValueError("attrition must be in [0, 1)")
    alpha = 1 - confidence
    z = float(norm.ppf(1 - alpha / 2))
    zero_event_n = math.ceil(-math.log(alpha) / human_fpr_target)
    human_precision_n = math.ceil(
        z**2 * human_fpr_target * (1 - human_fpr_target) / desired_half_width**2
    )
    ai_precision_n = math.ceil(
        z**2 * expected_ai_tpr * (1 - expected_ai_tpr) / desired_half_width**2
    )
    human_n = max(zero_event_n, human_precision_n)
    return PowerPlan(
        human_fpr_target=human_fpr_target,
        expected_ai_tpr=expected_ai_tpr,
        confidence=confidence,
        desired_half_width=desired_half_width,
        human_sessions_zero_events=zero_event_n,
        human_sessions_precision=human_precision_n,
        ai_sessions_precision=ai_precision_n,
        attrition_adjusted_human_sessions=math.ceil(human_n / (1 - attrition)),
        attrition_adjusted_ai_sessions=math.ceil(ai_precision_n / (1 - attrition)),
        caveat=(
            "Planning approximation for independent sessions; clustering, exclusions, "
            "multiplicity and the final estimand require statistical review. Zero observed "
            "events must be reported with an upper confidence bound, never as FPR=0."
        ),
    )
