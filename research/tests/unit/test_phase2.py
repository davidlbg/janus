from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import make_response

from janus_research.audit import audit_challenges
from janus_research.consent import ConsentRequiredError, ConsentStore
from janus_research.controls import run_controls
from janus_research.evaluation import cross_model_transfer, option_position_probe
from janus_research.manifest import load_manifest
from janus_research.pipeline import RESEARCH_ROOT
from janus_research.preflight import CheckStatus, run_preflight
from janus_research.proposal import propose_confirmatory
from janus_research.provenance import report_label
from janus_research.runners.human.server import StudyState
from janus_research.runners.model import MockModelRunner, OpenAIResponsesRunner, ProviderConfig
from janus_research.runners.model.batch import CheckpointStore, run_batch
from janus_research.schema import DatasetSplit, ManifestStatus, PopulationClass


class FakeTransport:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response

    def post(
        self, url: str, headers: dict[str, str], payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]:
        return self.response


def test_response_requires_consent_and_withdrawal_blocks_collection(
    tmp_path: Path, challenge
) -> None:
    store = ConsentStore(tmp_path, "pilot", "preserve_pending_review")
    state = StudyState(
        "pilot",
        "0.2",
        "subject-001",
        DatasetSplit.DISCOVERY,
        [challenge],
        tmp_path / "responses.parquet",
        store,
        "reviewed-v1",
    )
    option = challenge.public_payload["options"][0]["id"]
    with pytest.raises(ConsentRequiredError):
        state.submit(option, 0, "keyboard")
    store.consent("subject-001", "0.2", "reviewed-v1")
    store.withdraw("subject-001")
    with pytest.raises(ConsentRequiredError):
        state.submit(option, 0, "keyboard")


def test_provider_metadata_is_preserved(monkeypatch: pytest.MonkeyPatch, challenge) -> None:
    monkeypatch.setenv("TEST_PROVIDER_KEY", "not-a-real-key")
    option = challenge.public_payload["options"][0]["id"]
    runner = OpenAIResponsesRunner(
        ProviderConfig("provider-model", "TEST_PROVIDER_KEY", temperature=0.7, top_p=0.9),
        FakeTransport({"output_text": option, "model": "provider-model-2026-01"}),
    )
    response = runner.run(challenge.to_public(), "M1", seed=42)
    assert response.metadata.provider_reported_version == "provider-model-2026-01"
    assert response.metadata.raw_response == option
    assert response.metadata.parsed_response == option
    assert response.metadata.temperature == 0.7
    assert response.metadata.seed is None
    assert response.metadata.rendered_challenge_hash


def test_resume_does_not_duplicate_calls(tmp_path: Path, challenge) -> None:
    manifest = load_manifest(
        RESEARCH_ROOT / "experiments" / "manifests" / "exp001a_real_signal_pilot.yaml"
    )
    target = manifest.provider_targets[0].model_copy(
        update={"enabled": True, "model_identifier": "mock"}
    )
    manifest = manifest.model_copy(
        update={
            "provider_targets": [target],
            "model_conditions": ["M1"],
            "samples_per_challenge_per_condition": 2,
            "max_model_calls_without_confirmation": 10,
        }
    )
    checkpoint = CheckpointStore(tmp_path / "checkpoint.jsonl")
    runners = {(target.provider, target.model_identifier): MockModelRunner("mock")}
    _, first = run_batch(manifest, [challenge], runners, checkpoint, tmp_path / "responses.parquet")
    _, second = run_batch(
        manifest, [challenge], runners, checkpoint, tmp_path / "responses.parquet"
    )
    assert len(first) == len(second) == 2
    assert len({record.call_id for record in second}) == 2


def test_controls_and_option_position_probe(challenge) -> None:
    assert run_controls(123).pipeline_valid
    options = [option["id"] for option in challenge.public_payload["options"]]
    records = []
    for index in range(30):
        population = PopulationClass.HUMAN if index < 15 else PopulationClass.AI
        response = options[0] if population == PopulationClass.HUMAN else options[-1]
        records.append(make_response(challenge, population, response, session_id=f"s{index}"))
    assert option_position_probe(records)["flagged"] is True


def test_cross_model_matrix_holds_out_entire_model_family(challenge) -> None:
    options = [option["id"] for option in challenge.public_payload["options"]]
    records = []
    for split in (DatasetSplit.DISCOVERY, DatasetSplit.VALIDATION):
        for index in range(8):
            human = make_response(
                challenge,
                PopulationClass.HUMAN,
                options[0],
                session_id=f"h-{split}-{index}",
                split=split,
            )
            records.append(human.model_copy(update={"challenge_split": split}))
            for family in ("family-a", "family-b"):
                ai = make_response(
                    challenge,
                    PopulationClass.AI,
                    options[-1],
                    session_id=f"{family}-{split}-{index}",
                    split=split,
                )
                records.append(
                    ai.model_copy(update={"model_family": family, "challenge_split": split})
                )
    matrix = cross_model_transfer(records)
    assert {(row["train_model_family"], row["test_model_family"]) for row in matrix} == {
        ("family-a", "family-a"),
        ("family-a", "family-b"),
        ("family-b", "family-a"),
        ("family-b", "family-b"),
    }


def test_audit_report_labels_and_confirmatory_proposal(tmp_path: Path, challenge) -> None:
    assert audit_challenges([challenge]).status == "PASS"
    manifest = load_manifest(
        RESEARCH_ROOT / "experiments" / "manifests" / "exp001a_real_signal_pilot.yaml"
    )
    assert "NOT CONFIRMATORY" in report_label(manifest)
    invalid = manifest.model_copy(
        update={
            "data_kind": "real_confirmatory",
            "confirmatory": True,
            "status": ManifestStatus.DRAFT,
        }
    )
    with pytest.raises(ValueError, match="frozen"):
        report_label(invalid)
    proposal = propose_confirmatory(manifest, tmp_path / "exp001b.yaml")
    text = proposal.read_text(encoding="utf-8")
    assert "status: draft" in text
    assert "NEEDS_DECISION" in text


def test_exp001a_preflight_is_blocked_without_human_decisions() -> None:
    manifest = load_manifest(
        RESEARCH_ROOT / "experiments" / "manifests" / "exp001a_real_signal_pilot.yaml"
    )
    report = run_preflight(manifest, environment={}, test_runner=lambda: True)
    assert report.status == CheckStatus.BLOCKED
    by_name = {check.name: check.status for check in report.checks}
    assert by_name["challenge audit passing"] == CheckStatus.PASS
    assert by_name["controls passing"] == CheckStatus.PASS
    assert by_name["consent version approved"] == CheckStatus.BLOCKED
    assert by_name["manifest frozen"] == CheckStatus.BLOCKED
