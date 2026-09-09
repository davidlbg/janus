from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from janus_research.runners.model.conditions import render_condition_prompt
from janus_research.schema import ModelRunMetadata, ParserStatus, PublicChallenge


@dataclass(frozen=True)
class ModelResponse:
    response: str | None
    rendered_prompt: str
    metadata: ModelRunMetadata


class ModelRunner(Protocol):
    def run(
        self, challenge: PublicChallenge, condition: str, *, seed: int | None = None
    ) -> ModelResponse: ...


class MockModelRunner:
    def __init__(self, model_identifier: str = "mock-model-v1") -> None:
        self.model_identifier = model_identifier

    def run(
        self, challenge: PublicChallenge, condition: str, *, seed: int | None = None
    ) -> ModelResponse:
        rendered, template_hash = render_condition_prompt(condition, challenge)
        options = [str(option["id"]) for option in challenge.public_payload["options"]]
        material = f"{self.model_identifier}:{condition}:{challenge.challenge_id}:{seed}"
        response = options[int(hashlib.sha256(material.encode()).hexdigest(), 16) % len(options)]
        metadata = ModelRunMetadata(
            provider_runtime="local/mock",
            model_identifier=self.model_identifier,
            system_prompt_hash=hashlib.sha256(b"").hexdigest(),
            user_prompt_template_hash=template_hash,
            rendered_prompt_hash=hashlib.sha256(rendered.encode()).hexdigest(),
            seed=seed,
            parser_status=ParserStatus.OK,
        )
        return ModelResponse(response, rendered, metadata)


class FixtureModelRunner:
    def __init__(
        self, responses: dict[tuple[str, str], str], model_identifier: str = "fixture-v1"
    ) -> None:
        self.responses = responses
        self.model_identifier = model_identifier

    def run(
        self, challenge: PublicChallenge, condition: str, *, seed: int | None = None
    ) -> ModelResponse:
        rendered, template_hash = render_condition_prompt(condition, challenge)
        response = self.responses.get((challenge.challenge_id, condition))
        valid = {str(option["id"]) for option in challenge.public_payload["options"]}
        status = ParserStatus.OK if response in valid else ParserStatus.INVALID
        metadata = ModelRunMetadata(
            provider_runtime="local/fixture",
            model_identifier=self.model_identifier,
            system_prompt_hash=hashlib.sha256(b"").hexdigest(),
            user_prompt_template_hash=template_hash,
            rendered_prompt_hash=hashlib.sha256(rendered.encode()).hexdigest(),
            seed=seed,
            parser_status=status,
            error_state=None
            if status == ParserStatus.OK
            else "missing or invalid fixture response",
        )
        return ModelResponse(response if status == ParserStatus.OK else None, rendered, metadata)
