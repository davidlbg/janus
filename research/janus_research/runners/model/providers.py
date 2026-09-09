from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from janus_research.runners.model.base import ModelResponse
from janus_research.runners.model.conditions import render_condition_prompt
from janus_research.schema import ModelRunMetadata, ParserStatus, PublicChallenge


class JsonTransport(Protocol):
    def post(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]: ...


class UrlLibJsonTransport:
    def post(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode())


@dataclass(frozen=True)
class ProviderConfig:
    model_identifier: str
    credential_env: str
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int = 16
    timeout_seconds: float = 60.0
    max_retries: int = 2


class ProviderRunnerBase:
    provider_name: str
    endpoint: str
    supports_seed = False

    def __init__(self, config: ProviderConfig, transport: JsonTransport | None = None) -> None:
        self.config = config
        self.transport = transport or UrlLibJsonTransport()

    def _credential(self) -> str:
        value = os.environ.get(self.config.credential_env)
        if not value:
            raise RuntimeError(
                f"missing provider credential environment variable {self.config.credential_env}"
            )
        return value

    def _headers(self, credential: str) -> dict[str, str]:
        raise NotImplementedError

    def _payload(self, prompt: str, seed: int | None) -> dict[str, Any]:
        raise NotImplementedError

    def _extract(self, response: dict[str, Any]) -> tuple[str, str | None]:
        raise NotImplementedError

    def run(
        self, challenge: PublicChallenge, condition: str, *, seed: int | None = None
    ) -> ModelResponse:
        rendered, template_hash = render_condition_prompt(condition, challenge)
        challenge_json = json.dumps(challenge.model_dump(mode="json"), sort_keys=True)
        started = time.perf_counter()
        raw_response: str | None = None
        parsed: str | None = None
        provider_version: str | None = None
        error_state: str | None = None
        retry_count = 0
        try:
            credential = self._credential()
            for attempt in range(self.config.max_retries + 1):
                retry_count = attempt
                try:
                    response = self.transport.post(
                        self.endpoint,
                        self._headers(credential),
                        self._payload(rendered, seed),
                        self.config.timeout_seconds,
                    )
                    raw_response, provider_version = self._extract(response)
                    break
                except (
                    OSError,
                    TimeoutError,
                    urllib.error.URLError,
                    ValueError,
                    KeyError,
                ) as error:
                    error_state = f"{type(error).__name__}: {error}"
                    if attempt == self.config.max_retries:
                        break
            valid_options = {str(option["id"]) for option in challenge.public_payload["options"]}
            candidate = (raw_response or "").strip()
            parsed = candidate if candidate in valid_options else None
            if raw_response is not None and parsed is None and error_state is None:
                error_state = "provider output did not parse to exactly one public option ID"
        except RuntimeError as error:
            error_state = str(error)
        status = (
            ParserStatus.OK
            if parsed is not None
            else ParserStatus.ERROR
            if raw_response is None
            else ParserStatus.INVALID
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        metadata = ModelRunMetadata(
            provider_runtime=self.provider_name,
            model_identifier=self.config.model_identifier,
            provider_reported_version=provider_version,
            system_prompt_hash=hashlib.sha256(b"").hexdigest(),
            user_prompt_template_hash=template_hash,
            rendered_prompt_hash=hashlib.sha256(rendered.encode()).hexdigest(),
            rendered_challenge_hash=hashlib.sha256(challenge_json.encode()).hexdigest(),
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            seed=seed if self.supports_seed else None,
            retry_count=retry_count,
            parser_status=status,
            error_state=error_state,
            condition=condition,
            raw_response=raw_response,
            parsed_response=parsed,
            latency_ms=latency_ms,
        )
        return ModelResponse(parsed, rendered, metadata)


class OpenAIResponsesRunner(ProviderRunnerBase):
    provider_name = "openai_responses"
    endpoint = "https://api.openai.com/v1/responses"

    def _headers(self, credential: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {credential}"}

    def _payload(self, prompt: str, seed: int | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model_identifier,
            "input": prompt,
            "max_output_tokens": self.config.max_output_tokens,
            "store": False,
        }
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        if self.config.top_p is not None:
            payload["top_p"] = self.config.top_p
        return payload

    def _extract(self, response: dict[str, Any]) -> tuple[str, str | None]:
        if isinstance(response.get("output_text"), str):
            return response["output_text"], response.get("model")
        texts = [
            content.get("text", "")
            for output in response.get("output", [])
            for content in output.get("content", [])
            if content.get("type") == "output_text"
        ]
        if not texts:
            raise ValueError("response contains no output text")
        return "".join(texts), response.get("model")


class AnthropicMessagesRunner(ProviderRunnerBase):
    provider_name = "anthropic_messages"
    endpoint = "https://api.anthropic.com/v1/messages"

    def _headers(self, credential: str) -> dict[str, str]:
        return {"x-api-key": credential, "anthropic-version": "2023-06-01"}

    def _payload(self, prompt: str, seed: int | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model_identifier,
            "max_tokens": self.config.max_output_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        if self.config.top_p is not None:
            payload["top_p"] = self.config.top_p
        return payload

    def _extract(self, response: dict[str, Any]) -> tuple[str, str | None]:
        texts = [
            block.get("text", "")
            for block in response.get("content", [])
            if block.get("type") == "text"
        ]
        if not texts:
            raise ValueError("message contains no text content")
        return "".join(texts), response.get("model")


def build_provider_runner(
    provider: str, config: ProviderConfig, transport: JsonTransport | None = None
) -> ProviderRunnerBase:
    if provider == "openai_responses":
        return OpenAIResponsesRunner(config, transport)
    if provider == "anthropic_messages":
        return AnthropicMessagesRunner(config, transport)
    raise ValueError(f"unsupported provider adapter: {provider}")
