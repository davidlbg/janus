from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from janus_research.schema import DatasetSplit


def _validate_proportions(proportions: dict[str, float]) -> None:
    expected = {split.value for split in DatasetSplit}
    if set(proportions) != expected:
        raise ValueError(f"split policy must contain exactly {sorted(expected)}")
    if any(value < 0 for value in proportions.values()):
        raise ValueError("split proportions cannot be negative")
    if abs(sum(proportions.values()) - 1.0) > 1e-9:
        raise ValueError("split proportions must sum to 1")


@dataclass
class SplitAssigner:
    namespace: str
    proportions: dict[str, float]
    _assignments: dict[str, DatasetSplit] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_proportions(self.proportions)

    def assign(self, identifier: str) -> DatasetSplit:
        if not identifier:
            raise ValueError("identifier cannot be empty")
        existing = self._assignments.get(identifier)
        if existing is not None:
            return existing
        digest = hashlib.sha256(f"{self.namespace}:{identifier}".encode()).digest()
        point = int.from_bytes(digest[:8], "big") / 2**64
        cumulative = 0.0
        assigned = DatasetSplit.HOLDOUT
        for split in DatasetSplit:
            cumulative += self.proportions[split.value]
            if point < cumulative:
                assigned = split
                break
        self._assignments[identifier] = assigned
        return assigned

    @property
    def assignments(self) -> dict[str, DatasetSplit]:
        return dict(self._assignments)


def assert_disjoint_assignments(assignments: dict[DatasetSplit, set[str]]) -> None:
    seen: set[str] = set()
    for split, identifiers in assignments.items():
        overlap = seen.intersection(identifiers)
        if overlap:
            raise ValueError(f"identifiers overlap at split {split}: {sorted(overlap)}")
        seen.update(identifiers)
