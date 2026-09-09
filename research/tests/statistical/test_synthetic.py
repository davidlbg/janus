from collections import Counter

from janus_research.adversarial import (
    SyntheticAdversarialAIPopulation,
    SyntheticAIPopulation,
    SyntheticHumanPopulation,
    simulate_experiment,
)
from janus_research.generators import FreeChoiceGenerator, SemanticGenerator, VisualGenerator
from janus_research.metrics import total_variation_distance
from janus_research.schema import DatasetSplit, PopulationClass

POLICY = {"discovery": 1.0, "validation": 0.0, "holdout": 0.0}


def _distribution(records, population):
    counts = Counter(record.response for record in records if record.population_class == population)
    return [counts[f"o{index}"] for index in range(1, 5)]


def test_known_synthetic_distributions_are_recovered() -> None:
    challenges = [SemanticGenerator().generate(seed, DatasetSplit.DISCOVERY) for seed in range(12)]
    records = simulate_experiment(
        challenges,
        [SyntheticHumanPopulation(), SyntheticAIPopulation()],
        sessions_per_population=500,
        seed=91,
        study_version="test",
        split_policy=POLICY,
    )
    human = _distribution(records, PopulationClass.HUMAN)
    ai = _distribution(records, PopulationClass.AI)
    assert total_variation_distance(human, ai) > 0.35


def test_adversary_converging_to_human_reduces_discrimination() -> None:
    human = SyntheticHumanPopulation().canonical_weights
    weak = SyntheticAdversarialAIPopulation(human_similarity=0.2).canonical_weights
    strong = SyntheticAdversarialAIPopulation(human_similarity=0.95).canonical_weights
    assert total_variation_distance(human, strong) < total_variation_distance(human, weak)
    assert total_variation_distance(human, strong) < 0.05


def test_simulation_stratifies_each_session_across_families() -> None:
    generators = [SemanticGenerator(), VisualGenerator(), FreeChoiceGenerator()]
    challenges = [
        generator.generate(seed, DatasetSplit.DISCOVERY)
        for generator in generators
        for seed in range(4)
    ]
    records = simulate_experiment(
        challenges,
        [SyntheticHumanPopulation()],
        sessions_per_population=3,
        seed=1,
        study_version="test",
        split_policy=POLICY,
    )
    sessions = {record.session_id for record in records}
    for session_id in sessions:
        families = {
            record.challenge_family for record in records if record.session_id == session_id
        }
        assert families == {"SEM", "VIS", "FREE"}
