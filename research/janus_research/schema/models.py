from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class DatasetSplit(StrEnum):
    DISCOVERY = "discovery"
    VALIDATION = "validation"
    HOLDOUT = "holdout"


class PopulationClass(StrEnum):
    HUMAN = "human"
    AI = "ai"
    ADVERSARIAL_AI = "adversarial_ai"


class ParserStatus(StrEnum):
    OK = "ok"
    INVALID = "invalid"
    ERROR = "error"


class ManifestStatus(StrEnum):
    DRAFT = "draft"
    FROZEN = "frozen"
    COMPLETED = "completed"


class ConsentStatus(StrEnum):
    ACTIVE = "active"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class DecisionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_DECISION = "NEEDS_DECISION"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class Decision(StrEnum):
    HUMAN_COMPATIBLE = "HUMAN_COMPATIBLE"
    AI_COMPATIBLE = "AI_COMPATIBLE"
    UNKNOWN = "UNKNOWN"


class PublicChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    challenge_id: str
    family: str
    generator_version: str
    split: DatasetSplit
    public_payload: dict[str, Any]
    created_at: datetime


class ChallengeDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    challenge_id: str
    family: str
    generator_version: str
    seed: int
    split: DatasetSplit
    public_payload: dict[str, Any]
    private_features: dict[str, Any]
    created_at: datetime = Field(default_factory=utc_now)

    def to_public(self) -> PublicChallenge:
        """The sole normal public export path; private features are unrepresentable."""
        return PublicChallenge(
            challenge_id=self.challenge_id,
            family=self.family,
            generator_version=self.generator_version,
            split=self.split,
            public_payload=self.public_payload,
            created_at=self.created_at,
        )


class ResponseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    study_version: str
    subject_id: str = Field(min_length=3, max_length=128)
    population_class: PopulationClass
    model_version: str | None = None
    model_family: str | None = None
    condition: str
    session_id: str
    challenge_id: str
    challenge_family: str
    generator_version: str
    seed_reference: str
    sequence: int = Field(ge=0)
    public_option_order: list[str] = Field(min_length=2)
    response: str
    response_latency_bucket: str
    revision_count: int = Field(ge=0)
    input_modality: str
    timestamp: datetime = Field(default_factory=utc_now)
    split: DatasetSplit
    challenge_split: DatasetSplit
    temporal_wave: str = "T0"

    @model_validator(mode="after")
    def validate_population_metadata(self) -> Self:
        if self.population_class != PopulationClass.HUMAN and not self.model_version:
            raise ValueError("model_version is required for artificial populations")
        if self.response not in self.public_option_order:
            raise ValueError("response must be present in public_option_order")
        return self


class ModelRunMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_runtime: str
    model_identifier: str
    provider_reported_version: str | None = None
    run_at: datetime = Field(default_factory=utc_now)
    system_prompt_hash: str
    user_prompt_template_hash: str
    rendered_prompt_hash: str
    rendered_challenge_hash: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    seed: int | None = None
    retry_count: int = Field(default=0, ge=0)
    parser_status: ParserStatus
    error_state: str | None = None
    condition: str | None = None
    raw_response: str | None = None
    parsed_response: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)


class ModelCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    call_id: str
    experiment_id: str
    challenge_id: str
    challenge_family: str
    generator_version: str
    challenge_split: DatasetSplit
    public_option_order: list[str]
    condition: str
    sample_index: int = Field(ge=0)
    sequence: int = Field(ge=0)
    metadata: ModelRunMetadata
    completed_at: datetime = Field(default_factory=utc_now)


class ConsentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    consent_id: str
    subject_id: str = Field(min_length=3, max_length=128)
    study_version: str
    consent_document_version: str
    consented_at: datetime | None = None
    withdrawn_at: datetime | None = None
    status: ConsentStatus

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        if self.status == ConsentStatus.ACTIVE and self.consented_at is None:
            raise ValueError("active consent requires consented_at")
        if self.status == ConsentStatus.WITHDRAWN and self.withdrawn_at is None:
            raise ValueError("withdrawn consent requires withdrawn_at")
        return self


class ProviderTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    model_identifier: str
    credential_env: str
    enabled: bool = False
    provider_reported_version: str | None = None
    estimated_input_tokens: int | None = Field(default=None, ge=0)
    estimated_output_tokens: int | None = Field(default=None, ge=0)
    input_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)


class ExperimentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    experiment_id: str
    protocol_version: str
    hypothesis: str
    analysis_tier: str = "E"
    challenge_families: dict[str, str]
    human_split_policy: dict[str, float]
    challenge_split_policy: dict[str, float]
    model_split_policy: dict[str, float] | None = None
    temporal_wave: str = "T0"
    model_conditions: list[str]
    model_condition_parameters: dict[str, dict[str, float | None]] = Field(default_factory=dict)
    primary_metrics: list[str]
    random_seed: int
    challenge_count_per_family: int = Field(default=30, ge=3)
    synthetic_sessions_per_population: int = Field(default=60, ge=3)
    samples_per_challenge_per_condition: int = Field(default=1, ge=1)
    provider_targets: list[ProviderTarget] = Field(default_factory=list)
    consent_document_version: str | None = None
    retention_policy: str = "NEEDS_DECISION"
    max_model_calls_without_confirmation: int = Field(default=100, ge=1)
    exclusion_criteria: list[str] = Field(default_factory=list)
    abandonment_criteria: list[str] = Field(default_factory=list)
    threshold_selection_procedure: str = "exploratory_manifest_thresholds"
    pilot_decision_rules: dict[str, float] | None = None
    participant_target: int | None = Field(default=None, ge=1)
    sessions_per_participant: int | None = Field(default=None, ge=1)
    challenges_per_session: int | None = Field(default=None, ge=1)
    budget_cap_usd: float | None = Field(default=None, gt=0)
    launch_approvals: dict[str, DecisionStatus] = Field(default_factory=dict)
    scorer: dict[str, float] = Field(
        default_factory=lambda: {
            "smoothing": 1.0,
            "human_log_threshold": -2.0,
            "ai_log_threshold": 2.0,
        }
    )
    declared_human_fpr_target: float | None = Field(default=None, gt=0, lt=1)
    expected_ai_tpr: float | None = Field(default=None, gt=0, lt=1)
    attrition_allowance: float = Field(default=0.0, ge=0, lt=1)
    confirmatory: bool = False
    data_kind: str = "synthetic"
    status: ManifestStatus = ManifestStatus.DRAFT
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_frozen_hash(self) -> Self:
        if self.status != ManifestStatus.DRAFT and not self.content_hash:
            raise ValueError("frozen/completed manifests require content_hash")
        if self.confirmatory and self.data_kind == "synthetic":
            raise ValueError("synthetic experiments cannot be confirmatory")
        if self.data_kind == "real_exploratory" and not self.consent_document_version:
            raise ValueError("real human studies require a consent document version")
        return self

    def canonical_bytes(self, *, status: ManifestStatus | None = None) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        if status is not None:
            payload["status"] = status.value
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    def freeze(self, *, at: datetime | None = None) -> ExperimentManifest:
        if self.status != ManifestStatus.DRAFT:
            raise ValueError("only draft manifests can be frozen")
        frozen_at = at or utc_now()
        candidate = self.model_copy(
            update={"status": ManifestStatus.FROZEN, "updated_at": frozen_at, "content_hash": None}
        )
        digest = hashlib.sha256(candidate.canonical_bytes()).hexdigest()
        return candidate.model_copy(update={"content_hash": digest})

    def update_draft(self, **changes: Any) -> ExperimentManifest:
        if self.status != ManifestStatus.DRAFT:
            raise ValueError("frozen manifests are immutable; create a new experiment ID")
        changes["updated_at"] = utc_now()
        changes["content_hash"] = None
        return self.model_copy(update=changes)

    def verify_hash(self) -> bool:
        if not self.content_hash:
            return self.status == ManifestStatus.DRAFT
        candidate = self.model_copy(update={"content_hash": None})
        return hashlib.sha256(candidate.canonical_bytes()).hexdigest() == self.content_hash
