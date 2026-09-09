from __future__ import annotations

import random
from typing import Any

from janus_research.generators.base import deterministic_created_at, deterministic_id
from janus_research.schema import ChallengeDefinition, DatasetSplit

SEMANTIC_SETS = (
    {
        "anchor": "garden",
        "items": (
            ("leaf", "plant"),
            ("stone", "material"),
            ("rain", "weather"),
            ("bench", "object"),
        ),
    },
    {
        "anchor": "journey",
        "items": (
            ("path", "route"),
            ("bridge", "structure"),
            ("map", "representation"),
            ("cloud", "environment"),
        ),
    },
    {
        "anchor": "morning",
        "items": (("window", "place"), ("tea", "drink"), ("bird", "animal"), ("shadow", "light")),
    },
    {
        "anchor": "workshop",
        "items": (
            ("paper", "material"),
            ("wheel", "mechanism"),
            ("lamp", "object"),
            ("thread", "material"),
        ),
    },
)


class SemanticGenerator:
    family = "SEM"
    version = "SEM_v1"

    def generate(
        self,
        seed: int,
        split: DatasetSplit,
        parameters: dict[str, Any] | None = None,
    ) -> ChallengeDefinition:
        params = parameters or {}
        rng = random.Random(f"{self.version}:{seed}:{sorted(params.items())}")
        semantic_set = SEMANTIC_SETS[rng.randrange(len(SEMANTIC_SETS))]
        entries = [
            {"id": f"o{index + 1}", "label": label, "relation": relation}
            for index, (label, relation) in enumerate(semantic_set["items"])
        ]
        rng.shuffle(entries)
        challenge_id = deterministic_id(self.version, seed, params)
        return ChallengeDefinition(
            challenge_id=challenge_id,
            family=self.family,
            generator_version=self.version,
            seed=seed,
            split=split,
            public_payload={
                "instruction": "Choose the item that feels least related.",
                "context": semantic_set["anchor"],
                "options": [{"id": item["id"], "label": item["label"]} for item in entries],
            },
            private_features={
                "anchor": semantic_set["anchor"],
                "relations_by_option": {item["id"]: item["relation"] for item in entries},
                "hypothesis_tags": ["semantic_salience", "ambiguity_resolution"],
            },
            created_at=deterministic_created_at(seed),
        )
