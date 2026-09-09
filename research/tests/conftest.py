from __future__ import annotations

from datetime import UTC, datetime

import pytest

from janus_research.generators import SemanticGenerator
from janus_research.schema import DatasetSplit, PopulationClass, ResponseRecord


@pytest.fixture
def challenge():
    return SemanticGenerator().generate(123, DatasetSplit.DISCOVERY)


def make_response(
    challenge,
    population: PopulationClass,
    response: str,
    *,
    session_id: str,
    split: DatasetSplit = DatasetSplit.DISCOVERY,
    condition: str = "HUMAN",
) -> ResponseRecord:
    options = [option["id"] for option in challenge.public_payload["options"]]
    return ResponseRecord(
        study_version="0.1",
        subject_id=f"subject-{session_id}",
        population_class=population,
        model_version=None if population == PopulationClass.HUMAN else "model-v1",
        model_family=None if population == PopulationClass.HUMAN else "model-family",
        condition=condition,
        session_id=session_id,
        challenge_id=challenge.challenge_id,
        challenge_family=challenge.family,
        generator_version=challenge.generator_version,
        seed_reference="seed-hash",
        sequence=0,
        public_option_order=options,
        response=response,
        response_latency_bucket="500-1500",
        revision_count=0,
        input_modality="keyboard",
        timestamp=datetime.now(UTC),
        split=split,
        challenge_split=split,
    )
