from __future__ import annotations

import html
import random
from typing import Any, TypedDict

from janus_research.generators.base import deterministic_created_at, deterministic_id
from janus_research.schema import ChallengeDefinition, DatasetSplit

SHAPES = ("circle", "square", "triangle", "diamond")
COLORS = ("#1f2937", "#1d4ed8", "#9a3412", "#166534")


class VisualSpec(TypedDict):
    id: str
    shape: str
    color: str
    scale: float
    rotation: int
    repeats: int


def _shape_svg(shape: str, color: str, scale: float, rotation: int, repeats: int) -> str:
    primitives: list[str] = []
    for index in range(repeats):
        x = 35 + (index % 2) * 30
        y = 35 + (index // 2) * 30
        size = 14 * scale
        transform = f' transform="rotate({rotation} {x} {y})"'
        if shape == "circle":
            primitives.append(f'<circle cx="{x}" cy="{y}" r="{size / 2:.2f}" fill="{color}"/>')
        elif shape == "square":
            primitives.append(
                f'<rect x="{x - size / 2:.2f}" y="{y - size / 2:.2f}" width="{size:.2f}" '
                f'height="{size:.2f}" rx="2" fill="{color}"{transform}/>'
            )
        elif shape == "triangle":
            points = (
                f"{x},{y - size / 2:.2f} "
                f"{x - size / 2:.2f},{y + size / 2:.2f} "
                f"{x + size / 2:.2f},{y + size / 2:.2f}"
            )
            primitives.append(f'<polygon points="{points}" fill="{color}"{transform}/>')
        else:
            points = (
                f"{x},{y - size / 2:.2f} {x + size / 2:.2f},{y} "
                f"{x},{y + size / 2:.2f} {x - size / 2:.2f},{y}"
            )
            primitives.append(f'<polygon points="{points}" fill="{color}"{transform}/>')
    label = html.escape(f"Abstract {shape} composition")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        f'role="img" aria-label="{label}"><rect width="100" height="100" fill="#f8fafc"/>'
        + "".join(primitives)
        + "</svg>"
    )


class VisualGenerator:
    family = "VIS"
    version = "VIS_v1"

    def generate(
        self,
        seed: int,
        split: DatasetSplit,
        parameters: dict[str, Any] | None = None,
    ) -> ChallengeDefinition:
        params = parameters or {}
        rng = random.Random(f"{self.version}:{seed}:{sorted(params.items())}")
        option_specs: list[VisualSpec] = []
        for index, shape in enumerate(SHAPES):
            spec: VisualSpec = {
                "id": f"o{index + 1}",
                "shape": shape,
                "color": COLORS[(index + seed) % len(COLORS)],
                "scale": float(rng.choice((0.85, 1.0, 1.15))),
                "rotation": int(rng.choice((0, 15, 30, 45))),
                "repeats": int(rng.choice((1, 2, 3, 4))),
            }
            option_specs.append(spec)
        rng.shuffle(option_specs)
        public_options = [
            {
                "id": spec["id"],
                "label": f"Composition {index + 1}",
                "svg": _shape_svg(
                    spec["shape"],
                    spec["color"],
                    spec["scale"],
                    spec["rotation"],
                    spec["repeats"],
                ),
            }
            for index, spec in enumerate(option_specs)
        ]
        return ChallengeDefinition(
            challenge_id=deterministic_id(self.version, seed, params),
            family=self.family,
            generator_version=self.version,
            seed=seed,
            split=split,
            public_payload={
                "instruction": "Which composition catches your attention first?",
                "options": public_options,
            },
            private_features={
                "features_by_option": {
                    spec["id"]: {k: v for k, v in spec.items() if k != "id"}
                    for spec in option_specs
                },
                "hypothesis_tags": ["visual_salience", "symmetry", "repetition", "orientation"],
            },
            created_at=deterministic_created_at(seed),
        )
