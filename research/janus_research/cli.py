from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from janus_research.audit import audit_challenges, generate_audit_set, write_audit
from janus_research.controls import run_controls, write_controls
from janus_research.manifest import load_manifest, save_manifest
from janus_research.pipeline import (
    RESEARCH_ROOT,
    analyze_pilot,
    experiment_directory,
    generate_experiment,
    manifest_path,
)
from janus_research.pipeline import analyze as analyze_experiment
from janus_research.pipeline import simulate as simulate_experiment
from janus_research.power import plan_power
from janus_research.preflight import CheckStatus, run_preflight
from janus_research.proposal import propose_confirmatory
from janus_research.provenance import git_commit
from janus_research.reports import generate_report
from janus_research.runners.model import ModelRunner, ProviderConfig, build_provider_runner
from janus_research.runners.model.batch import CheckpointStore, estimate_batch, run_batch
from janus_research.storage import read_challenges

app = typer.Typer(no_args_is_help=True, help="JANUS falsification-first research harness")
study_app = typer.Typer(no_args_is_help=True, help="Local consented human-study operations")
app.add_typer(study_app, name="study")


@app.command()
def generate(experiment: str = typer.Option(..., "--experiment", "-e")) -> None:
    public, private = generate_experiment(experiment)
    typer.echo(f"public={public}")
    typer.echo(f"private={private}")


@app.command()
def simulate(experiment: str = typer.Option(..., "--experiment", "-e")) -> None:
    exploratory, holdout = simulate_experiment(experiment)
    typer.echo("SYNTHETIC — NOT EVIDENCE")
    typer.echo(f"exploratory={exploratory}")
    typer.echo(f"sealed_holdout={holdout}")


@app.command()
def analyze(experiment: str = typer.Option(..., "--experiment", "-e")) -> None:
    typer.echo(f"analysis={analyze_experiment(experiment)}")


@app.command("analyze-pilot")
def analyze_real_pilot(
    human: Annotated[list[Path], typer.Option("--human")],
    model: Annotated[list[Path], typer.Option("--model")],
    experiment: str = typer.Option(..., "--experiment", "-e"),
) -> None:
    typer.echo(f"analysis={analyze_pilot(experiment, human, model)}")


@app.command()
def report(experiment: str = typer.Option(..., "--experiment", "-e")) -> None:
    report_path, digest_path = generate_report(experiment)
    typer.echo("SYNTHETIC — NOT EVIDENCE")
    typer.echo(f"report={report_path}")
    typer.echo(f"sha256={digest_path}")


@app.command("freeze-manifest")
def freeze_manifest(experiment: str = typer.Option(..., "--experiment", "-e")) -> None:
    path: Path = manifest_path(experiment)
    manifest = load_manifest(path)
    frozen = manifest.freeze()
    save_manifest(frozen, path)
    typer.echo(f"frozen={path} hash={frozen.content_hash}")


@study_app.command("start")
def study_start(
    experiment: str = typer.Option(..., "--experiment", "-e"),
    subject: str = typer.Option(..., "--subject"),
    port: int = typer.Option(8765, "--port", min=1024, max=65535),
) -> None:
    from janus_research.runners.human.server import run_study_server

    run_study_server(experiment, subject, port)


@study_app.command("withdraw")
def study_withdraw(
    experiment: str = typer.Option(..., "--experiment", "-e"),
    subject: str = typer.Option(..., "--subject"),
) -> None:
    from janus_research.runners.human.server import withdraw_subject

    typer.echo(f"withdrawal_audit={withdraw_subject(experiment, subject)}")


@app.command("power-plan")
def power_plan(
    human_fpr_target: float = typer.Option(..., "--human-fpr-target"),
    expected_ai_tpr: float = typer.Option(..., "--expected-ai-tpr"),
    confidence: float = typer.Option(0.95, "--confidence"),
    half_width: float = typer.Option(0.02, "--half-width"),
    attrition: float = typer.Option(0.1, "--attrition"),
) -> None:
    result = plan_power(
        human_fpr_target,
        expected_ai_tpr,
        confidence=confidence,
        desired_half_width=half_width,
        attrition=attrition,
    )
    typer.echo(json.dumps(result.to_dict(), indent=2))


@app.command("audit-challenges")
def audit_challenge_set(
    experiment: str = typer.Option(..., "--experiment", "-e"),
    seeds_per_family: int = typer.Option(120, "--seeds-per-family", min=10),
) -> None:
    manifest = load_manifest(manifest_path(experiment))
    challenges = generate_audit_set(manifest, seeds_per_family)
    audit = audit_challenges(challenges)
    destination = RESEARCH_ROOT / "data" / "reports" / manifest.experiment_id / "challenge-audit"
    challenge_hash = hashlib.sha256(
        "".join(sorted(challenge.challenge_id for challenge in challenges)).encode()
    ).hexdigest()
    provenance = {
        "manifest_hash": manifest.content_hash
        or hashlib.sha256(manifest.canonical_bytes()).hexdigest(),
        "dataset_hash": challenge_hash,
        "generator_versions": ",".join(manifest.challenge_families.values()),
        "analysis_code_version": git_commit(RESEARCH_ROOT.parent),
    }
    json_path, markdown_path = write_audit(audit, destination, provenance)
    typer.echo(f"status={audit.status} json={json_path} markdown={markdown_path}")
    if audit.status != "PASS":
        raise typer.Exit(1)


@app.command("controls")
def controls(experiment: str = typer.Option(..., "--experiment", "-e")) -> None:
    manifest = load_manifest(manifest_path(experiment))
    result = run_controls(manifest.random_seed)
    provenance = {
        "manifest_hash": manifest.content_hash
        or hashlib.sha256(manifest.canonical_bytes()).hexdigest(),
        "dataset_hash": "deterministic-control-seed:" + str(manifest.random_seed),
        "generator_versions": ",".join(manifest.challenge_families.values()),
        "analysis_code_version": git_commit(RESEARCH_ROOT.parent),
    }
    path = write_controls(
        result,
        RESEARCH_ROOT / "data" / "reports" / manifest.experiment_id,
        provenance,
    )
    typer.echo(f"{result.label}\nvalid={result.pipeline_valid} report={path}")
    if not result.pipeline_valid:
        raise typer.Exit(1)


@app.command("run-models")
def run_models(
    experiment: str = typer.Option(..., "--experiment", "-e"),
    execute: bool = typer.Option(False, "--execute"),
    approve_large_batch: bool = typer.Option(False, "--approve-large-batch"),
) -> None:
    manifest = load_manifest(manifest_path(experiment))
    expected_challenges = len(manifest.challenge_families) * manifest.challenge_count_per_family
    plan = estimate_batch(manifest, expected_challenges)
    typer.echo(json.dumps(plan.__dict__, indent=2))
    if not execute:
        typer.echo("DRY RUN — no provider calls made; pass --execute after reviewing the plan")
        return
    challenges = read_challenges(experiment_directory(manifest.experiment_id))
    runners: dict[tuple[str, ...], ModelRunner] = {}
    for target in manifest.provider_targets:
        if not target.enabled:
            continue
        for condition in manifest.model_conditions:
            parameters = manifest.model_condition_parameters.get(condition, {})
            runners[(target.provider, target.model_identifier, condition)] = build_provider_runner(
                target.provider,
                ProviderConfig(
                    target.model_identifier,
                    target.credential_env,
                    temperature=parameters.get("temperature"),
                    top_p=parameters.get("top_p"),
                ),
            )
    raw = RESEARCH_ROOT / "data" / "raw" / manifest.experiment_id / "models"
    run_batch(
        manifest,
        challenges,
        runners,
        CheckpointStore(raw / "checkpoint.jsonl"),
        raw / "responses.parquet",
        approved_large_batch=approve_large_batch,
    )
    typer.echo(f"responses={raw / 'responses.parquet'}")


@app.command("preflight")
def preflight(experiment: str = typer.Option(..., "--experiment", "-e")) -> None:
    manifest = load_manifest(manifest_path(experiment))

    def tests_pass() -> bool:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=RESEARCH_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.returncode == 0

    result = run_preflight(manifest, environment=os.environ, test_runner=tests_pass)
    typer.echo(f"{result.status.value}: {result.experiment_id}")
    for check in result.checks:
        typer.echo(f"{check.status.value:7} {check.name}: {check.detail}")
    if result.status == CheckStatus.BLOCKED:
        raise typer.Exit(1)


@app.command("propose-confirmatory")
def propose_confirmatory_manifest(
    experiment: str = typer.Option(..., "--from", "-e"),
) -> None:
    manifest = load_manifest(manifest_path(experiment))
    destination = RESEARCH_ROOT / "experiments" / "manifests" / "exp001b_confirmatory.yaml"
    typer.echo(f"proposal={propose_confirmatory(manifest, destination)} status=draft")


if __name__ == "__main__":
    app()
