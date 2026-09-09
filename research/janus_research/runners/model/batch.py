from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from janus_research.runners.model.base import ModelRunner
from janus_research.schema import (
    ChallengeDefinition,
    ExperimentManifest,
    ModelCallRecord,
    ParserStatus,
    PopulationClass,
    ProviderTarget,
    ResponseRecord,
)
from janus_research.splits import SplitAssigner
from janus_research.storage import write_responses


@dataclass(frozen=True)
class BatchPlan:
    models: tuple[str, ...]
    conditions: tuple[str, ...]
    challenges: int
    samples_per_challenge_per_condition: int
    estimated_calls: int
    estimated_input_tokens: int | None
    estimated_output_tokens: int | None
    estimated_cost: float | None


class CheckpointStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def records(self) -> dict[str, ModelCallRecord]:
        if not self.path.exists():
            return {}
        records: dict[str, ModelCallRecord] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = ModelCallRecord.model_validate_json(line)
                records[record.call_id] = record
        return records

    def append(self, record: ModelCallRecord) -> None:
        existing = self.records()
        if record.call_id in existing:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(record.model_dump_json() + "\n")


def _samples_for_condition(manifest: ExperimentManifest, condition: str) -> int:
    parameters = manifest.model_condition_parameters.get(condition, {})
    if parameters.get("temperature") == 0:
        return 1
    return manifest.samples_per_challenge_per_condition


def estimate_batch(
    manifest: ExperimentManifest, challenge_count: int, *, enabled_only: bool = False
) -> BatchPlan:
    targets = [target for target in manifest.provider_targets if target.enabled or not enabled_only]
    samples_across_conditions = sum(
        _samples_for_condition(manifest, condition) for condition in manifest.model_conditions
    )
    calls = len(targets) * challenge_count * samples_across_conditions
    input_tokens = 0
    output_tokens = 0
    cost = 0.0
    fully_estimated = bool(targets)
    for target in targets:
        target_calls = challenge_count * samples_across_conditions
        if target.estimated_input_tokens is None or target.estimated_output_tokens is None:
            fully_estimated = False
            continue
        input_tokens += target_calls * target.estimated_input_tokens
        output_tokens += target_calls * target.estimated_output_tokens
        if target.input_cost_per_million is None or target.output_cost_per_million is None:
            fully_estimated = False
            continue
        cost += target_calls * (
            target.estimated_input_tokens * target.input_cost_per_million / 1_000_000
            + target.estimated_output_tokens * target.output_cost_per_million / 1_000_000
        )
    return BatchPlan(
        models=tuple(f"{target.provider}:{target.model_identifier}" for target in targets),
        conditions=tuple(manifest.model_conditions),
        challenges=challenge_count,
        samples_per_challenge_per_condition=manifest.samples_per_challenge_per_condition,
        estimated_calls=calls,
        estimated_input_tokens=input_tokens if fully_estimated else None,
        estimated_output_tokens=output_tokens if fully_estimated else None,
        estimated_cost=cost if fully_estimated else None,
    )


def _run_id(manifest: ExperimentManifest) -> str:
    digest = manifest.content_hash or hashlib.sha256(manifest.canonical_bytes()).hexdigest()
    return f"{manifest.experiment_id}_{digest[:16]}"


def _call_id(
    run_id: str, target: ProviderTarget, condition: str, challenge_id: str, sample_index: int
) -> str:
    material = (
        f"{run_id}:{target.provider}:{target.model_identifier}:{condition}:"
        f"{challenge_id}:{sample_index}"
    )
    return hashlib.sha256(material.encode()).hexdigest()


def run_batch(
    manifest: ExperimentManifest,
    challenges: list[ChallengeDefinition],
    runners: Mapping[tuple[str, ...], ModelRunner],
    checkpoint: CheckpointStore,
    output_path: Path,
    *,
    approved_large_batch: bool = False,
) -> tuple[BatchPlan, list[ModelCallRecord]]:
    plan = estimate_batch(manifest, len(challenges), enabled_only=True)
    if (
        plan.estimated_calls > manifest.max_model_calls_without_confirmation
        and not approved_large_batch
    ):
        raise RuntimeError(
            f"batch has {plan.estimated_calls} calls; explicit large-batch confirmation required"
        )
    run_id = _run_id(manifest)
    completed = checkpoint.records()
    model_assigner = SplitAssigner(
        f"{manifest.experiment_id}:models",
        manifest.model_split_policy or manifest.human_split_policy,
    )
    sequence_by_family = {
        challenge.challenge_id: index for index, challenge in enumerate(challenges)
    }
    for target in [target for target in manifest.provider_targets if target.enabled]:
        for condition in manifest.model_conditions:
            runner = runners.get((target.provider, target.model_identifier, condition))
            if runner is None:
                runner = runners[(target.provider, target.model_identifier)]
            for sample_index in range(_samples_for_condition(manifest, condition)):
                for challenge in challenges:
                    call_id = _call_id(
                        run_id, target, condition, challenge.challenge_id, sample_index
                    )
                    if call_id in completed:
                        continue
                    response = runner.run(
                        challenge.to_public(), condition, seed=manifest.random_seed + sample_index
                    )
                    metadata = response.metadata.model_copy(
                        update={
                            "condition": response.metadata.condition or condition,
                            "parsed_response": response.metadata.parsed_response
                            or response.response,
                            "raw_response": response.metadata.raw_response or response.response,
                        }
                    )
                    record = ModelCallRecord(
                        run_id=run_id,
                        call_id=call_id,
                        experiment_id=manifest.experiment_id,
                        challenge_id=challenge.challenge_id,
                        challenge_family=challenge.family,
                        generator_version=challenge.generator_version,
                        challenge_split=challenge.split,
                        public_option_order=[
                            str(option["id"]) for option in challenge.public_payload["options"]
                        ],
                        condition=condition,
                        sample_index=sample_index,
                        sequence=sequence_by_family[challenge.challenge_id],
                        metadata=metadata,
                    )
                    checkpoint.append(record)
                    completed[call_id] = record
    ordered = sorted(completed.values(), key=lambda record: record.call_id)
    responses = []
    for record in ordered:
        if record.metadata.parser_status != ParserStatus.OK:
            continue
        target_key = f"{record.metadata.provider_runtime}:{record.metadata.model_identifier}"
        model_split = model_assigner.assign(target_key)
        session_material = f"{record.run_id}:{target_key}:{record.condition}:{record.sample_index}"
        responses.append(
            ResponseRecord(
                study_version=manifest.protocol_version,
                subject_id=hashlib.sha256(session_material.encode()).hexdigest()[:24],
                population_class=PopulationClass.AI,
                model_version=record.metadata.provider_reported_version
                or record.metadata.model_identifier,
                model_family=record.metadata.provider_runtime,
                condition=record.condition,
                session_id=hashlib.sha256(session_material.encode()).hexdigest()[:20],
                challenge_id=record.challenge_id,
                challenge_family=record.challenge_family,
                generator_version=record.generator_version,
                seed_reference=hashlib.sha256(record.challenge_id.encode()).hexdigest()[:16],
                sequence=record.sequence,
                public_option_order=record.public_option_order,
                response=record.metadata.parsed_response or "",
                response_latency_bucket="provider_call",
                revision_count=0,
                input_modality="model_api",
                split=model_split,
                challenge_split=record.challenge_split,
                temporal_wave=manifest.temporal_wave,
            )
        )
    if responses:
        write_responses(responses, output_path)
    return plan, ordered
