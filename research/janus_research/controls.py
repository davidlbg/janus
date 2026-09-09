from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from janus_research.metrics.core import total_variation_distance


@dataclass(frozen=True)
class ControlResult:
    label: str
    positive_tv: float
    negative_tv: float
    positive_pass: bool
    negative_pass: bool
    pipeline_valid: bool


def run_controls(seed: int, draws: int = 10_000) -> ControlResult:
    rng = np.random.default_rng(seed)
    baseline = np.array([0.4, 0.3, 0.2, 0.1])
    separated = np.array([0.1, 0.2, 0.3, 0.4])
    first = rng.multinomial(draws, baseline)
    positive = rng.multinomial(draws, separated)
    identical = rng.multinomial(draws, baseline)
    positive_tv = total_variation_distance(first.tolist(), positive.tolist())
    negative_tv = total_variation_distance(first.tolist(), identical.tolist())
    positive_pass = positive_tv >= 0.20
    negative_pass = negative_tv <= 0.04
    return ControlResult(
        label="CONTROL — NOT REAL DATA",
        positive_tv=positive_tv,
        negative_tv=negative_tv,
        positive_pass=positive_pass,
        negative_pass=negative_pass,
        pipeline_valid=positive_pass and negative_pass,
    )


def write_controls(
    result: ControlResult,
    directory: Path,
    provenance: dict[str, str] | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "controls.json"
    payload = {**asdict(result), "provenance": provenance or {}}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path
