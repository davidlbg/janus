from __future__ import annotations

import random
from typing import Any

from janus_research.generators.base import deterministic_created_at, deterministic_id
from janus_research.schema import ChallengeDefinition, DatasetSplit


def _pattern_svg(stroke: str, density: int, curvature: int, symmetry: bool) -> str:
    paths = []
    for index in range(density):
        offset = 16 + index * (68 / max(density - 1, 1))
        control = 50 + (curvature if index % 2 else -curvature)
        paths.append(
            f'<path d="M 10 {offset:.1f} Q 50 {control:.1f} 90 {100 - offset:.1f}" '
            f'fill="none" stroke="{stroke}" stroke-width="4" stroke-linecap="round"/>'
        )
        if symmetry:
            paths.append(
                f'<path d="M {offset:.1f} 10 Q {control:.1f} 50 {100 - offset:.1f} 90" '
                f'fill="none" stroke="{stroke}" stroke-width="3" stroke-linecap="round"/>'
            )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        'role="img" aria-label="Abstract line pattern">'
        '<rect width="100" height="100" fill="#f8fafc"/>' + "".join(paths) + "</svg>"
    )


class FreeChoiceGenerator:
    family = "FREE"
    version = "FREE_v1"

    def generate(
        self,
        seed: int,
        split: DatasetSplit,
        parameters: dict[str, Any] | None = None,
    ) -> ChallengeDefinition:
        params = parameters or {}
        rng = random.Random(f"{self.version}:{seed}:{sorted(params.items())}")
        palette = ("#334155", "#1e40af", "#9f1239", "#3f6212")
        specs = []
        for index in range(4):
            specs.append(
                {
                    "id": f"o{index + 1}",
                    "stroke": palette[(index + seed) % len(palette)],
                    "density": rng.choice((2, 3, 4)),
                    "curvature": rng.choice((10, 20, 30)),
                    "symmetry": bool(rng.getrandbits(1)),
                }
            )
        rng.shuffle(specs)
        return ChallengeDefinition(
            challenge_id=deterministic_id(self.version, seed, params),
            family=self.family,
            generator_version=self.version,
            seed=seed,
            split=split,
            public_payload={
                "instruction": "Choose whichever pattern you prefer.",
                "options": [
                    {
                        "id": spec["id"],
                        "label": f"Pattern {index + 1}",
                        "svg": _pattern_svg(
                            str(spec["stroke"]),
                            int(spec["density"]),
                            int(spec["curvature"]),
                            bool(spec["symmetry"]),
                        ),
                    }
                    for index, spec in enumerate(specs)
                ],
            },
            private_features={
                "features_by_option": {
                    spec["id"]: {k: v for k, v in spec.items() if k != "id"} for spec in specs
                },
                "hypothesis_tags": ["free_preference", "structural_balance"],
            },
            created_at=deterministic_created_at(seed),
        )
