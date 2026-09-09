from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from janus_research.schema import Decision, PopulationClass, ResponseRecord


@dataclass(frozen=True)
class ScoringThresholds:
    human_log_threshold: float
    ai_log_threshold: float

    def __post_init__(self) -> None:
        if self.human_log_threshold >= self.ai_log_threshold:
            raise ValueError("human threshold must be lower than AI threshold")


@dataclass(frozen=True)
class SessionScore:
    session_id: str
    log_likelihood_ratio: float
    ai_probability: float
    decision: Decision
    contributions: tuple[float, ...]


class LikelihoodScorer:
    """Interpretable family-level P(response | population, family) baseline."""

    def __init__(self, smoothing: float, thresholds: ScoringThresholds) -> None:
        if smoothing <= 0:
            raise ValueError("smoothing must be positive")
        self.smoothing = smoothing
        self.thresholds = thresholds
        self._counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        self._options: dict[str, set[str]] = defaultdict(set)
        self._fitted = False

    def fit(self, records: Iterable[ResponseRecord]) -> LikelihoodScorer:
        count = 0
        for record in records:
            population = "human" if record.population_class == PopulationClass.HUMAN else "ai"
            self._counts[(record.challenge_family, population)][record.response] += 1
            self._options[record.challenge_family].update(record.public_option_order)
            count += 1
        populations = {population for _, population in self._counts}
        if count == 0 or populations != {"human", "ai"}:
            raise ValueError("training requires both human and artificial responses")
        self._fitted = True
        return self

    def _probability(self, family: str, population: str, response: str) -> float:
        if not self._fitted:
            raise RuntimeError("scorer must be fitted before scoring")
        options = self._options.get(family)
        if not options or response not in options:
            raise ValueError(f"unknown response {response!r} for family {family!r}")
        counts = self._counts[(family, population)]
        return (counts[response] + self.smoothing) / (
            sum(counts.values()) + self.smoothing * len(options)
        )

    def evidence(self, record: ResponseRecord) -> float:
        p_ai = self._probability(record.challenge_family, "ai", record.response)
        p_human = self._probability(record.challenge_family, "human", record.response)
        return math.log(p_ai / p_human)

    def score_session(self, records: Iterable[ResponseRecord]) -> SessionScore:
        ordered = sorted(records, key=lambda record: record.sequence)
        if not ordered:
            raise ValueError("cannot score an empty session")
        session_ids = {record.session_id for record in ordered}
        if len(session_ids) != 1:
            raise ValueError("all records must belong to one session")
        contributions = tuple(self.evidence(record) for record in ordered)
        score = sum(contributions)
        probability = 1 / (1 + math.exp(-max(min(score, 700), -700)))
        if score <= self.thresholds.human_log_threshold:
            decision = Decision.HUMAN_COMPATIBLE
        elif score >= self.thresholds.ai_log_threshold:
            decision = Decision.AI_COMPATIBLE
        else:
            decision = Decision.UNKNOWN
        return SessionScore(ordered[0].session_id, score, probability, decision, contributions)
