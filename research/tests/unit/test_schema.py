from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from janus_research.schema import ExperimentManifest, PopulationClass, ResponseRecord


def test_public_export_cannot_contain_private_features(challenge) -> None:
    payload = challenge.to_public().model_dump(mode="json")
    assert "private_features" not in payload
    assert "private_features" not in json.dumps(payload)
    with pytest.raises(ValidationError):
        challenge.to_public().__class__.model_validate(
            {**payload, "private_features": {"secret": 1}}
        )


def test_artificial_response_requires_model_version(challenge) -> None:
    options = [option["id"] for option in challenge.public_payload["options"]]
    with pytest.raises(ValidationError, match="model_version"):
        ResponseRecord(
            study_version="0.1",
            subject_id="agent-1",
            population_class=PopulationClass.AI,
            condition="M0",
            session_id="s1",
            challenge_id=challenge.challenge_id,
            challenge_family=challenge.family,
            generator_version=challenge.generator_version,
            seed_reference="hash",
            sequence=0,
            public_option_order=options,
            response=options[0],
            response_latency_bucket="0-500",
            revision_count=0,
            input_modality="api",
            split="discovery",
            challenge_split="discovery",
        )


def test_frozen_manifest_rejects_project_api_mutation() -> None:
    manifest = ExperimentManifest(
        experiment_id="test",
        protocol_version="0.1",
        hypothesis="H1",
        challenge_families={"SEM": "SEM_v1"},
        human_split_policy={"discovery": 0.6, "validation": 0.3, "holdout": 0.1},
        challenge_split_policy={"discovery": 0.6, "validation": 0.3, "holdout": 0.1},
        model_conditions=["M0"],
        primary_metrics=["jsd"],
        random_seed=1,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    frozen = manifest.freeze(at=datetime(2026, 1, 2, tzinfo=UTC))
    assert frozen.verify_hash()
    with pytest.raises(ValueError, match="immutable"):
        frozen.update_draft(hypothesis="changed")


def test_synthetic_cannot_be_confirmatory() -> None:
    with pytest.raises(ValidationError, match="cannot be confirmatory"):
        ExperimentManifest(
            experiment_id="bad",
            protocol_version="0.1",
            hypothesis="H1",
            challenge_families={"SEM": "SEM_v1"},
            human_split_policy={"discovery": 0.6, "validation": 0.3, "holdout": 0.1},
            challenge_split_policy={"discovery": 0.6, "validation": 0.3, "holdout": 0.1},
            model_conditions=["M0"],
            primary_metrics=["jsd"],
            random_seed=1,
            confirmatory=True,
            data_kind="synthetic",
        )
