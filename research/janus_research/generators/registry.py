from __future__ import annotations

from dataclasses import dataclass

from janus_research.generators.base import ChallengeGenerator
from janus_research.generators.free_choice import FreeChoiceGenerator
from janus_research.generators.semantic import SemanticGenerator
from janus_research.generators.visual import VisualGenerator


@dataclass(frozen=True)
class GeneratorRegistry:
    generators: dict[str, ChallengeGenerator]

    def get(self, version: str) -> ChallengeGenerator:
        try:
            return self.generators[version]
        except KeyError as error:
            raise ValueError(f"unknown generator version: {version}") from error


def default_registry() -> GeneratorRegistry:
    generators: list[ChallengeGenerator] = [
        SemanticGenerator(),
        VisualGenerator(),
        FreeChoiceGenerator(),
    ]
    return GeneratorRegistry({generator.version: generator for generator in generators})
