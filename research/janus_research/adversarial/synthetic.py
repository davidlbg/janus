from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from janus_research.schema import ChallengeDefinition, PopulationClass, ResponseRecord
from janus_research.splits import SplitAssigner


@dataclass(frozen=True)
class SyntheticPopulation:
    name: str
    population_class: PopulationClass
    canonical_weights: tuple[float, float, float, float]
    model_version: str | None
    condition: str

    def probabilities(self, option_ids: list[str]) -> np.ndarray:
        rank = {f"o{index + 1}": weight for index, weight in enumerate(self.canonical_weights)}
        weights = np.asarray([rank[option] for option in option_ids], dtype=float)
        return weights / weights.sum()


class SyntheticHumanPopulation(SyntheticPopulation):
    def __init__(
        self, weights: tuple[float, float, float, float] = (0.55, 0.25, 0.15, 0.05)
    ) -> None:
        super().__init__("synthetic-human", PopulationClass.HUMAN, weights, None, "H_SYNTHETIC")


class SyntheticAIPopulation(SyntheticPopulation):
    def __init__(
        self,
        weights: tuple[float, float, float, float] = (0.05, 0.15, 0.25, 0.55),
        *,
        condition: str = "M0",
    ) -> None:
        super().__init__(
            f"synthetic-ai-{condition.lower()}",
            PopulationClass.AI,
            weights,
            f"synthetic-ai-v1-{condition.lower()}",
            condition,
        )


class SyntheticAdversarialAIPopulation(SyntheticPopulation):
    def __init__(self, human_similarity: float = 0.8, *, condition: str = "M5") -> None:
        if not 0 <= human_similarity <= 1:
            raise ValueError("human_similarity must be between 0 and 1")
        human = np.asarray((0.55, 0.25, 0.15, 0.05))
        ai = np.asarray((0.05, 0.15, 0.25, 0.55))
        mixed = human_similarity * human + (1 - human_similarity) * ai
        super().__init__(
            f"synthetic-adversarial-ai-{condition.lower()}",
            PopulationClass.ADVERSARIAL_AI,
            (float(mixed[0]), float(mixed[1]), float(mixed[2]), float(mixed[3])),
            "synthetic-adversarial-ai-v1",
            condition,
        )


def _latency_bucket(rng: np.random.Generator, population: PopulationClass) -> str:
    base = 1700 if population == PopulationClass.HUMAN else 900
    latency = max(100, int(rng.normal(base, 450)))
    if latency < 500:
        return "0-500"
    if latency < 1500:
        return "500-1500"
    if latency < 2500:
        return "1500-2500"
    return "2500+"


def simulate_experiment(
    challenges: Iterable[ChallengeDefinition],
    populations: Iterable[SyntheticPopulation],
    *,
    sessions_per_population: int,
    seed: int,
    study_version: str,
    split_policy: dict[str, float],
) -> list[ResponseRecord]:
    challenge_list = list(challenges)
    if not challenge_list:
        raise ValueError("simulation requires challenges")
    subject_assigner = SplitAssigner(f"{study_version}:subjects", split_policy)
    records: list[ResponseRecord] = []
    for population_index, population in enumerate(populations):
        for subject_index in range(sessions_per_population):
            subject_id = hashlib.sha256(
                f"{study_version}:{population.name}:{subject_index}".encode()
            ).hexdigest()[:24]
            subject_split = subject_assigner.assign(subject_id)
            session_id = f"synth_{population_index}_{subject_index:05d}"
            rng = np.random.default_rng(seed + population_index * 100_000 + subject_index)
            eligible = [
                challenge for challenge in challenge_list if challenge.split == subject_split
            ]
            selected: list[ChallengeDefinition] = []
            for family in sorted({challenge.family for challenge in challenge_list}):
                family_candidates = [
                    challenge for challenge in eligible if challenge.family == family
                ]
                if not family_candidates:
                    raise ValueError(f"split {subject_split} has no challenge for family {family}")
                sample_size = min(3, len(family_candidates))
                indices = rng.choice(len(family_candidates), size=sample_size, replace=False)
                selected.extend(family_candidates[int(index)] for index in indices)
            rng.shuffle(selected)
            for sequence, challenge in enumerate(selected):
                option_ids = [str(option["id"]) for option in challenge.public_payload["options"]]
                response = str(rng.choice(option_ids, p=population.probabilities(option_ids)))
                records.append(
                    ResponseRecord(
                        study_version=study_version,
                        subject_id=subject_id,
                        population_class=population.population_class,
                        model_version=population.model_version,
                        model_family=population.name if population.model_version else None,
                        condition=population.condition,
                        session_id=session_id,
                        challenge_id=challenge.challenge_id,
                        challenge_family=challenge.family,
                        generator_version=challenge.generator_version,
                        seed_reference=hashlib.sha256(str(challenge.seed).encode()).hexdigest()[
                            :16
                        ],
                        sequence=sequence,
                        public_option_order=option_ids,
                        response=response,
                        response_latency_bucket=_latency_bucket(rng, population.population_class),
                        revision_count=int(
                            rng.random()
                            < (
                                0.12
                                if population.population_class == PopulationClass.HUMAN
                                else 0.02
                            )
                        ),
                        input_modality="synthetic",
                        timestamp=datetime.now(UTC),
                        split=subject_split,
                        challenge_split=challenge.split,
                    )
                )
    rng = np.random.default_rng(seed + 9_999_999)
    rng.shuffle(records)
    return records
