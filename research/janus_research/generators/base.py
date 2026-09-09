from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from janus_research.schema import ChallengeDefinition, DatasetSplit


def deterministic_id(version: str, seed: int, parameters: dict[str, Any]) -> str:
    material = json.dumps(
        {"version": version, "seed": seed, "parameters": parameters},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return f"{version.lower()}_{hashlib.sha256(material).hexdigest()[:20]}"


def deterministic_created_at(seed: int) -> datetime:
    """A reproducible provenance timestamp for generated research fixtures."""
    return datetime(2020, 1, 1, tzinfo=UTC) + timedelta(seconds=seed % 1_000_000_000)


class ChallengeGenerator(Protocol):
    family: str
    version: str

    def generate(
        self,
        seed: int,
        split: DatasetSplit,
        parameters: dict[str, Any] | None = None,
    ) -> ChallengeDefinition: ...
