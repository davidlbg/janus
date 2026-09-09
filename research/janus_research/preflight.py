from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum

from janus_research.audit import audit_challenges, generate_audit_set
from janus_research.controls import run_controls
from janus_research.schema import DecisionStatus, ExperimentManifest, ManifestStatus


class CheckStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    WARNING = "WARNING"


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    status: CheckStatus
    detail: str


@dataclass(frozen=True)
class PreflightReport:
    experiment_id: str
    status: CheckStatus
    checks: tuple[PreflightCheck, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "status": self.status.value,
            "checks": [asdict(check) for check in self.checks],
        }


def _approved(manifest: ExperimentManifest, key: str) -> bool:
    return manifest.launch_approvals.get(key) == DecisionStatus.APPROVED


def _resolved(value: str | None) -> bool:
    return bool(value and "NEEDS_" not in value)


def run_preflight(
    manifest: ExperimentManifest,
    *,
    environment: Mapping[str, str],
    test_runner: Callable[[], bool],
) -> PreflightReport:
    checks: list[PreflightCheck] = []

    def add(name: str, passed: bool, pass_detail: str, blocked_detail: str) -> None:
        checks.append(
            PreflightCheck(
                name,
                CheckStatus.PASS if passed else CheckStatus.BLOCKED,
                pass_detail if passed else blocked_detail,
            )
        )

    add(
        "consent version approved",
        _approved(manifest, "consent") and _resolved(manifest.consent_document_version),
        f"approved document {manifest.consent_document_version}",
        "consent draft still requires human/legal/privacy/ethics review",
    )
    add(
        "retention decided",
        _approved(manifest, "retention") and _resolved(manifest.retention_policy),
        manifest.retention_policy,
        "retention behavior exists technically but research policy is not approved",
    )
    add(
        "recruitment decided",
        _approved(manifest, "recruitment"),
        "recruitment policy approved",
        "recruitment source, eligibility and compensation are unresolved",
    )
    selected_targets = [
        target
        for target in manifest.provider_targets
        if target.enabled and _resolved(target.model_identifier)
    ]
    add(
        "models selected",
        _approved(manifest, "models") and len(selected_targets) >= 2,
        f"{len(selected_targets)} enabled provider targets selected",
        "two enabled, explicitly approved model targets are required",
    )
    missing_credentials = [
        target.credential_env
        for target in selected_targets
        if not environment.get(target.credential_env)
    ]
    add(
        "credentials available",
        len(selected_targets) >= 2 and not missing_credentials,
        "required environment variables are present (values not inspected or printed)",
        "provider credentials cannot be verified until targets are selected and variables exist",
    )
    add(
        "model modalities compatible",
        _approved(manifest, "model_modalities") and len(selected_targets) >= 2,
        "stimulus representation reviewed for every selected provider",
        "VIS_v1 human-rendered SVG versus provider input representation needs explicit review",
    )
    condition_parameters_ready = all(
        condition in manifest.model_condition_parameters for condition in ("M0", "M1", "M2")
    )
    add(
        "model conditions approved",
        _approved(manifest, "model_conditions")
        and {"M0", "M1", "M2"}.issubset(manifest.model_conditions)
        and condition_parameters_ready,
        "M0/M1/M2 and provider decoding review approved",
        "primary conditions or provider-specific decoding behavior remain unresolved",
    )
    sample_ready = all(
        value is not None
        for value in (
            manifest.participant_target,
            manifest.sessions_per_participant,
            manifest.challenges_per_session,
        )
    )
    add(
        "sample plan approved",
        _approved(manifest, "human_sample") and _approved(manifest, "sampling") and sample_ready,
        "human and model sampling plan approved",
        "participant/session/challenge counts and model sampling are unresolved",
    )
    add(
        "budget cap approved",
        _approved(manifest, "budget") and manifest.budget_cap_usd is not None,
        f"maximum spend USD {manifest.budget_cap_usd}",
        "provider budget cap is unresolved",
    )
    add(
        "exclusions approved",
        _approved(manifest, "exclusions")
        and bool(manifest.exclusion_criteria)
        and all(_resolved(item) for item in manifest.exclusion_criteria),
        "pre-analysis exclusions approved",
        "exclusion criteria remain unresolved",
    )
    add(
        "decision rules approved",
        _approved(manifest, "decision_rules") and manifest.pilot_decision_rules is not None,
        "pilot decision thresholds approved",
        "PROMISING/INCONCLUSIVE/NOT SUPPORTED rules remain unresolved",
    )
    add(
        "stopping rules approved",
        _approved(manifest, "stopping_rules")
        and bool(manifest.abandonment_criteria)
        and all(_resolved(item) for item in manifest.abandonment_criteria),
        "technical, financial and scientific stopping rules approved",
        "stopping rules remain unresolved",
    )
    add(
        "manifest reviewed",
        _approved(manifest, "manifest_review"),
        "manifest review recorded",
        "owner has not recorded manifest approval",
    )
    add(
        "manifest frozen",
        manifest.status == ManifestStatus.FROZEN and manifest.verify_hash(),
        f"frozen manifest hash {manifest.content_hash}",
        "manifest is draft; freezing remains an explicit human action",
    )
    audit = audit_challenges(generate_audit_set(manifest))
    add(
        "challenge audit passing",
        audit.status == "PASS",
        f"{audit.challenge_count} generated challenges audited",
        "challenge audit failed; collection must not begin",
    )
    controls = run_controls(manifest.random_seed)
    add(
        "controls passing",
        controls.pipeline_valid,
        f"positive TV={controls.positive_tv:.4f}; negative TV={controls.negative_tv:.4f}",
        "positive or negative pipeline control failed",
    )
    add(
        "test suite passing",
        test_runner(),
        "local test suite passed in this preflight invocation",
        "local test suite failed or could not run",
    )
    checks.append(
        PreflightCheck(
            "exploratory scope",
            CheckStatus.WARNING,
            "EXP001A cannot establish production FPR or adversarial CAPTCHA security",
        )
    )
    overall = (
        CheckStatus.BLOCKED
        if any(check.status == CheckStatus.BLOCKED for check in checks)
        else CheckStatus.PASS
    )
    return PreflightReport(manifest.experiment_id, overall, tuple(checks))
